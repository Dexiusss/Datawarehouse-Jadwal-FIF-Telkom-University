import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import streamlit.components.v1 as components

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard DW Jadwal Kuliah", layout="wide")

# --- FUNGSI MERMAID (DIAGRAM) ---
def render_mermaid(code):
    html_code = f"""
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
    </script>
    <div class="mermaid">
    {code}
    </div>
    """
    components.html(html_code, height=600, scrolling=True)

# --- KONEKSI DATABASE ---
st.sidebar.header("Koneksi Database")

# Mengambil URL dari secrets.toml
if "NEON_DB_URL" in st.secrets:
    db_url = st.secrets["NEON_DB_URL"]
    st.sidebar.success("Terhubung via Secrets")
else:
    db_url = st.sidebar.text_input("Masukkan Connection String (PostgreSQL):", type="password")
    st.sidebar.caption("Saran: Gunakan .streamlit/secrets.toml agar tidak perlu input manual.")

@st.cache_resource
def get_engine(connection_string):
    if connection_string.startswith("postgres://"):
        connection_string = connection_string.replace("postgres://", "postgresql://", 1)
    return create_engine(connection_string)

engine = None
is_connected = False

if db_url:
    try:
        engine = get_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        is_connected = True
    except Exception as e:
        st.sidebar.error(f"Gagal Konek: {e}")

# --- UI UTAMA ---
st.title("📊 Dashboard Jadwal Kuliah (Multi-Semester)")

if is_connected:
    # --- FILTER GLOBAL (SIDEBAR) ---
    st.sidebar.divider()
    st.sidebar.header("🔍 Filter Data")
    
    # Ambil list Tahun Ajaran yang tersedia
    try:
        df_ta = pd.read_sql("SELECT DISTINCT tahun_ajaran FROM dim_waktu ORDER BY tahun_ajaran DESC", engine)
        list_ta = df_ta['tahun_ajaran'].tolist()
        selected_ta = st.sidebar.selectbox("Pilih Tahun Ajaran:", list_ta)
        
        df_sem = pd.read_sql("SELECT DISTINCT semester FROM dim_waktu ORDER BY semester", engine)
        list_sem = df_sem['semester'].tolist()
        selected_sem = st.sidebar.selectbox("Pilih Semester:", list_sem)
    except Exception as e:
        st.error("Gagal memuat filter tahun/semester. Pastikan ETL Multi-Semester sudah dijalankan.")
        selected_ta = None
        selected_sem = None

    # Tab Navigasi
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Visualisasi Metrik", "📝 SQL Runner", "🔗 Star Schema", "ℹ️ Info"])

    # === TAB 1: VISUALISASI ===
    with tab1:
        if selected_ta and selected_sem:
            st.header(f"Analisis: {selected_ta} - {selected_sem}")
            
            col1, col2 = st.columns(2)
            
            # --- CHART 1: Beban SKS Dosen ---
            with col1:
                st.subheader("Top 10 Dosen (Total SKS)")
                # Query difilter berdasarkan Tahun & Semester dari Sidebar
                query_dosen = text("""
                SELECT 
                    d.nama_dosen, 
                    SUM(f.beban_sks_dosen) as total_sks
                FROM fact_table f
                JOIN dim_dosen d ON f.id_dosen = d.id_dosen
                JOIN dim_waktu w ON f.id_waktu = w.id_waktu
                WHERE w.tahun_ajaran = :ta AND w.semester = :sem
                GROUP BY d.nama_dosen
                ORDER BY total_sks DESC
                LIMIT 10;
                """)
                try:
                    df_dosen = pd.read_sql(query_dosen, engine, params={"ta": selected_ta, "sem": selected_sem})
                    if not df_dosen.empty:
                        fig_dosen = px.bar(df_dosen, x='nama_dosen', y='total_sks', color='total_sks',
                                           labels={'total_sks': 'SKS', 'nama_dosen': 'Nama Dosen'})
                        st.plotly_chart(fig_dosen, use_container_width=True)
                    else:
                        st.info("Tidak ada data untuk periode ini.")
                except Exception as e: st.error(f"Error query dosen: {e}")

            # --- CHART 2: Pola Kesibukan Harian ---
            with col2:
                st.subheader("Pola Kesibukan Harian")
                query_hari = text("""
                SELECT 
                    w.hari, 
                    COUNT(*) as jumlah_sesi
                FROM fact_table f
                JOIN dim_waktu w ON f.id_waktu = w.id_waktu
                WHERE w.tahun_ajaran = :ta AND w.semester = :sem
                GROUP BY w.hari
                ORDER BY 
                    CASE 
                        WHEN w.hari = 'Senin' THEN 1 WHEN w.hari = 'Selasa' THEN 2 
                        WHEN w.hari = 'Rabu' THEN 3 WHEN w.hari = 'Kamis' THEN 4 
                        WHEN w.hari = 'Jumat' THEN 5 WHEN w.hari = 'Sabtu' THEN 6 ELSE 7 
                    END;
                """)
                try:
                    df_hari = pd.read_sql(query_hari, engine, params={"ta": selected_ta, "sem": selected_sem})
                    if not df_hari.empty:
                        fig_hari = px.pie(df_hari, values='jumlah_sesi', names='hari', hole=0.4)
                        st.plotly_chart(fig_hari, use_container_width=True)
                    else:
                        st.info("Tidak ada data harian.")
                except Exception as e: st.error(f"Error query hari: {e}")

            # --- CHART 3: Penggunaan Ruangan ---
            st.subheader("Top 15 Penggunaan Ruangan")
            query_ruang = text("""
            SELECT 
                r.nama_ruangan,
                COUNT(*) as frekuensi_pakai
            FROM fact_table f
            JOIN dim_ruangan r ON f.id_ruangan = r.id_ruangan
            JOIN dim_waktu w ON f.id_waktu = w.id_waktu
            WHERE w.tahun_ajaran = :ta AND w.semester = :sem
            GROUP BY r.nama_ruangan
            ORDER BY frekuensi_pakai DESC
            LIMIT 15;
            """)
            try:
                df_ruang = pd.read_sql(query_ruang, engine, params={"ta": selected_ta, "sem": selected_sem})
                if not df_ruang.empty:
                    fig_ruang = px.bar(df_ruang, x='nama_ruangan', y='frekuensi_pakai')
                    st.plotly_chart(fig_ruang, use_container_width=True)
            except Exception as e: st.error(f"Error query ruangan: {e}")
        else:
            st.warning("Silakan pilih Tahun Ajaran dan Semester di Sidebar.")

    # === TAB 2: SQL RUNNER ===
    with tab2:
        st.header("🛠️ SQL Playground")
        st.caption("Gunakan sintaks PostgreSQL standar.")
        
        # Contoh query yang disesuaikan dengan skema Multi-Semester
        default_query = """-- Cek Mata Kuliah di Semester Tertentu
SELECT 
    d.nama_dosen,
    mk.nama_mk,
    mk.jenis_matakuliah,
    w.hari,
    w.jam_mulai
FROM fact_table f
JOIN dim_dosen d ON f.id_dosen = d.id_dosen
JOIN dim_matakuliah mk ON f.id_mk = mk.id_mk
JOIN dim_waktu w ON f.id_waktu = w.id_waktu
WHERE w.tahun_ajaran = '25/26' AND w.semester = 'Ganjil'
LIMIT 10;"""
        
        sql_query = st.text_area("SQL Editor:", value=default_query, height=200)
        if st.button("▶️ Jalankan Query", type="primary"):
            try:
                df_result = pd.read_sql(sql_query, engine)
                st.success(f"Hasil: {len(df_result)} baris.")
                st.dataframe(df_result, use_container_width=True)
            except Exception as e:
                st.error(f"SQL Error: {e}")

    # === TAB 3: STAR SCHEMA ===
    with tab3:
        st.header("Visualisasi Star Schema")
        schema_diagram = """
        erDiagram
            FACT_TABLE {
                int id_dosen FK
                int id_mk FK
                int id_ruangan FK
                int id_kelas FK
                int id_waktu FK
                int beban_sks_dosen
                int utilitas_ruangan
            }
            DIM_DOSEN { int id_dosen PK string nama_dosen }
            DIM_MATAKULIAH { int id_mk PK string nama_mk string jenis_matakuliah }
            DIM_RUANGAN { int id_ruangan PK string nama_ruangan string gedung }
            DIM_KELAS { int id_kelas PK string prodi string angkatan }
            DIM_WAKTU { int id_waktu PK string tahun_ajaran string semester string hari }

            DIM_DOSEN ||--|{ FACT_TABLE : "mengajar"
            DIM_MATAKULIAH ||--|{ FACT_TABLE : "memiliki"
            DIM_RUANGAN ||--|{ FACT_TABLE : "ditempati"
            DIM_KELAS ||--|{ FACT_TABLE : "menghadiri"
            DIM_WAKTU ||--|{ FACT_TABLE : "terjadi_pada"
        """
        render_mermaid(schema_diagram)

    # === TAB 4: INFO ===
    with tab4:
        st.markdown("""
        **Update Struktur:**
        - **Dimensi Waktu**: Kini memiliki kolom `tahun_ajaran` dan `semester` untuk membedakan data antar periode.
        - **Dimensi Mata Kuliah**: Memiliki kolom `jenis_matakuliah` (Reguler/Responsi).
        - **Fakta**: Kolom `beban_sks_dosen` sudah dihitung bersih dari duplikasi sesi.
        """)

else:
    st.info("Menunggu koneksi database...")