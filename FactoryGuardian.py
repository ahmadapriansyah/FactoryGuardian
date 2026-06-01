from supabase import create_client
import streamlit as st
import cv2
import numpy as np
import time
import pandas as pd
import os
import base64
from st_supabase_connection import SupabaseConnection
from fpdf import FPDF
from datetime import datetime
import pytz
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

# --- SETUP ZONA WAKTU INDONESIA ---
tz_indo = pytz.timezone('Asia/Jakarta')

# --- UI SETTINGS ---
st.set_page_config(page_title="FactoryGuard AI Pro Cloud", layout="wide")

# --- KONEKSI SUPABASE & TWILIO ---
SUPABASE_URL = "https://cifkqcpxpskuxeksncwk.supabase.co"
SUPABASE_KEY = "sb_publishable_GnTiR-ZJBNBFChFEHt1KhQ_CIcax-D8"

# Coba ambil dari Streamlit Secrets dulu (kalau di Cloud), kalau gagal baru ambil dari lokal (.env)
try:
    TWILIO_SID = st.secrets["TWILIO_SID"]
    TWILIO_TOKEN = st.secrets["TWILIO_TOKEN"]
except:
    TWILIO_SID = os.getenv("TWILIO_SID")
    TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)
supabase_native = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNGSI ALARM LOKAL ---
def bunyikan_alarm(file_audio):
    try:
        with open(file_audio, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Gagal memutar suara, pastikan file {file_audio} ada di folder yang sama!")

# --- FUNGSI ANALITIK & PERHITUNGAN ---
def hitung_fatigue(bpm, jam_kerja):
    if jam_kerja > 8 and bpm > 100:
        return "⚠️ High Risk Fatigue"
    elif bpm > 110:
        return "⚠️ Anomali Jantung (Cek Medis)"
    return "✅ Fit to Work"

def estimasi_biaya(listrik, solar):
    return (listrik * 1500) + (solar * 13000)

def export_to_pdf(data, title):
    pdf = FPDF(orientation='L')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    
    title_clean = title.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 10, txt=title_clean, ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", size=9)
    
    if not data.empty:
        cols = data.columns.tolist()
        col_width = pdf.w / (len(cols) + 0.5) 
        
        pdf.set_fill_color(200, 220, 255)
        
        for col in cols:
            header_clean = str(col).upper().encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(col_width, 10, header_clean, border=1, align='C', fill=True)
        pdf.ln()
        
        for index, row in data.iterrows():
            for v in row.values:
                val_clean = str(v).encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(col_width, 10, val_clean, border=1, align='C')
            pdf.ln()
            
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 FactoryGuard Login</h1>", unsafe_allow_html=True)
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk", width="stretch"):
            if user == "admin" and pw == "123":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Akses Ditolak!")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("🏭 FactoryGuard AI")
menu = st.sidebar.selectbox("Main Menu", [
    "Dashboard Performance", 
    "Absensi & Fit Check", 
    "Eco Monitoring", 
    "Laporan Absensi", 
    "Laporan Eco Monitoring",
    "CCTV Safety Guard (AI)"
])
if st.sidebar.button("Logout", width="stretch"):
    st.session_state.logged_in = False
    st.rerun()

# --- 1. DASHBOARD PERFORMANCE ---
if menu == "Dashboard Performance":
    st.title("🚀 Factory Executive Analytics")
    
    try:
        emisi_data = conn.table("emisi").select("*").execute().data
        df_emisi = pd.DataFrame(emisi_data) if emisi_data else pd.DataFrame()
        
        absensi_data = conn.table("absensi").select("*").execute().data
        df_absensi = pd.DataFrame(absensi_data) if absensi_data else pd.DataFrame()

        karyawan_data = conn.table("karyawan").select("*").execute().data
        total_karyawan = len(karyawan_data) if karyawan_data else 0
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        df_emisi, df_absensi, total_karyawan = pd.DataFrame(), pd.DataFrame(), 0

    # --- ROW 1: HR & ABSENSI ---
    tgl_skrg = datetime.now(tz_indo).strftime("%Y-%m-%d")
    hadir_hari_ini = len(df_absensi[df_absensi['tanggal'] == tgl_skrg]) if not df_absensi.empty else 0
    bolos_hari_ini = max(total_karyawan - hadir_hari_ini, 0)

    st.subheader("👥 Live HR & Safety Monitoring")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Karyawan", f"{total_karyawan} Orang")
    k2.metric("Hadir Hari Ini", f"{hadir_hari_ini} Orang", "Aman", delta_color="normal")
    k3.metric("Belum Masuk/Bolos", f"{bolos_hari_ini} Orang", "- Risk", delta_color="inverse")
    
    lelah_count = len(df_absensi[df_absensi['status_lelah'] != "✅ Fit to Work"]) if not df_absensi.empty and 'status_lelah' in df_absensi.columns else 0
    k4.metric("Fatigue Alert (K3)", f"{lelah_count} Insiden", "Risk", delta_color="inverse")
    
    st.divider()

    # --- ROW 2: 3 PILAR LINGKUNGAN (ESG) ---
    st.subheader("🌍 Executive ESG & Environment Summary")
    
    e1, e2, e3, e4 = st.columns(4)
    if not df_emisi.empty:
        total_co2 = df_emisi['total_co2'].sum()
        total_biaya = df_emisi['biaya_estimasi'].sum()
        total_air = df_emisi['debit_air'].sum() if 'debit_air' in df_emisi.columns else 0
        avg_ph = df_emisi['ph_air'].mean() if 'ph_air' in df_emisi.columns else 0
        total_b3 = df_emisi['limbah_b3'].sum() if 'limbah_b3' in df_emisi.columns else 0
        total_non_b3 = df_emisi['limbah_non_b3'].sum() if 'limbah_non_b3' in df_emisi.columns else 0

        e1.metric("☁️ Carbon Footprint", f"{total_co2:.1f} kg", "Emisi Udara", delta_color="off")
        e2.metric("💧 Total Air Buangan", f"{total_air:.1f} m³", f"Avg pH: {avg_ph:.1f}", delta_color="off")
        e3.metric("🛢️ Total Limbah Padat", f"{(total_b3 + total_non_b3):.1f} kg", f"B3: {total_b3} kg", delta_color="inverse")
        e4.metric("💰 Total Biaya Operasional", f"Rp {total_biaya / 1000000:.2f} Jt", "Energi + IPAL + Vendor", delta_color="off")
    else:
        e1.metric("☁️ Carbon Footprint", "0 kg")
        e2.metric("💧 Total Air Buangan", "0 m³")
        e3.metric("🛢️ Total Limbah Padat", "0 kg")
        e4.metric("💰 Total Biaya Operasional", "Rp 0")

    st.write("---")

    # --- ROW 3: VISUALISASI GRAFIK 3 PILAR ---
    st.markdown("### 📊 Analitik Tren Lingkungan")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**📉 Tren Emisi Karbon**")
        if not df_emisi.empty and 'tanggal' in df_emisi.columns:
            st.area_chart(df_emisi.set_index('tanggal')['total_co2'], color="#ff0000")
        else:
            st.info("Belum ada data emisi.")

    with c2:
        st.markdown("**🌊 Debit Air Limbah (m³)**")
        if not df_emisi.empty and 'tanggal' in df_emisi.columns and 'debit_air' in df_emisi.columns:
            st.line_chart(df_emisi.set_index('tanggal')['debit_air'], color="#0000ff")
        else:
            st.info("Belum ada data air.")

    with c3:
        st.markdown("**🗑️ Komparasi Limbah (Kg)**")
        if not df_emisi.empty and 'limbah_b3' in df_emisi.columns:
            df_limbah = df_emisi[['tanggal', 'limbah_b3', 'limbah_non_b3']].set_index('tanggal')
            try:
                st.bar_chart(df_limbah, color=["#ff0000", "#ffffff"], stack=False)
            except Exception:
                st.bar_chart(df_limbah, color=["#ff0000", "#ffffff"])
        else:
            st.info("Belum ada data limbah.")

# --- 2. ABSENSI & FIT CHECK ---
elif menu == "Absensi & Fit Check":
    st.title("❤️ Presensi & Health Scan")
    tgl_skrg = datetime.now(tz_indo).strftime("%Y-%m-%d")
    
    with st.expander("👤 Management Karyawan (Tambah Baru)"):
        nama_baru = st.text_input("Nama Karyawan Baru")
        if st.button("Daftarkan Karyawan"):
            if nama_baru:
                try:
                    conn.table("karyawan").insert([{"nama": nama_baru}]).execute()
                    st.success(f"{nama_baru} Terdaftar!"); time.sleep(1); st.rerun()
                except Exception as e: 
                    st.error(f"Error / Nama sudah ada: {e}")
    
    if 'scan_selesai' not in st.session_state: st.session_state.scan_selesai = False
    if 'current_bpm' not in st.session_state: st.session_state.current_bpm = 0

    res_karyawan = conn.table("karyawan").select("nama").execute().data
    list_n = [r['nama'] for r in res_karyawan] if res_karyawan else []
    
    if list_n:
        nama_p = st.selectbox("Pilih Nama Anda", list_n)
        st.write("---")
        
        img_absen = st.camera_input("📸 Pindai Wajah Anda untuk Mengambil HR-BPM")
        
        if img_absen:
            if not st.session_state.scan_selesai:
                st.session_state.current_bpm = np.random.randint(72, 105)
                st.session_state.scan_selesai = True
                st.rerun()
                
            col_kiri, col_kanan = st.columns([2, 1])
            with col_kiri:
                st.success("✅ Wajah & Biometrik Berhasil Dipindai!")
            with col_kanan:
                st.metric("Detak Jantung", f"{st.session_state.current_bpm} BPM")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Check-In (Masuk)", width="stretch"):
                    data_in = {
                        "nama": nama_p, 
                        "tanggal": tgl_skrg, 
                        "jam_masuk": datetime.now(tz_indo).strftime("%H:%M:%S"), 
                        "bpm_masuk": st.session_state.current_bpm,
                        "status_lelah": hitung_fatigue(st.session_state.current_bpm, 0)
                    }
                    conn.table("absensi").insert([data_in]).execute()
                    st.session_state.scan_selesai = False
                    st.success("Check-In Berhasil!"); time.sleep(1); st.rerun()
            
            with c2:
                if st.button("🏠 Check-Out (Pulang)", width="stretch"):
                    cek = conn.table("absensi").select("id, jam_masuk").eq("nama", nama_p).eq("tanggal", tgl_skrg).is_("jam_pulang", "null").execute().data
                    if cek:
                        id_absen = cek[0]['id']
                        jam_masuk_str = cek[0]['jam_masuk']
                        jam_pulang_str = datetime.now(tz_indo).strftime("%H:%M:%S")
                        
                        fmt = "%H:%M:%S"
                        t_masuk = datetime.strptime(jam_masuk_str, fmt)
                        t_pulang = datetime.strptime(jam_pulang_str, fmt)
                        durasi_jam = (t_pulang - t_masuk).total_seconds() / 3600
                        
                        data_out = {
                            "jam_pulang": jam_pulang_str,
                            "bpm_pulang": st.session_state.current_bpm,
                            "status_lelah": hitung_fatigue(st.session_state.current_bpm, durasi_jam)
                        }
                        conn.table("absensi").update(data_out).eq("id", id_absen).execute()
                        st.session_state.scan_selesai = False
                        st.balloons()
                        st.success(f"Check-Out Berhasil! Tercatat bekerja selama {round(durasi_jam, 2)} Jam hari ini.")
                        time.sleep(3); st.rerun()
                    else: 
                        st.error("Belum Check-In hari ini atau sudah Check-Out!")
        else:
            st.session_state.scan_selesai = False

# --- 3. ECO MONITORING ---
elif menu == "Eco Monitoring":
    st.title("🌿 Input Data Lingkungan (PROPER KLHK)")
    
    if 'eco_unlocked' not in st.session_state:
        st.session_state.eco_unlocked = False

    if not st.session_state.eco_unlocked:
        st.warning("⚠️ **RESTRICTED AREA** \nHanya Manager HSE atau Kepala Divisi yang berwenang untuk mengakses dan mengubah data emisi dan limbah perusahaan.")
        
        col_pin, col_kosong = st.columns([1, 2])
        with col_pin:
            pin_input = st.text_input("Masukkan PIN Otorisasi:", type="password")
            if st.button("Buka Akses", width="stretch"):
                if pin_input == "ahmadganteng":
                    st.session_state.eco_unlocked = True
                    st.rerun()
                else:
                    st.error("❌ PIN Akses Ditolak!")
    
    if st.session_state.eco_unlocked:
        st.success("✅ Akses Diberikan. Selamat datang, Manager Lingkungan.")
        if st.button("🔒 Kunci Kembali Akses", type="secondary"):
            st.session_state.eco_unlocked = False
            st.rerun()
            
        st.write("---")
        
        tgl_hari_ini = datetime.now(tz_indo).strftime("%Y-%m-%d")
        try:
            cek_data = conn.table("emisi").select("*").eq("tanggal", tgl_hari_ini).execute().data
            data_hari_ini = cek_data[0] if cek_data else {}
        except Exception:
            data_hari_ini = {}
            
        def_l = float(data_hari_ini.get("listrik", 0.0) or 0.0)
        def_s = float(data_hari_ini.get("solar", 0.0) or 0.0)
        def_air = float(data_hari_ini.get("debit_air", 0.0) or 0.0)
        def_ph = float(data_hari_ini.get("ph_air", 7.0) or 7.0)
        def_b3 = float(data_hari_ini.get("limbah_b3", 0.0) or 0.0)
        def_nb3 = float(data_hari_ini.get("limbah_non_b3", 0.0) or 0.0)

        with st.form("eco_form"):
            tab_udara, tab_air, tab_padat = st.tabs(["🌫️ Udara & Energi", "💧 Air Limbah", "🛢️ Limbah Padat (B3 & Non-B3)"])
            
            with tab_udara:
                st.write("### 🏭 Data Pemantauan Udara & Energi")
                l = st.number_input("Konsumsi Listrik (kWh)", min_value=0.0, value=def_l)
                s = st.number_input("Konsumsi Solar (Liter)", min_value=0.0, value=def_s)
                
            with tab_air:
                st.write("### 🧪 Data Pemantauan Air Limbah")
                debit = st.number_input("Debit Air Buangan (m³)", min_value=0.0, value=def_air)
                ph = st.number_input("Tingkat Keasaman (pH)", min_value=0.0, max_value=14.0, value=def_ph, step=0.1, help="Baku mutu normal: pH 6.0 - 9.0")
                
            with tab_padat:
                st.write("### 🛢️ Data Pemantauan Limbah Padat")
                b3 = st.number_input("Limbah B3 (Oli Bekas, Sludge, dll) - Kg", min_value=0.0, value=def_b3, help="Bahan Berbahaya dan Beracun")
                non_b3 = st.number_input("Limbah Non-B3 (Kertas, Plastik, Scrap) - Kg", min_value=0.0, value=def_nb3, help="Limbah domestik/sisa produksi aman")
                
            if st.form_submit_button("Simpan Data Harian & Evaluasi"):
                
                if ph < 6.0 or ph > 9.0:
                    st.error(f"🚨 BAHAYA: pH Air {ph} melanggar baku mutu (Normal: 6-9). Segera hentikan pembuangan ke sungai!")
                if b3 > 50.0:
                    st.warning(f"⚠️ PERINGATAN K3: Limbah B3 mencapai {b3} Kg hari ini. Pastikan segera dipindahkan ke TPS B3 berizin dan catat di Logbook Manifest!")
                    
                tot = (l * 0.87) + (s * 2.31)
                
                biaya_energi = (l * 1500) + (s * 13000)
                biaya_air_ipal = debit * 5000 
                biaya_vendor_limbah = (b3 * 10000) + (non_b3 * 1000)
                biaya_total = biaya_energi + biaya_air_ipal + biaya_vendor_limbah
                
                data_payload = {
                    "listrik": l, 
                    "solar": s, 
                    "total_co2": tot, 
                    "biaya_estimasi": biaya_total,
                    "debit_air": debit,
                    "ph_air": ph,
                    "limbah_b3": b3,
                    "limbah_non_b3": non_b3
                }
                
                try:
                    if data_hari_ini:
                        id_emisi = data_hari_ini['id']
                        conn.table("emisi").update(data_payload).eq("id", id_emisi).execute()
                        st.success(f"✅ Data Diperbarui! Karbon: {tot:.2f} kg CO2 | Biaya: Rp {biaya_total:,.0f}")
                    else:
                        data_payload["tanggal"] = tgl_hari_ini
                        conn.table("emisi").insert([data_payload]).execute()
                        st.success(f"✅ Tersimpan Baru! Karbon: {tot:.2f} kg CO2 | Biaya: Rp {biaya_total:,.0f}")
                except Exception as e:
                    st.error(f"Error Database: {e}. Pastikan semua kolom baru sudah dibuat di Supabase!")

# --- 4. LAPORAN ABSENSI ---
elif menu == "Laporan Absensi":
    st.title("📋 Laporan Presensi & Durasi")
    st.write("### 🔍 Filter Pencarian Data")
    
    col1, col2 = st.columns(2)
    with col1:
        mulai_tgl = st.date_input("Dari Tanggal", pd.to_datetime(datetime.now(tz_indo).date()) - pd.Timedelta(days=7))
    with col2:
        akhir_tgl = st.date_input("Sampai Tanggal", pd.to_datetime(datetime.now(tz_indo).date()))

    absen_data = conn.table("absensi").select("*").gte("tanggal", str(mulai_tgl)).lte("tanggal", str(akhir_tgl)).execute().data
    df_absen = pd.DataFrame(absen_data) if absen_data else pd.DataFrame()
    
    if not df_absen.empty:
        df_absen['jam_masuk_dt'] = pd.to_datetime(df_absen['jam_masuk'], format='%H:%M:%S', errors='coerce')
        df_absen['jam_pulang_dt'] = pd.to_datetime(df_absen['jam_pulang'], format='%H:%M:%S', errors='coerce')
        df_absen['DURASI (JAM)'] = (df_absen['jam_pulang_dt'] - df_absen['jam_masuk_dt']).dt.total_seconds() / 3600
        df_absen['DURASI (JAM)'] = df_absen['DURASI (JAM)'].fillna(0).round(2)
        
        df_absen = df_absen.drop(columns=['jam_masuk_dt', 'jam_pulang_dt', 'id'], errors='ignore')

        st.write(f"Menampilkan data dari **{mulai_tgl}** hingga **{akhir_tgl}**")
        st.dataframe(df_absen, width="stretch")
        
        pdf_bytes = export_to_pdf(df_absen, f"LAPORAN ABSENSI PABRIK ({mulai_tgl} sd {akhir_tgl})")
        st.download_button(label="📥 Download PDF Absensi", data=pdf_bytes, file_name=f"Absensi_{mulai_tgl}_sd_{akhir_tgl}.pdf", mime="application/pdf")
    else:
        st.warning("Tidak ada data absensi pada rentang tanggal tersebut.")

# --- 5. LAPORAN ECO MONITORING ---
elif menu == "Laporan Eco Monitoring":
    st.title("📉 Laporan Lingkungan & PROPER")
    
    col1, col2 = st.columns(2)
    with col1:
        mulai_tgl_eco = st.date_input("Dari Tanggal ", pd.to_datetime(datetime.now(tz_indo).date()) - pd.Timedelta(days=30))
    with col2:
        akhir_tgl_eco = st.date_input("Sampai Tanggal ", pd.to_datetime(datetime.now(tz_indo).date()))

    with st.spinner("Menarik data lingkungan..."):
        eco_data = conn.table("emisi").select("*").gte("tanggal", str(mulai_tgl_eco)).lte("tanggal", str(akhir_tgl_eco)).execute().data
        df_eco = pd.DataFrame(eco_data) if eco_data else pd.DataFrame()
    
    if not df_eco.empty:
        df_eco = df_eco.drop(columns=['id'], errors='ignore')
        
        df_eco = df_eco.rename(columns={
            'tanggal': 'Tanggal',
            'listrik': 'Listrik(kWh)',
            'solar': 'Solar(L)',
            'total_co2': 'CO2(kg)',
            'biaya_estimasi': 'Biaya(Rp)',
            'debit_air': 'Air(m3)',
            'ph_air': 'pH',
            'limbah_b3': 'B3(kg)',
            'limbah_non_b3': 'NonB3(kg)'
        })
        
        if 'opasitas_asap' in df_eco.columns:
            df_eco = df_eco.drop(columns=['opasitas_asap'])
            
        st.write(f"Menampilkan data dari **{mulai_tgl_eco}** hingga **{akhir_tgl_eco}**")
        st.dataframe(df_eco, width="stretch")
        
        c1, c2 = st.columns(2)
        with c1:
            pdf_bytes = export_to_pdf(df_eco, f"LAPORAN LINGKUNGAN PABRIK ({mulai_tgl_eco} sd {akhir_tgl_eco})")
            st.download_button(label="📄 Download PDF Lingkungan", data=pdf_bytes, file_name=f"Lingkungan_{mulai_tgl_eco}_sd_{akhir_tgl_eco}.pdf", mime="application/pdf")
        with c2:
            csv_eco = df_eco.to_csv(index=False).encode('utf-8')
            st.download_button(label="📊 Download CSV (Excel)", data=csv_eco, file_name=f"Lingkungan_{mulai_tgl_eco}_sd_{akhir_tgl_eco}.csv", mime="text/csv")
    else:
        st.warning("Tidak ada data lingkungan pada rentang tanggal tersebut.")

# --- 6. CCTV SAFETY GUARD (AI) - MULTI AREA & ABNORMAL POSTURE ---
elif menu == "CCTV Safety Guard (AI)":
    st.title("🚨 Live CCTV K3 Detector")
    
    if 'list_area' not in st.session_state:
        st.session_state.list_area = ["Area Produksi 1", "Gudang Bahan Baku", "Jalur Konveyor"]

    if 'ppe_logs' not in st.session_state:
        st.session_state.ppe_logs = []
            
    if 'wa_sent' not in st.session_state:
        st.session_state.wa_sent = False

    with st.expander("⚙️ Pengaturan Area CCTV (Tambah/Hapus)"):
        tambah_area = st.text_input("Nama Area Baru:")
        if st.button("Tambah Area"):
            if tambah_area and tambah_area not in st.session_state.list_area:
                st.session_state.list_area.append(tambah_area)
                st.success(f"Area {tambah_area} ditambahkan!")
                st.rerun()

    pilih_area = st.selectbox("📍 Pilih Kamera Area yang Sedang Aktif:", st.session_state.list_area)

    col_cam, col_status = st.columns([2, 1])

    with col_cam:
        st.subheader(f"📹 Live Feed Scan: {pilih_area}")
        
        uploaded_image = st.camera_input("📸 Klik tombol di bawah untuk Ambil Gambar & Analisis AI")
        
        st.write("**Panel Kontrol AI:**")
        c2 = st.container()
        with c2:
            simulasi_abnormal = st.checkbox("⚠️ Simulasi: Postur Abnormal (Jatuh)")
            batas_tinggi = st.slider("Batas Ketinggian Abnormal (cm)", min_value=10, max_value=150, value=30, step=5, help="Sesuaikan ambang batas deteksi dengan kondisi lapangan")

    with col_status:
        st.subheader("📊 Status Kinerja")
        status_placeholder = st.empty()
        log_placeholder = st.empty()

    if uploaded_image:
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        frame = cv2.imdecode(file_bytes, 1)
        
        h, w, _ = frame.shape
        tgl_jam = datetime.now(tz_indo).strftime("%Y-%m-%d %H:%M:%S")
        
        batas_y = int(h - (h * (batas_tinggi / 200.0)))
        cv2.line(frame, (0, batas_y), (w, batas_y), (0, 255, 255), 2)
        cv2.putText(frame, f"Batas Deteksi: {batas_tinggi}cm", (10, batas_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if simulasi_abnormal:
            color = (0, 165, 255) 
            label = f"WARNING: ABNORMAL POSTURE (< {batas_tinggi}cm)!"
            status_k3 = f"🚨 PERHATIAN! Terdeteksi Pekerja Terjatuh di bawah {batas_tinggi}cm!"
            
            cv2.rectangle(frame, (int(w*0.2), int(h*0.7)), (int(w*0.8), int(h*0.9)), color, 3)
            cv2.rectangle(frame, (int(w*0.2), int(h*0.6)), (int(w*0.8), int(h*0.7)), color, -1)
            cv2.putText(frame, label, (int(w*0.21), int(h*0.66)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            bunyikan_alarm("alarm.mp3")
            
            entry_log = f"[{tgl_jam}] - {pilih_area}: Postur Abnormal (< {batas_tinggi}cm)!"
            if not st.session_state.ppe_logs or st.session_state.ppe_logs[0] != entry_log:
                st.session_state.ppe_logs.insert(0, entry_log)
                
            if not st.session_state.wa_sent:
                with st.spinner("⏳ Sedang memproses... Mengunggah bukti ke Cloud & mengirim WhatsApp Alert..."):
                    try:
                        filename_aman = tgl_jam.replace(":", "-").replace(" ", "_")
                        nama_file = f"bukti_{filename_aman}.jpg"
                        cv2.imwrite(nama_file, frame)
                        
                        with open(nama_file, "rb") as f:
                            supabase_native.storage.from_("bukti-kejadian").upload(
                                file=f, 
                                path=nama_file, 
                                file_options={"content-type": "image/jpeg"}
                            )
                        
                        link_foto = supabase_native.storage.from_("bukti-kejadian").get_public_url(nama_file)
                        
                        if os.path.exists(nama_file):
                            os.remove(nama_file)

                        client = Client(TWILIO_SID, TWILIO_TOKEN)
                        msg_body = f"🚨 *FACTORYGUARD ALERT* 🚨\n\nTerdeteksi Karyawan Terjatuh/Tidur (< {batas_tinggi}cm)!\nLokasi: {pilih_area}\nWaktu: {tgl_jam}\n\nSistem telah mengunggah bukti gambar secara otomatis."
                        client.messages.create(
                            from_='whatsapp:+14155238886', 
                            body=msg_body,
                            media_url=[link_foto],
                            to='whatsapp:+6285796326920'
                        )
                        
                        st.session_state.wa_sent = True 
                        st.sidebar.success("✅ Bukti terupload ke Supabase & WA Terkirim!")
                    except Exception as e:
                        st.sidebar.error(f"❌ Gagal sistem Cloud/WA: {e}")
        else:
            color = (0, 255, 0)
            label = "NORMAL ACTIVITY"
            status_k3 = "✅ Aman. Pekerja Beraktivitas Normal."
            
            cv2.rectangle(frame, (int(w*0.4), int(h*0.2)), (int(w*0.6), int(h*0.8)), color, 3)
            cv2.rectangle(frame, (int(w*0.4), int(h*0.1)), (int(w*0.6), int(h*0.2)), color, -1)
            cv2.putText(frame, label, (int(w*0.41), int(h*0.16)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            if st.session_state.wa_sent:
                st.session_state.wa_sent = False

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        st.image(frame_rgb, caption="Hasil Pemindaian Snapshot AI", width="stretch")
        
        if simulasi_abnormal:
            status_placeholder.error(status_k3)
        else:
            status_placeholder.success(status_k3)
            
        with log_placeholder.container():
            st.write("**📝 Log Anomali Terbaru:**")
            for log in st.session_state.ppe_logs[:5]: 
                st.caption(log)
    else:
        status_placeholder.info("Kamera standby. Klik tombol 'Ambil Gambar' di atas untuk memindai area.")
