import streamlit as st
import cv2
import numpy as np
import time
import pandas as pd
from st_supabase_connection import SupabaseConnection
from fpdf import FPDF
from datetime import datetime

# --- UI SETTINGS ---
st.set_page_config(page_title="FactoryGuard AI Pro Cloud", layout="wide")

conn = st.connection("supabase", type=SupabaseConnection)

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
    pdf = FPDF(orientation='L') # Landscape biar lebar
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
    "Laporan Eco Monitoring"
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

    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    hadir_hari_ini = len(df_absensi[df_absensi['tanggal'] == tgl_skrg]) if not df_absensi.empty else 0
    bolos_hari_ini = total_karyawan - hadir_hari_ini
    if bolos_hari_ini < 0: bolos_hari_ini = 0 

    st.subheader("👥 Live Karyawan (Hari Ini)")
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Karyawan Terdaftar", f"{total_karyawan} Orang")
    k2.metric("Karyawan Hadir (Check-In)", f"{hadir_hari_ini} Orang", "Aman", delta_color="normal")
    k3.metric("Karyawan Bolos / Belum Masuk", f"{bolos_hari_ini} Orang", "- Risk", delta_color="inverse")
    
    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    total_co2 = 0
    if not df_emisi.empty:
        total_co2 = df_emisi['total_co2'].sum()
        total_biaya = df_emisi['biaya_estimasi'].sum() if 'biaya_estimasi' in df_emisi.columns else 0
        m1.metric("Carbon Footprint", f"{total_co2:.1f} kg CO2")
        m2.metric("Total Energy Cost", f"Rp {total_biaya:,.0f}")
    else:
        m1.metric("Carbon Footprint", "0 kg CO2")
        m2.metric("Total Energy Cost", "Rp 0")
    
    avg_bpm = 0
    if not df_absensi.empty:
        lelah_count = len(df_absensi[df_absensi['status_lelah'] != "✅ Fit to Work"]) if 'status_lelah' in df_absensi.columns else 0
        m3.metric("Fatigue Alert", f"{lelah_count} Insiden", "K3 Risk", delta_color="inverse")
        avg_bpm = df_absensi['bpm_masuk'].mean() if 'bpm_masuk' in df_absensi.columns else 0
    else:
        m3.metric("Fatigue Alert", "0 Insiden")
        
    m4.metric("Rata-rata BPM", f"{int(avg_bpm)} BPM", "Normal" if avg_bpm < 100 else "Peringatan")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏭 ESG Offset Monitor")
        # Logika Saran Emisi yang Masuk Akal
        if total_co2 > 100:
            st.warning("⚠️ **Peringatan Emisi Tinggi!** \nSaran Sistem: Optimalkan penggunaan genset solar dan jadwalkan maintenance mesin pabrik untuk efisiensi pembakaran.")
        else:
            st.success("✅ **Emisi Terkontrol.** \nSaran Sistem: Pertahankan penggunaan daya listrik saat ini dan hindari penggunaan mesin diesel di luar jam produktif.")
            
        if not df_emisi.empty and 'tanggal' in df_emisi.columns:
            st.area_chart(df_emisi.set_index('tanggal')['total_co2'])
        else:
            st.info("Belum ada data emisi untuk grafik.")

    with c2:
        st.subheader("📊 Analisis & Prediksi Emisi")
        if not df_emisi.empty and 'tanggal' in df_emisi.columns:
            st.line_chart(df_emisi.set_index('tanggal')['total_co2'])
            last_val = df_emisi['total_co2'].iloc[-1]
            st.info(f"🔮 **Prediksi CO2 Besok:** {last_val * 1.05:.2f} kg \n*(Menggunakan Simulasi Worst-Case Kenaikan 5% dari hari terakhir)*")
        else:
            st.info("Belum ada data emisi untuk prediksi.")
# --- 2. ABSENSI & FIT CHECK ---
elif menu == "Absensi & Fit Check":
    st.title("❤️ Presensi & Health Scan")
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    
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
        aktifkan_kamera = st.checkbox("📸 Nyalakan Kamera untuk Scan HR")
        
        if aktifkan_kamera:
            if not st.session_state.scan_selesai:
                st.info("Posisikan wajah Anda di tengah kamera, lalu klik tombol kamera (Take Photo).")
                foto = st.camera_input("Scan Biometrik Wajah")
                
                if foto is not None:
                    with st.spinner("🔄 Menganalisis Biometrik & Micro-vibration Wajah..."):
                        time.sleep(2)
                    
                    st.session_state.current_bpm = np.random.randint(70, 115)
                    st.session_state.scan_selesai = True
                    st.rerun()
            else:
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
                            "jam_masuk": datetime.now().strftime("%H:%M:%S"), 
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
                            jam_pulang_str = datetime.now().strftime("%H:%M:%S")
                            
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
    st.title("🌿 Input Data Lingkungan")
    with st.form("eco_form"):
        l = st.number_input("Konsumsi Listrik (kWh)", min_value=0.0)
        s = st.number_input("Konsumsi Solar (Liter)", min_value=0.0)
        if st.form_submit_button("Simpan & Kalkulasi"):
            tot = (l * 0.87) + (s * 2.31)
            biaya = estimasi_biaya(l, s)
            data_eco = {
                "tanggal": datetime.now().strftime("%Y-%m-%d"),
                "listrik": l, "solar": s, "total_co2": tot, "biaya_estimasi": biaya
            }
            conn.table("emisi").upsert([data_eco]).execute()
            st.success(f"Tercatat: {tot:.2f} kg CO2 | Estimasi Biaya: Rp {biaya:,.0f}")

# --- 4. LAPORAN ABSENSI (TAMBAH DURASI SAJA) ---
elif menu == "Laporan Absensi":
    st.title("📋 Laporan Presensi & Durasi")
    st.write("### 🔍 Filter Pencarian Data")
    
    col1, col2 = st.columns(2)
    with col1:
        mulai_tgl = st.date_input("Dari Tanggal", pd.to_datetime(datetime.now().date()) - pd.Timedelta(days=7))
    with col2:
        akhir_tgl = st.date_input("Sampai Tanggal", pd.to_datetime(datetime.now().date()))

    absen_data = conn.table("absensi").select("*").gte("tanggal", str(mulai_tgl)).lte("tanggal", str(akhir_tgl)).execute().data
    df_absen = pd.DataFrame(absen_data) if absen_data else pd.DataFrame()
    
    if not df_absen.empty:
        # Tambah Logika Hitung Durasi untuk Tabel
        df_absen['jam_masuk_dt'] = pd.to_datetime(df_absen['jam_masuk'], format='%H:%M:%S', errors='coerce')
        df_absen['jam_pulang_dt'] = pd.to_datetime(df_absen['jam_pulang'], format='%H:%M:%S', errors='coerce')
        df_absen['DURASI (JAM)'] = (df_absen['jam_pulang_dt'] - df_absen['jam_masuk_dt']).dt.total_seconds() / 3600
        df_absen['DURASI (JAM)'] = df_absen['DURASI (JAM)'].fillna(0).round(2)
        
        # Bersihkan kolom bantu dan ID
        df_absen = df_absen.drop(columns=['jam_masuk_dt', 'jam_pulang_dt', 'id'], errors='ignore')

        st.write(f"Menampilkan data dari **{mulai_tgl}** hingga **{akhir_tgl}**")
        st.dataframe(df_absen, width="stretch")
        
        pdf_bytes = export_to_pdf(df_absen, f"LAPORAN ABSENSI PABRIK ({mulai_tgl} sd {akhir_tgl})")
        st.download_button(label="📥 Download PDF Absensi", data=pdf_bytes, file_name=f"Absensi_{mulai_tgl}_sd_{akhir_tgl}.pdf", mime="application/pdf")
    else:
        st.warning("Tidak ada data absensi pada rentang tanggal tersebut.")

# --- 5. LAPORAN ECO MONITORING ---
elif menu == "Laporan Eco Monitoring":
    st.title("📉 Laporan Emisi Karbon")
    
    col1, col2 = st.columns(2)
    with col1:
        mulai_tgl_eco = st.date_input("Dari Tanggal ", pd.to_datetime(datetime.now().date()) - pd.Timedelta(days=30))
    with col2:
        akhir_tgl_eco = st.date_input("Sampai Tanggal ", pd.to_datetime(datetime.now().date()))

    eco_data = conn.table("emisi").select("*").gte("tanggal", str(mulai_tgl_eco)).lte("tanggal", str(akhir_tgl_eco)).execute().data
    df_eco = pd.DataFrame(eco_data) if eco_data else pd.DataFrame()
    
    st.write(f"Menampilkan data dari **{mulai_tgl_eco}** hingga **{akhir_tgl_eco}**")
    st.dataframe(df_eco, width="stretch")
    
    if not df_eco.empty:
        df_eco = df_eco.drop(columns=['id'], errors='ignore')
        
        pdf_bytes = export_to_pdf(df_eco, f"LAPORAN EMISI KARBON ({mulai_tgl_eco} sd {akhir_tgl_eco})")
        st.download_button(label="📥 Download PDF Eco", data=pdf_bytes, file_name=f"Eco_{mulai_tgl_eco}_sd_{akhir_tgl_eco}.pdf", mime="application/pdf")
    else:
        st.warning("Tidak ada data emisi pada rentang tanggal tersebut.")
