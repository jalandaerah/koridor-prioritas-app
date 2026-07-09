# Aplikasi Penilaian Koridor Prioritas v5.3

Versi ini menambahkan penyempurnaan panduan dan audit rumus:

- Menu baru **Pengguna → Rumus Aktif** untuk membaca rumus scoring yang sedang dipakai.
- Panduan aplikasi diperluas: alur kerja, peta menu, cara membuat rumus baru, contoh formula_type, contoh settings_json, ekonomi komoditas, dan checklist audit.
- Menu **Admin → Rumus Perhitungan** ditambah expander panduan cepat membuat rumus baru.
- Scoring ekonomi komoditas v5.2 tetap ada: jenis produksi, jumlah produksi, dan luas lahan bisa dibobotkan berdasarkan jenis komoditas.

## Deploy Streamlit Cloud

- Repository: `jalandaerah/koridor-prioritas-app`
- Branch: `main`
- Main file path: `app.py`

## Update dari folder lokal ke GitHub

Jika folder ini sudah menjadi folder kerja repo GitHub:

```powershell
git add .
git commit -m "Update v5.3 panduan rumus aktif"
git push origin main
```

Jika folder ini belum punya remote GitHub, copy isinya ke folder repo lama atau tambahkan remote sesuai repo Bapak.

## Menjalankan lokal

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Catatan

Data upload dan hasil scoring di folder `data/processed` tidak perlu ikut GitHub. Upload ulang Excel di aplikasi online setelah redeploy.
