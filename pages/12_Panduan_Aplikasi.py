
from __future__ import annotations
import streamlit as st

st.title("📘 Panduan Aplikasi Koridor Prioritas")
st.info("Panduan ini mengikuti struktur menu baru: menu Pengguna untuk membaca hasil, menu Admin untuk upload, validasi, rumus, scoring, dan query teknis.")

st.header("1. Peta Menu Aplikasi")
st.markdown("""
```text
👤 Pengguna
├── 🛣️ Dashboard
├── 🔎 Detail Koridor
└── 📘 Panduan Aplikasi

🔐 Admin
├── 📤 Upload Data
├── 🧪 Validasi Data
├── 🧮 Rumus Perhitungan
├── ⚖️ Scoring
└── 🦆 Query DuckDB
```
""")

st.header("2. Alur kerja yang benar")
st.markdown("""
1. Admin membuka **Upload Data** dan mengunggah Excel agregasi koridor.
2. Admin membuka **Validasi Data** untuk memeriksa data kosong, biaya 0, KML kosong, tematik kosong, dan mismatch kondisi jalan.
3. Admin membuka **Rumus Perhitungan** untuk mengatur bobot, rumus internal, kebijakan penalti, fallback KML/KMZ, dan biaya berbasis kondisi.
4. Admin klik **Simpan + Hitung Ulang** atau membuka menu **Scoring** untuk menghitung ulang ranking.
5. Pengguna membuka **Dashboard** untuk membaca ranking, filter, rekap, query builder, dan export.
6. Pengguna membuka **Detail Koridor** untuk audit satu koridor secara rinci.
""")

st.header("3. Menu Pengguna")
with st.expander("👤 Dashboard", expanded=True):
    st.markdown("""
    Menu ini dipakai untuk membaca hasil akhir. Fitur utamanya:
    - **Filter sidebar**: provinsi, kabupaten/kota, kategori, tematik, jenis produksi, rentang final score, pencarian teks.
    - **Overview**: grafik top ranking, komposisi kategori, rekap provinsi, koridor penalti tertinggi, dan biaya aktif 0.
    - **Ranking**: daftar urutan dan nilai setiap koridor. Kolom bisa dipilih.
    - **Komponen Skor**: melihat kontribusi setiap parameter terhadap skor.
    - **Rekap Wilayah**: rekap per provinsi, kabupaten/kota, atau gabungan.
    - **Query Builder**: filter angka dan teks tanpa SQL.
    - **Export**: download CSV/Excel hasil filter.

    Hint: filter sidebar memengaruhi semua tab dan file export. Kalau data terlihat sedikit, cek dulu apakah ada filter yang masih aktif.
    """)

with st.expander("🔎 Detail Koridor", expanded=False):
    st.markdown("""
    Menu ini untuk melihat satu koridor. Cocok untuk menjawab:
    - kenapa ranking koridor tinggi/rendah;
    - parameter mana yang paling menaikkan skor;
    - apakah penalti data menurunkan skor;
    - biaya aktif berasal dari Excel atau hitungan kondisi jalan;
    - panjang KML/KMZ memakai data asli atau fallback panjang koridor.

    Nilai angka di menu ini sudah memakai format Indonesia: ribuan titik, desimal koma, dan persen bila kolom memang persentase.
    """)

st.header("4. Menu Admin")
with st.expander("📤 Upload Data", expanded=False):
    st.markdown("""
    Upload Excel agregasi koridor. Setelah diproses, aplikasi menyimpan:
    - `data/processed/koridor_raw.parquet` sebagai data mentah;
    - `data/processed/koridor_score.parquet` sebagai hasil scoring.

    Hint: file sebaiknya sudah level koridor. Jika masih level ruas, data produksi/fasilitas bisa dobel hitung.
    """)

with st.expander("🧪 Validasi Data", expanded=False):
    st.markdown("""
    Menu ini membaca kualitas data sesuai setting terbaru di **Rumus Perhitungan**. Contoh catatan:
    - panjang koridor kosong/0;
    - biaya aktif kosong/0;
    - nama koridor kosong;
    - panjang KML/KMZ kosong;
    - total kondisi jalan tidak sama dengan panjang koridor;
    - tematik kosong.

    Catatan validasi bukan selalu salah. Contoh: jika KML/KMZ diatur memakai fallback panjang koridor, aplikasi akan menunjukkan perlakuan khusus itu.
    """)

with st.expander("🧮 Rumus Perhitungan", expanded=True):
    st.markdown("""
    Menu ini mengatur logika scoring. Bagian penting:

    **A. Kebijakan awal perhitungan**
    - Penalti kualitas data aktif/tidak.
    - KML/KMZ kosong: dipenalti, diabaikan, atau memakai panjang koridor.
    - Kondisi jalan: angka mentah atau dinormalisasi terhadap panjang koridor.
    - Biaya: dari Excel, dari kondisi jalan, atau fallback jika Excel kosong.
    - Nama koridor kosong: wajib atau pakai No. Koridor.
    - Tematik kosong: hanya skor turun atau skor turun + penalti.

    **B. Editor Rumus / Parameter**
    - `active`: parameter ikut dinilai atau tidak.
    - `weight`: bobot parameter. Total bobot tidak wajib 100 karena otomatis dinormalisasi.
    - `formula_type`: jenis rumus.
    - `source_columns`: kolom yang dibaca.
    - `settings_json`: angka internal rumus.

    Contoh mengubah rumus kondisi jalan:
    ```json
    {"weights":{"persen_rusak_berat":1.3,"persen_rusak_ringan":0.7,"persen_sedang":0.15},"clip_min":0,"clip_max":100}
    ```

    **C. Editor Penalti**
    Penalti mengurangi `final_score` bila data kosong/tidak wajar.

    Hint: format `settings_json` harus JSON valid. Pakai tanda kutip dua `"`, bukan kutip satu `'`.
    """)

with st.expander("⚖️ Scoring", expanded=False):
    st.markdown("""
    Menu ini menghitung ulang ranking dari data raw + konfigurasi rumus yang tersimpan.

    Gunakan menu ini bila:
    - baru upload data;
    - baru mengubah rumus;
    - baru mengubah penalti;
    - ranking di dashboard belum berubah setelah edit.
    """)

with st.expander("🦆 Query DuckDB", expanded=False):
    st.markdown("""
    Menu ini untuk admin/pengolah data yang ingin SQL langsung ke file Parquet.

    Contoh:
    ```sql
    SELECT Provinsi, COUNT(*) AS jumlah_koridor, AVG(final_score) AS avg_score
    FROM read_parquet('data/processed/koridor_score.parquet')
    GROUP BY Provinsi
    ORDER BY avg_score DESC;
    ```

    Hint: jika nama kolom mengandung spasi, gunakan tanda kutip ganda pada SQL.
    """)

st.header("5. Format angka yang digunakan")
st.markdown("""
Tampilan aplikasi memakai format Indonesia:

| Jenis nilai | Contoh tampilan |
|---|---|
| Ribuan | `12.345` |
| Desimal | `12.345,67` |
| Persen | `45,25%` |
| Panjang | `1.234,56` km |
| Biaya | `1.234,56` Rp miliar |
| Score | `78,25` |

Catatan: data asli di Parquet dan hasil export tetap numerik agar bisa dihitung lagi. Format Indonesia hanya untuk tampilan layar.
""")

st.header("6. Cara membaca final score")
st.code("final_score = raw_score - (data_quality_penalty × penalty_factor)")
st.markdown("""
- `raw_score`: gabungan semua parameter aktif.
- `data_quality_penalty`: penalti kualitas data.
- `penalty_factor`: pengali penalti, misalnya 0,30.
- `final_score`: skor akhir untuk ranking.

Jika penalti kualitas data dimatikan, rumus menjadi:
```text
final_score = raw_score
```
Namun parameter kosong tetap bisa membuat skor parameter tersebut menjadi 0.
""")

st.header("7. Checklist sebelum ranking dipakai")
st.markdown("""
Sebelum ranking dipakai untuk bahan keputusan, cek minimal:
1. Apakah biaya aktif masih banyak yang 0?
2. Apakah tematik kosong masih banyak?
3. Apakah panjang kondisi sudah normal terhadap panjang koridor?
4. Apakah KML/KMZ kosong memang ingin diabaikan atau memakai panjang koridor?
5. Apakah top 20 masuk akal secara teknis, ekonomi, konektivitas, dan layanan publik?
""")
