# Aplikasi Penilaian Koridor Prioritas v5.2

Versi ini menambahkan scoring **Ekonomi Komoditas**:

- Jenis Produksi 1-4 bisa diberi bobot berbeda.
- Jumlah Produksi 1-4 ikut dinilai sebagai produksi tertimbang komoditas.
- Luas Lahan 1-4 ikut dinilai sebagai lahan tertimbang komoditas.
- Dashboard menampilkan rekap jenis produksi.
- Detail Koridor menampilkan ringkasan ekonomi komoditas.

Contoh bobot komoditas di `settings_json`:

```json
{"commodity_weights":{"Padi":1.5,"Jagung":1.2,"Kelapa Sawit":1.15},"default_weight":1.0,"cap_quantile":0.95,"missing_score":0}
```

Jalankan lokal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Deploy Streamlit Cloud:

- Repository: `jalandaerah/koridor-prioritas-app`
- Branch: `main`
- Main file path: `app.py`
