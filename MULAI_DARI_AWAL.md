# Koridor Prioritas App - Instalasi Bersih

Paket ini dibuat untuk instalasi bersih. Jangan ditimpa ke folder lama.

## Struktur menu

👤 Pengguna
- Dashboard
- Detail Koridor
- Panduan Aplikasi

🔐 Admin
- Upload Data
- Validasi Data
- Rumus Perhitungan
- Scoring
- Query DuckDB

## Instalasi cepat Windows

1. Rename folder lama:
   `C:\koridor_prioritas_app` menjadi `C:\koridor_prioritas_app_lama`

2. Ekstrak ZIP ini langsung ke drive C sehingga menjadi:
   `C:\koridor_prioritas_app_fresh_v5`

3. Buka PowerShell di folder aplikasi:
   `cd C:\koridor_prioritas_app_fresh_v5`

4. Jalankan:
   `python -m venv .venv`
   `.\.venv\Scripts\Activate.ps1`
   `pip install -r requirements.txt`
   `streamlit run app.py`

5. Upload ulang Excel dari menu Admin → Upload Data.

## Catatan penting

- Jangan copy file satu per satu dari folder lama.
- Jangan campur folder pages lama dengan pages baru.
- File wajib ada: `scoring/formatting.py`.
- File pages hanya boleh berisi:
  - `10_Dashboard_Pengguna.py`
  - `11_Detail_Koridor.py`
  - `12_Panduan_Aplikasi.py`
  - `90_Upload_Data.py`
  - `91_Validasi_Data.py`
  - `92_Rumus_Perhitungan.py`
  - `93_Scoring.py`
  - `94_Query_DuckDB.py`
