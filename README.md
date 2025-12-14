# 📊 Data Warehouse & Dashboard Jadwal Kuliah FIF Telkom University

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://datawarehouse-jadwal-fif-telkom-university.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?logo=postgresql&logoColor=white)
![ETL Status](https://img.shields.io/badge/ETL-Multi--Semester-green)

Proyek ini adalah implementasi *Data Warehouse* *end-to-end* untuk menganalisis data jadwal perkuliahan di Fakultas Informatika (FIF), Telkom University.

## 🚀 Demo

Akses Dashboard interaktif secara langsung melalui link berikut:

### 👉 [*Buka Dashboard Data Warehouse*](https://datawarehouse-jadwal-fif-telkom-university.streamlit.app) 👈


## 🏗️ Arsitektur Sistem

Proyek ini menggunakan pendekatan *Star Schema* untuk pemodelan datanya:

### Tech Stack
* *ETL (Extract, Transform, Load):* Python (`Pandas`, `OpenPyxl`).
* *Database:* PostgreSQL (Cloud Hosting by *Neon*).
* *Visualization:* Streamlit & Plotly.
* *Containerization (Dev):* Docker & Docker Compose.

### Skema Database
* *Fact Table:* `fact_table` (Menyimpan metrik SKS, frekuensi, dan foreign keys).
* *Dimensions:*
    * `dim_dosen`: Informasi detail dosen (Kode, Nama, JFA).
    * `dim_matakuliah`: Detail mata kuliah dan jenisnya (Reguler/Responsi).
    * `dim_ruangan`: Gedung dan Lantai.
    * `dim_kelas`: Program Studi dan Angkatan.
    * `dim_waktu`: Tahun Ajaran, Semester, Hari, dan Shift.

---

## 📂 Struktur Project

```text
/
├── .streamlit/             # Konfigurasi secrets (Tidak di-upload)
├── dashboard.py            # Main application code (Streamlit)
├── etl_multisemester.py    # Script ETL utama (Python)
├── requirements.txt        # Dependencies library
├── docker-compose.yml      # Konfigurasi Docker lokal
├── kode_dosen_data.csv     # Data referensi nama dosen
└── Jadwal Kuliah FIF.xlsx  # Data mentah jadwal (Source)

*untuk program ETL, DDL, Database SQL bisa kontak aja*
