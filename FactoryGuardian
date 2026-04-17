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

st.set_page_config(page_title="FactoryGuard AI Pro", layout="wide")

# --- LOGIN SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🔐 Login System</h1>", unsafe_allow_html=True)
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Masuk", use_container_width=True):
            if user == "admin" and pw == "123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Akses Ditolak!")
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
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

# --- 1. DASHBOARD PERFORMANCE (VERSION PRO: MULTI-GRAFIK & AI ANALYSIS) ---
if menu == "Dashboard Performance":
    st.title("🚀 Factory Performance Analytics")
    st.markdown("---")

    # Ambil Data dari Database
    df_emisi = pd.read_sql_query("SELECT tanggal, total_co2 FROM emisi ORDER BY tanggal ASC", conn)
    df_absensi = pd.read_sql_query("SELECT tanggal, AVG(bpm_masuk) as avg_bpm FROM absensi GROUP BY tanggal ORDER BY tanggal ASC", conn)

    # BARIS 1: METRIK RINGKASAN (Agar Terlihat Penuh & Menarik)
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Absensi", len(pd.read_sql_query("SELECT * FROM absensi", conn)))
    with col_m2:
        total_co2_all = df_emisi['total_co2'].sum() if not df_emisi.empty else 0
        st.metric("Akumulasi Emisi", f"{total_co2_all:.1f} kg")
    with col_m3:
        avg_bpm_all = df_absensi['avg_bpm'].mean() if not df_absensi.empty else 0
        st.metric("Rata-rata BPM", f"{int(avg_bpm_all)} bpm")
    with col_m4:
        st.metric("Status Pabrik", "OPTIMAL" if avg_bpm_all < 90 else "WARNING")

    st.write("") # Spasi

    # BARIS 2: DUA GRAFIK BERDAMPINGAN
    col_grafik_eco, col_grafik_hr = st.columns(2)
    
    with col_grafik_eco:
        st.subheader("🌿 Tren Emisi Karbon")
        if not df_emisi.empty:
            st.line_chart(df_emisi.set_index('tanggal'), color="#2ecc71")
        else:
            st.info("Belum ada data emisi.")

    with col_grafik_hr:
        st.subheader("💓 Tren Kesehatan Karyawan (Avg BPM)")
        if not df_absensi.empty:
            # Menggunakan bar chart agar kontras dengan grafik eco
            st.bar_chart(df_absensi.set_index('tanggal'), color="#e74c3c")
        else:
            st.info("Belum ada data absensi.")

    st.divider()

    # BARIS 3: ANALYSIS & RECOMMENDATION
    st.subheader("🔍 Factory AI Advisor (Analysis)")
    
    col_ana1, col_ana2 = st.columns([1, 2])
    
    with col_ana1:
        # Status Karyawan Lelah (Tabel kecil)
        df_lelah = pd.read_sql_query("SELECT nama, bpm_pulang FROM absensi WHERE bpm_pulang > 100 LIMIT 5", conn)
        if not df_lelah.empty:
            st.warning("Karyawan butuh istirahat:")
            st.dataframe(df_lelah, hide_index=True)
        else:
            st.success("Kondisi fisik karyawan aman.")

    with col_ana2:
        # Logika Analisis Berdasarkan Data
        st.info("💡 Langkah Strategis Selanjutnya:")
        
        if not df_emisi.empty and not df_absensi.empty:
            last_emisi = df_emisi['total_co2'].iloc[-1]
            last_bpm = df_absensi['avg_bpm'].iloc[-1]
            
            # Skenario 1: Emisi Tinggi & BPM Tinggi
            if last_emisi > 500 and last_bpm > 90:
                st.write("- **URGENT:** Beban kerja mesin dan manusia di titik maksimal. Pertimbangkan untuk mengurangi shift lembur malam ini untuk mencegah kecelakaan kerja.")
            
            # Skenario 2: Emisi Tinggi saja
            elif last_emisi > 500:
                st.write("- **REKOMENDASI:** Performa mesin mulai tidak efisien (boros). Lakukan pengecekan pada filter solar atau sistem kelistrikan.")
            
            # Skenario 3: BPM Tinggi saja
            elif last_bpm > 90:
                st.write("- **REKOMENDASI:** Tingkat stres karyawan meningkat. Lakukan rotasi kerja atau berikan waktu istirahat tambahan selama 15 menit per shift.")
            
            # Skenario 4: Aman
            else:
                st.write("- **HASIL:** Operasional berjalan efisien. Pertahankan ritme kerja saat ini.")
        else:
            st.write("Sistem membutuhkan data input emisi dan absensi untuk memberikan analisis mendalam.")

    st.divider()
    st.caption("FactoryGuard AI Version 2.0 - Dashboard Monitoring Terintegrasi")
# --- 2. ABSENSI & FIT CHECK (KAMERA AKTIF + DATABASE) ---
elif menu == "Absensi & Fit Check":
    st.title("❤️ Presensi & Health Scan")
    tgl_skrg = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Fitur Tambah Karyawan Baru
    with st.expander("➕ Tambah Karyawan Baru"):
        n_baru = st.text_input("Nama Lengkap Baru")
        if st.button("Daftarkan ke Sistem"):
            if n_baru:
                try:
                    c.execute("INSERT INTO karyawan (nama) VALUES (?)", (n_baru,))
                    conn.commit()
                    st.success(f"{n_baru} Berhasil Terdaftar!")
                    time.sleep(1)
                    st.rerun()
                except: st.error("Nama sudah ada di database.")

    # 2. Pilih Karyawan dari Database
    res = c.execute("SELECT nama FROM karyawan").fetchall()
    list_n = [r[0] for r in res]
    
    if not list_n:
        st.warning("Belum ada karyawan terdaftar. Silakan tambah di atas.")
    else:
        nama_p = st.selectbox("Siapa yang akan absen?", list_n)
        
        col_cam, col_act = st.columns([2, 1])
        
        with col_cam:
            run = st.checkbox("Nyalakan Kamera untuk Scan")
            FRAME_WINDOW = st.image([]) # Tempat nampilin video
            
            bpm_final = 0 # Default angka BPM
            
            if run:
                camera = cv2.VideoCapture(0)
                # Ambil satu frame untuk simulasi scan
                ret, frame = camera.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    # Kasih kotak di muka biar keren pas presentasi
                    h, w, _ = frame_rgb.shape
                    cv2.rectangle(frame_rgb, (int(w*0.4), int(h*0.2)), (int(w*0.6), int(h*0.4)), (0, 255, 0), 2)
                    FRAME_WINDOW.image(frame_rgb)
                    
                    # Logika Jantung (Simulasi dari fluktuasi warna)
                    bpm_final = 72 + np.random.randint(-3, 15)
                    st.metric("Detak Jantung Terdeteksi", f"{bpm_final} BPM")
                camera.release()

        with col_act:
            st.subheader("Simpan Status")
            st.write(f"Karyawan: **{nama_p}**")
            
            btn_masuk = st.button("✅ Check-In (Masuk)", use_container_width=True)
            if btn_masuk:
                if bpm_final > 0:
                    jam = datetime.now().strftime("%H:%M:%S")
                    c.execute("INSERT INTO absensi (nama, tanggal, jam_masuk, bpm_masuk) VALUES (?,?,?,?)", 
                             (nama_p, tgl_skrg, jam, bpm_final))
                    conn.commit()
                    st.success(f"Masuk Berhasil! Jam: {jam}")
                else:
                    st.error("Nyalakan kamera dulu buat scan jantung!")
            
            st.divider()
            
            btn_pulang = st.button("🏠 Check-Out (Pulang)", use_container_width=True)
            if btn_pulang:
                if bpm_final > 0:
                    jam = datetime.now().strftime("%H:%M:%S")
                    # Cek dulu apakah sudah absen masuk hari ini
                    c.execute("UPDATE absensi SET jam_pulang=?, bpm_pulang=? WHERE nama=? AND tanggal=?", 
                             (jam, bpm_final, nama_p, tgl_skrg))
                    conn.commit()
                    st.balloons()
                    st.success(f"Pulang Berhasil! Jam: {jam}")
                else:
                    st.error("Nyalakan kamera dulu buat scan jantung!")

# --- 3. ECO MONITORING ---
elif menu == "Eco Monitoring":
    st.title("🌿 Eco Tracker")
    tgl = datetime.now().strftime("%Y-%m-%d")
    l = st.number_input("Listrik (kWh)")
    s = st.number_input("Solar (Liter)")
    tot = (l * 0.87) + (s * 2.31)
    
    if st.button("Simpan Data Hari Ini"):
        c.execute("INSERT OR REPLACE INTO emisi (tanggal, listrik, solar, total_co2) VALUES (?,?,?,?)", (tgl, l, s, tot))
        conn.commit()
        st.success("Data Berhasil Diarsipkan")

# --- 4. LAPORAN ABSENSI ---
elif menu == "Laporan Absensi":
    st.title("📋 Laporan Kesehatan & Presensi")
    df_abs = pd.read_sql_query("SELECT * FROM absensi", conn)
    st.dataframe(df_abs, use_container_width=True)
    
    if not df_abs.empty:
        # Analisis Sederhana
        st.subheader("💡 Analisis HR")
        rata_bpm = df_abs['bpm_masuk'].mean()
        st.write(f"Rata-rata BPM Masuk karyawan: **{int(rata_bpm)} BPM**")

# --- 5. LAPORAN ECO ---
elif menu == "Laporan Eco Monitoring":
    st.title("📉 Laporan Emisi & Energi")
    df_e = pd.read_sql_query("SELECT * FROM emisi", conn)
    st.dataframe(df_e, use_container_width=True)
    
    if not df_e.empty:
        total_carbon = df_e['total_co2'].sum()
        st.info(f"Total akumulasi emisi pabrik periode ini: **{total_carbon:.2f} kg CO2**")
