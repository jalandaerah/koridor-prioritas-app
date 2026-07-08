
# Aplikasi Penilaian Koridor Prioritas v4

Versi ini menambahkan:

- Pemisahan menu menjadi **Pengguna** dan **Admin**.
- Format tampilan angka Indonesia: ribuan titik, desimal koma, persen, dan satuan lebih konsisten.
- Panduan aplikasi yang mengikuti peta menu baru.
- Dashboard pengguna tetap berisi ranking, komponen skor, rekap wilayah, query builder, dan export.
- Admin tetap mengelola upload data, validasi, rumus scoring, scoring ulang, dan SQL DuckDB.

## Cara menjalankan

```powershell
cd C:\koridor_prioritas_app
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Jika sidebar menu tidak berkelompok, upgrade Streamlit:

```powershell
pip install --upgrade streamlit
```

## Struktur menu

```text
Pengguna
- Dashboard
- Detail Koridor
- Panduan Aplikasi

Admin
- Upload Data
- Validasi Data
- Rumus Perhitungan
- Scoring
- Query DuckDB
```
