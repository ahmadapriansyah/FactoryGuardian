import streamlit as st
import cv2
import numpy as np
import time
import pandas as pd
from st_supabase_connection import SupabaseConnection
from fpdf import FPDF
from datetime import datetime
import plotly.express as px

# --- UI SETTINGS ---
st.set_page_config(page_title="FactoryGuard AI Pro Cloud", layout="wide", initial_sidebar_state="expanded")

# --- KONEKSI SUPABASE ---
SUPABASE_URL = "https://cifkqcpxpskuxeksncwk.supabase.co"
SUPABASE_KEY = "sb_publishable_GnTiR-ZJBNBFChFEHt1KhQ_CIcax-D8"

conn = st.connection("supabase", type=SupabaseConnection, url=SUPABASE_URL, key=SUPABASE_KEY)

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
        st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🔐 FactoryGuard Login</h1>", unsafe_allow_html=True)
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk"):
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
    "Laporan Eco"
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
    bolos_hari_ini = max(total_karyawan - hadir_hari_ini, 0)

    st.subheader("👥 Live HR & Safety Monitoring")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Karyawan", f"{total_karyawan} Orang")
    k2.metric("Hadir Hari Ini", f"{hadir_hari_ini} Orang", "Aman")
    k3.metric("Belum Masuk/Bolos", f"{bolos_hari_ini} Orang", "- Risk", delta_color="inverse")
    
    lelah_count = len(df_absensi[df_absensi['status_lelah'] != "✅ Fit to Work"]) if not df_absensi.empty and 'status_lelah' in df_absensi.columns else 0
    k4.metric("Fatigue Alert (K3)", f"{lelah_count} Insiden", "Risk", delta_color="inverse")
    
    st.divider()

    st.subheader("🌍 Executive ESG & Environment Summary")
    e1, e2, e3, e4 = st.columns(4)
    if not df_emisi.empty:
        total_co2 = df_emisi['total_co2'].sum()
        total_biaya = df_emisi['biaya_estimasi'].sum()
        total_air = df_emisi['debit_air'].sum() if 'debit_air' in df_emisi.columns else 0
        avg_ph = df_emisi['ph_air'].mean() if 'ph_air' in df_emisi.columns else 0
        total_b3 = df_emisi['limbah_b3'].sum() if 'limbah_b3' in df_emisi.columns else 0
        total_non_b3 = df_emisi['limbah_non_b3'].sum() if 'limbah_non_b3' in df_emisi.columns else 0

        e1.metric("☁️ Carbon Footprint", f"{total_co2:.1f} kg")
        e2.metric("💧 Total Air Buangan", f"{total_air:.1f} m³", f"Avg pH: {avg_ph:.1f}")
        e3.metric("🛢️ Total Limbah Padat", f"{(total_b3 + total_non_b3):.1f} kg", f"B3: {total_b3} kg")
        e4.metric("💰 Total Biaya Operasional", f"Rp {total_biaya / 1000000:.2f} Jt")
    else:
        for e in [e1, e2, e3, e4]: e.metric("Data", "0")

    st.write("---")
    st.markdown("### 📊 Analitik Tren Lingkungan")
    
    def fix_axis_layout(fig):
        fig.update_xaxes(tickangle=0, tickfont=dict(size=12), nticks=6)
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified")
        return fig

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📉 Tren Emisi Karbon (CO2)**")
        if not df_emisi.empty:
            fig_emisi = px.area(df_emisi, x='tanggal', y='total_co2', color_discrete_sequence=['#10B981'], markers=True)
            st.plotly_chart(fix_axis_layout(fig_emisi), use_container_width=True)
    with c2:
        st.markdown("**🌊 Debit Air Limbah (m³)**")
        if not df_emisi.empty:
            fig_air = px.line(df_emisi, x='tanggal', y='debit_air', color_discrete_sequence=['#3B82F6'], markers=True)
            st.plotly_chart(fix_axis_layout(fig_air), use_container_width=True)

    st.markdown("**🗑️ Komparasi Limbah B3 vs Non-B3 (Kg)**")
    if not df_emisi.empty:
        df_limbah = df_emisi[['tanggal', 'limbah_b3', 'limbah_non_b3']].melt(id_vars='tanggal', var_name='Kategori', value_name='Jumlah')
        fig_limbah = px.bar(df_limbah, x='tanggal', y='Jumlah', color='Kategori', barmode='group', color_discrete_map={'limbah_b3': '#EF4444', 'limbah_non_b3': '#F59E0B'})
        st.plotly_chart(fix_axis_layout(fig_limbah), use_container_width=True)

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
                except Exception as e: st.error(f"Error: {e}")
    
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
                placeholder = st.empty()
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    st.error("⚠️ Kamera tidak terdeteksi!")
                else:
                    start_time = time.time()
                    while time.time() - start_time < 5:
                        ret, frame = cap.read()
                        if not ret: continue
                        frame = cv2.flip(frame, 1)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, _ = frame_rgb.shape
                        cv2.rectangle(frame_rgb, (int(w*0.35), int(h*0.2)), (int(w*0.65), int(h*0.5)), (0, 255, 0), 2)
                        sisa = int(5 - (time.time() - start_time)) + 1
                        cv2.putText(frame_rgb, f"SCANNING HR... {sisa}s", (int(w*0.32), int(h*0.15)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        placeholder.image(frame_rgb, channels="RGB")
                        time.sleep(0.05)
                    cap.release()
                    placeholder.empty()
                    st.session_state.current_bpm = np.random.randint(70, 115)
                    st.session_state.scan_selesai = True
                    st.rerun()
            else:
                st.success("✅ Pindai Berhasil!")
                st.metric("Detak Jantung", f"{st.session_state.current_bpm} BPM")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Check-In (Masuk)", use_container_width=True):
                        data_in = {"nama": nama_p, "tanggal": tgl_skrg, "jam_masuk": datetime.now().strftime("%H:%M:%S"), "bpm_masuk": st.session_state.current_bpm, "status_lelah": hitung_fatigue(st.session_state.current_bpm, 0)}
                        conn.table("absensi").insert([data_in]).execute()
                        st.session_state.scan_selesai = False
                        st.success("Check-In Berhasil!"); time.sleep(1); st.rerun()
                with c2:
                    if st.button("🏠 Check-Out (Pulang)", use_container_width=True):
                        cek = conn.table("absensi").select("id, jam_masuk").eq("nama", nama_p).eq("tanggal", tgl_skrg).is_("jam_pulang", "null").execute().data
                        if cek:
                            t_masuk = datetime.strptime(cek[0]['jam_masuk'], "%H:%M:%S")
                            t_pulang = datetime.now()
                            durasi_jam = (t_pulang - t_masuk).total_seconds() / 3600
                            data_out = {"jam_pulang": t_pulang.strftime("%H:%M:%S"), "bpm_pulang": st.session_state.current_bpm, "status_lelah": hitung_fatigue(st.session_state.current_bpm, durasi_jam)}
                            conn.table("absensi").update(data_out).eq("id", cek[0]['id']).execute()
                            st.session_state.scan_selesai = False
                            st.balloons(); st.success("Check-Out Berhasil!"); time.sleep(2); st.rerun()

# --- 3. ECO MONITORING ---
elif menu == "Eco Monitoring":
    st.title("🌿 Input Data Lingkungan")
    if 'eco_unlocked' not in st.session_state: st.session_state.eco_unlocked = False

    if not st.session_state.eco_unlocked:
        pin_input = st.text_input("Masukkan PIN Otorisasi (HSE):", type="password")
        if st.button("Buka Akses"):
            if pin_input == "ahmadganteng":
                st.session_state.eco_unlocked = True
                st.rerun()
            else: st.error("PIN Salah!")
    
    if st.session_state.eco_unlocked:
        st.success("✅ Akses Manager HSE Aktif")
        if st.button("🔒 Kunci Akses"): 
            st.session_state.eco_unlocked = False
            st.rerun()
            
        tgl_hari_ini = datetime.now().strftime("%Y-%m-%d")
        with st.form("eco_form"):
            tab1, tab2, tab3 = st.tabs(["🌫️ Emisi Carbon", "💧 Limbah Air", "🛢️ Limbah Padat"])
            with tab1:
                l = st.number_input("Listrik (kWh)", min_value=0.0)
                s = st.number_input("Solar (Liter)", min_value=0.0)
            with tab2:
                debit = st.number_input("Debit Air (m³)", min_value=0.0)
                ph = st.number_input("pH Air", min_value=0.0, max_value=14.0, value=7.0)
            with tab3:
                b3 = st.number_input("Limbah B3 (kg)", min_value=0.0)
                non_b3 = st.number_input("Limbah Non-B3 (kg)", min_value=0.0)
            
            if st.form_submit_button("Simpan Data"):
                tot_co2 = (l * 0.87) + (s * 2.31)
                biaya = (l * 1500) + (s * 13000) + (b3 * 10000)
                payload = {"tanggal": tgl_hari_ini, "listrik": l, "solar": s, "total_co2": tot_co2, "biaya_estimasi": biaya, "debit_air": debit, "ph_air": ph, "limbah_b3": b3, "limbah_non_b3": non_b3}
                conn.table("emisi").insert([payload]).execute()
                st.success("Data Tersimpan!")

# --- 4. LAPORAN ABSENSI (DIPISAH) ---
elif menu == "Laporan Absensi":
    st.title("📋 Laporan Presensi & Safety (K3)")
    col1, col2 = st.columns(2)
    mulai = col1.date_input("Mulai", datetime.now() - pd.Timedelta(days=7))
    akhir = col2.date_input("Selesai", datetime.now())

    data = conn.table("absensi").select("*").gte("tanggal", str(mulai)).lte("tanggal", str(akhir)).execute().data
    df = pd.DataFrame(data) if data else pd.DataFrame()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        pdf_bytes = export_to_pdf(df, f"LAPORAN ABSENSI {mulai} - {akhir}")
        st.download_button("📥 Download PDF Absensi", pdf_bytes, f"Absensi_{mulai}.pdf", "application/pdf")
    else: st.warning("Data tidak ditemukan.")

# --- 5. LAPORAN ECO (DIPISAH) ---
elif menu == "Laporan Eco":
    st.title("📉 Laporan Eco Monitoring")
    col1, col2 = st.columns(2)
    mulai_e = col1.date_input("Mulai", datetime.now() - pd.Timedelta(days=30))
    akhir_e = col2.date_input("Selesai", datetime.now())

    data_e = conn.table("emisi").select("*").gte("tanggal", str(mulai_e)).lte("tanggal", str(akhir_e)).execute().data
    df_e = pd.DataFrame(data_e) if data_e else pd.DataFrame()

    if not df_e.empty:
        df_e = df_e.rename(columns={'total_co2': 'CO2(kg)', 'biaya_estimasi': 'Biaya(Rp)', 'ph_air': 'pH'})
        st.dataframe(df_e, use_container_width=True)
        pdf_e = export_to_pdf(df_e, f"LAPORAN ECO {mulai_e} - {akhir_e}")
        st.download_button("📄 Download PDF Lingkungan", pdf_e, f"Eco_{mulai_e}.pdf", "application/pdf")
        st.download_button("📊 Download CSV", df_e.to_csv(index=False).encode('utf-8'), f"Eco_{mulai_e}.csv", "text/csv")
    else: st.warning("Data tidak ditemukan.")
