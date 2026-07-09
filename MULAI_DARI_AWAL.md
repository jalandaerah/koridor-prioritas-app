# Mulai dari Awal v5.3

1. Ekstrak ZIP ke folder baru.
2. Jalankan PowerShell di folder aplikasi.
3. Buat environment dan install dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

4. Upload Excel di **Admin → Upload Data**.
5. Cek kualitas data di **Admin → Validasi Data**.
6. Cek dan atur rumus di **Admin → Rumus Perhitungan**.
7. Klik **Simpan + Hitung Ulang**.
8. Baca hasil di **Pengguna → Dashboard**.
9. Audit satu koridor di **Pengguna → Detail Koridor**.
10. Baca penjelasan rumus yang sedang dipakai di **Pengguna → Rumus Aktif**.

Menu baru v5.3:

```text
👤 Pengguna
├── Dashboard
├── Detail Koridor
├── Panduan Aplikasi
└── Rumus Aktif
```
