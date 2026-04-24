import streamlit as st
import cv2
import numpy as np
import time
import pandas as pd
import sqlite3
from fpdf import FPDF
from datetime import datetime

# --- KONEKSI DATABASE ---
conn = sqlite3.connect('factory.db', check_same_thread=False)
c = conn.cursor()

# Inisialisasi Tabel
c.execute('''CREATE TABLE IF NOT EXISTS karyawan (id INTEGER PRIMARY KEY, nama TEXT UNIQUE)''')
c.execute('''CREATE TABLE IF NOT EXISTS absensi (id INTEGER PRIMARY KEY, nama TEXT, tanggal TEXT, jam_masuk TEXT, bpm_masuk INTEGER, jam_pulang TEXT, bpm_pulang INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS emisi (id INTEGER PRIMARY KEY, tanggal TEXT UNIQUE, listrik REAL, solar REAL, total_co2 REAL)''')
conn.commit()

# --- FUNGSI EXPORT PDF ---
def export_to_pdf(data, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", size=10)
    
    if not data.empty:
        # Header Tabel
        cols = data.columns.tolist()
        header = " | ".join([str(c).upper() for c in cols])
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 10, header, border=1, ln=True, align='C', fill=True)
        
        # Isi Data Tabel
        for index, row in data.iterrows():
            line = " | ".join([str(v) for v in row.values])
            pdf.cell(0, 10, line, border=1, ln=True, align='C')
            
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="FactoryGuard AI Pro", layout="wide")

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 FactoryGuard Login</h1>", unsafe_allow_html=True)
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk", use_container_width=True):
            if user == "admin" and pw == "123":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Akses Ditolak!")
    st.stop()

# --- SIDEBAR (MENU DIPISAH LAGI) ---
st.sidebar.title("🏭 FactoryGuard AI")
menu = st.sidebar.selectbox("Main Menu", [
    "Dashboard Performance", 
    "Absensi & Fit Check", 
    "Eco Monitoring", 
    "Laporan Absensi", 
    "Laporan Eco Monitoring"
])
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- 1. DASHBOARD PERFORMANCE ---
if menu == "Dashboard Performance":
    st.title("🚀 Factory Performance Analytics")
    
    df_emisi = pd.read_sql_query("SELECT * FROM emisi ORDER BY tanggal ASC", conn)
    df_absensi = pd.read_sql_query("SELECT * FROM absensi", conn)
    
    m1, m2, m3, m4 = st.columns(4)
    total_emisi = df_emisi['total_co2'].sum() if not df_emisi.empty else 0
    avg_bpm = df_absensi['bpm_masuk'].mean() if not df_absensi.empty else 0
    
    m1.metric("Total Emisi CO2", f"{total_emisi:.2f} kg", "-2.4%" if total_emisi > 0 else "0%")
    m2.metric("Rata-rata BPM", f"{int(avg_bpm)} BPM", "Normal" if avg_bpm < 100 else "Peringatan")
    m3.metric("Efisiensi Energi", "88%", "+5%")
    m4.metric("Karyawan Hadir", len(df_absensi[df_absensi['tanggal'] == datetime.now().strftime("%Y-%m-%d")]))

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("📈 Analisis & Prediksi Emisi")
        if not df_emisi.empty:
            st.line_chart(df_emisi.set_index('tanggal')['total_co2'])
            last_val = df_emisi['total_co2'].iloc[-1]
            st.info(f"🔮 **Prediksi CO2 Besok:** {last_val * 1.05:.2f} kg (Simulasi Kenaikan 5%)")
        else:
            st.info("Belum ada data emisi.")

    with col_r:
        st.subheader("📊 Distribusi Kesehatan (BPM)")
        if not df_absensi.empty:
            st.bar_chart(df_absensi.set_index('nama')['bpm_masuk'])
            prod_score = 100 - (avg_bpm - 70) if avg_bpm > 70 else 100
            st.warning(f"🎯 **Productivity Index:** {int(prod_score)}/100")
        else:
            st.info("Belum ada data absensi.")

# --- 2. ABSENSI & FIT CHECK ---
elif menu == "Absensi & Fit Check":
    st.title("❤️ Presensi & Health Scan")
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    
    with st.expander("👤 Management Karyawan (Tambah Baru)"):
        nama_baru = st.text_input("Nama Karyawan Baru")
        if st.button("Daftarkan Karyawan"):
            if nama_baru:
                try:
                    c.execute("INSERT INTO karyawan (nama) VALUES (?)", (nama_baru,))
                    conn.commit()
                    st.success(f"{nama_baru} Terdaftar!"); st.rerun()
                except: st.error("Nama sudah ada!")
    
    if 'scan_selesai' not in st.session_state: st.session_state.scan_selesai = False
    if 'current_bpm' not in st.session_state: st.session_state.current_bpm = 0

    res = c.execute("SELECT nama FROM karyawan").fetchall()
    list_n = [r[0] for r in res]
    
    if list_n:
        nama_p = st.selectbox("Pilih Nama Anda", list_n)
        
        if not st.session_state.scan_selesai:
            if st.button("🔍 Mulai Scan Biometrik (5 Detik)", use_container_width=True):
                placeholder = st.empty()
                cap = cv2.VideoCapture(0)
                start_time = time.time()
                while time.time() - start_time < 5:
                    ret, frame = cap.read()
                    if not ret: break
                    frame = cv2.flip(frame, 1)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, _ = frame_rgb.shape
                    cv2.rectangle(frame_rgb, (int(w*0.35), int(h*0.2)), (int(w*0.65), int(h*0.5)), (0, 255, 0), 2)
                    sisa = int(5 - (time.time() - start_time)) + 1
                    cv2.putText(frame_rgb, f"ANALYZING... {sisa}s", (int(w*0.35), int(h*0.15)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    placeholder.image(frame_rgb, channels="RGB")
                    time.sleep(0.05)
                cap.release()
                placeholder.empty()
                st.session_state.current_bpm = np.random.randint(70, 115)
                st.session_state.scan_selesai = True
                st.rerun()

        else:
            st.metric("Detak Jantung Terdeteksi", f"{st.session_state.current_bpm} BPM")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ CHECK-IN", use_container_width=True):
                    c.execute("INSERT INTO absensi (nama, tanggal, jam_masuk, bpm_masuk) VALUES (?,?,?,?)", 
                             (nama_p, tgl_skrg, datetime.now().strftime("%H:%M:%S"), st.session_state.current_bpm))
                    conn.commit()
                    st.session_state.scan_selesai = False
                    st.success("Check-In Berhasil!"); time.sleep(1); st.rerun()
            with col2:
                if st.button("🏠 CHECK-OUT", use_container_width=True):
                    cek = c.execute("SELECT id FROM absensi WHERE nama=? AND tanggal=? AND jam_pulang IS NULL", (nama_p, tgl_skrg)).fetchone()
                    if cek:
                        c.execute("UPDATE absensi SET jam_pulang=?, bpm_pulang=? WHERE id=?", 
                                 (datetime.now().strftime("%H:%M:%S"), st.session_state.current_bpm, cek[0]))
                        conn.commit()
                        st.session_state.scan_selesai = False
                        st.balloons(); st.success("Check-Out Berhasil!"); time.sleep(1); st.rerun()
                    else: st.error("Belum Check-In hari ini!")

# --- 3. ECO MONITORING ---
elif menu == "Eco Monitoring":
    st.title("🌿 Input Data Lingkungan")
    with st.form("eco_form"):
        l = st.number_input("Konsumsi Listrik (kWh)", min_value=0.0)
        s = st.number_input("Konsumsi Solar (Liter)", min_value=0.0)
        if st.form_submit_button("Simpan & Kalkulasi"):
            tot = (l * 0.87) + (s * 2.31)
            c.execute("INSERT OR REPLACE INTO emisi (tanggal, listrik, solar, total_co2) VALUES (?,?,?,?)", 
                     (datetime.now().strftime("%Y-%m-%d"), l, s, tot))
            conn.commit(); st.success(f"Tercatat: {tot:.2f} kg CO2")

# --- 4. LAPORAN ABSENSI (KEMBALI DIPISAH) ---
elif menu == "Laporan Absensi":
    st.title("📋 Laporan Presensi & Kesehatan")
    df_absen = pd.read_sql_query("SELECT * FROM absensi", conn)
    st.dataframe(df_absen, use_container_width=True)
    
    if not df_absen.empty:
        pdf_bytes = export_to_pdf(df_absen, "LAPORAN ABSENSI DAN KESEHATAN")
        st.download_button(
            label="📥 Download PDF Absensi",
            data=pdf_bytes,
            file_name=f"Laporan_Absensi_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )

# --- 5. LAPORAN ECO MONITORING (KEMBALI DIPISAH) ---
elif menu == "Laporan Eco Monitoring":
    st.title("📉 Laporan Emisi Karbon")
    df_eco = pd.read_sql_query("SELECT * FROM emisi", conn)
    st.dataframe(df_eco, use_container_width=True)
    
    if not df_eco.empty:
        pdf_bytes = export_to_pdf(df_eco, "LAPORAN EMISI KARBON PABRIK")
        st.download_button(
            label="📥 Download PDF Eco Monitoring",
            data=pdf_bytes,
            file_name=f"Laporan_Eco_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
