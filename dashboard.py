import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
import streamlit.components.v1 as components
import textwrap # Import ini penting untuk membersihkan spasi

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard DW Jadwal Kuliah", layout="wide")

# --- FUNGSI MERMAID (DIAGRAM) ---
def render_mermaid(code):
    code = textwrap.dedent(code)
    
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


# --- SIDEBAR: KONEKSI DATABASE ---
st.sidebar.header("Koneksi Database")

# Prioritas: Secrets > Input Manual
if "NEON_DB_URL" in st.secrets:
    db_url = st.secrets["NEON_DB_URL"]
    st.sidebar.success("Terhubung via Secrets")
else:
    db_url = st.sidebar.text_input("Masukkan Connection String:", type="password")

@st.cache_resource
def get_engine(connection_string):
    if not connection_string: return None
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
st.title("Dashboard Data Warehouse Jadwal Kuliah")

if is_connected and engine:
    
    # --- FILTER ---
    st.sidebar.divider()
    st.sidebar.header("Filter Data")
    
    try:
        # Load filter dari DB
        df_ta = pd.read_sql("SELECT DISTINCT tahun_ajaran FROM dim_waktu ORDER BY tahun_ajaran DESC", engine)
        list_ta = df_ta['tahun_ajaran'].tolist()
        
        df_sem = pd.read_sql("SELECT DISTINCT semester FROM dim_waktu ORDER BY semester", engine)
        list_sem = df_sem['semester'].tolist()
        
        selected_ta = st.sidebar.selectbox("Pilih Tahun Ajaran:", list_ta)
        selected_sem = st.sidebar.selectbox("Pilih Semester:", list_sem)
        
    except Exception as e:
        st.error("Gagal memuat filter. Pastikan tabel dim_waktu sudah ada.")
        selected_ta = None
        selected_sem = None

    # Tab Navigasi
    tab1, tab2, tab3, tab4 = st.tabs(["Visualisasi Metrik", "SQL Terminal", "Star Schema", "Info"])

    # === TAB 1: VISUALISASI ===
    with tab1:
        if selected_ta and selected_sem:
            st.header(f"Analisis: {selected_ta} - {selected_sem}")
            
            col1, col2 = st.columns(2)
            
    # --- CHART 1: Beban SKS Dosen ---
            with col1:
                st.subheader("Top 10 Dosen (Total SKS)")
                st.caption("Total SKS dari mata kuliah unik yang diajar.")
                query_dosen = text("""
                SELECT 
                    d.nama_dosen, 
                    SUM(unik.sks) as total_sks
                FROM (
                    -- Subquery: Ambil kombinasi unik (Dosen + MK + Kelas)
                    SELECT DISTINCT 
                        f.id_dosen,
                        f.id_mk,
                        f.id_kelas,
                        mk.sks
                    FROM fact_table f
                    JOIN dim_waktu w ON f.id_waktu = w.id_waktu
                    JOIN dim_matakuliah mk ON f.id_mk = mk.id_mk
                    WHERE w.tahun_ajaran = :ta 
                      AND w.semester = :sem
                      AND mk.jenis_matakuliah = 'TETAP' -- Sesuaikan dengan data ('REGULER'/'TETAP')
                ) unik
                JOIN dim_dosen d ON unik.id_dosen = d.id_dosen
                GROUP BY d.nama_dosen
                ORDER BY total_sks DESC
                LIMIT 10;
                """)
                
                try:
                    df_dosen = pd.read_sql(query_dosen, engine, params={"ta": selected_ta, "sem": selected_sem})
                    if not df_dosen.empty:
                        fig_dosen = px.bar(df_dosen, x='nama_dosen', y='total_sks', color='total_sks',
                                           labels={'total_sks': 'SKS', 'nama_dosen': 'Nama Dosen'}, text_auto=True)
                        st.plotly_chart(fig_dosen, use_container_width=True)
                    else:
                        st.info("Tidak ada data untuk periode ini.")
                except Exception as e: st.error(f"Error query dosen: {e}")
                    
            # CHART 2: Kesibukan Hari
            with col2:
                st.subheader("Pola Kesibukan Harian")
                q_hari = text("""
                SELECT 
                    w.hari, 
                    COUNT(*) as jumlah_sesi
                FROM fact_table f
                JOIN dim_waktu w ON f.id_waktu = w.id_waktu
                WHERE w.tahun_ajaran = :ta AND w.semester = :sem
                GROUP BY w.hari
                ORDER BY CASE WHEN w.hari='Senin' THEN 1 WHEN w.hari='Selasa' THEN 2 
                WHEN w.hari='Rabu' THEN 3 WHEN w.hari='Kamis' THEN 4 
                WHEN w.hari='Jumat' THEN 5 ELSE 6 END;
                """)
                try:
                    df_hari = pd.read_sql(q_hari, engine, params={"ta": selected_ta, "sem": selected_sem})
                    if not df_hari.empty:
                        fig = px.pie(df_hari, values='jumlah_sesi', names='hari', hole=0.4)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Data kosong.")
                except Exception as e: st.error(f"Error: {e}")

            # CHART 3: Ruangan
            st.subheader("Top 15 Penggunaan Ruangan")
            q_ruang = text("""
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
                df_ruang = pd.read_sql(q_ruang, engine, params={"ta": selected_ta, "sem": selected_sem})
                if not df_ruang.empty:
                    fig = px.bar(df_ruang, x='nama_ruangan', y='frekuensi_pakai', text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e: st.error(f"Error: {e}")

    # === TAB 2: SQL RUNNER  ===
    with tab2:
        st.header("SQL Terminal")
        st.write("Query manual untuk eksplorasi data.")
        
        default_q = "SELECT d.nama_dosen, SUM(f.beban_sks_dosen) AS total_sks_beban FROM fact_table f JOIN dim_dosen d ON f.id_dosen = d.id_dosen JOIN dim_waktu w ON f.id_waktu = w.id_waktu WHERE w.tahun_ajaran = '25/26' AND w.semester = 'Ganjil' GROUP BY d.nama_dosen ORDER BY total_sks_beban DESC LIMIT 20;SELECT d.nama_dosen, SUM(f.beban_sks_dosen) AS total_sks_beban FROM fact_table f JOIN dim_dosen d ON f.id_dosen = d.id_dosen JOIN dim_waktu w ON f.id_waktu = w.id_waktu WHERE w.tahun_ajaran = '25/26' AND w.semester = 'Ganjil' GROUP BY d.nama_dosen ORDER BY total_sks_beban DESC LIMIT 20;"
        sql_input = st.text_area("Query SQL:", value=default_q, height=150)
        
        if st.button("Run!"):
            try:
                res = pd.read_sql(sql_input, engine)
                st.success(f"Hasil: {len(res)} baris.")
                st.dataframe(res, use_container_width=True)
            except Exception as e:
                st.error(f"Error: {e}")

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
            DIM_DOSEN {
                int id_dosen PK
                string kode_dosen
                string nama_dosen
            }
            DIM_MATAKULIAH {
                int id_mk PK
                string kode_mk
                string nama_mk
                string jenis_matakuliah
                int sks
            }
            DIM_RUANGAN {
                int id_ruangan PK
                string nama_ruangan
                string gedung
                string lantai
            }
            DIM_KELAS {
                int id_kelas PK
                string nama_kelas
                string prodi
                string angkatan
            }
            DIM_WAKTU {
                int id_waktu PK
                string tahun_ajaran
                string semester
                string hari
                string jam_mulai
            }

            DIM_DOSEN ||--|{ FACT_TABLE : "mengajar"
            DIM_MATAKULIAH ||--|{ FACT_TABLE : "memiliki"
            DIM_RUANGAN ||--|{ FACT_TABLE : "ditempati"
            DIM_KELAS ||--|{ FACT_TABLE : "menghadiri"
            DIM_WAKTU ||--|{ FACT_TABLE : "terjadi_pada"
        """
        render_mermaid(schema_diagram)
        
    # === TAB 4: INFO STRUKTUR ===
    with tab4:
        st.markdown("""
        ### Struktur Data Warehouse
        Sistem ini menggunakan **Star Schema** yang terdiri dari:
        
        1.  **Fact Table (`fact_table`)**: Menyimpan data transaksi jadwal perkuliahan.
            * *Granularity*: Satu baris per sesi pertemuan mata kuliah unik.
        2.  **Dimension Tables**:
            * `dim_dosen`: Menyimpan profil dosen.
            * `dim_matakuliah`: Menyimpan detail mata kuliah (termasuk pemisahan jenis Reguler/Responsi).
            * `dim_ruangan`: Menyimpan lokasi fisik (Gedung, Lantai).
            * `dim_waktu`: Menyimpan atribut waktu (Tahun Ajaran, Semester, Hari, Jam).

        Filenya di github btw: **https://github.com/Dexiusss/Datawarehouse-Jadwal-FIF-Telkom-University**
        Database akses bisa request aja
        
        """)

else:
    st.info("Silakan hubungkan database di sidebar sebelah kiri.")









