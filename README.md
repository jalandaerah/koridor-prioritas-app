# Aplikasi Penilaian Koridor Prioritas v5.5

Versi ini menambahkan/perbaiki:

- Perbaikan format kolom **Jenis Produksi** agar nama komoditas seperti Padi, Jagung, Kelapa Sawit tidak berubah menjadi tanda `-`.
- Grafik jenis produksi di Dashboard: total produksi, luas lahan, jumlah koridor, dan rata-rata final score.
- Rekap jenis produksi juga muncul di tab Rekap Wilayah.
- Panduan aplikasi diperbarui untuk menjelaskan grafik jenis produksi dan cara membaca ekonomi komoditas.
- Tetap mempertahankan fitur v5.4: threshold kategori bisa diubah, dashboard tidak cache scoring lama, biaya aktif mengikuti mode biaya terakhir setelah Simpan + Hitung Ulang.

## Update GitHub cepat

Jika folder GitHub aktif adalah `C:\koridor_prioritas_app_fresh_v5` dan hasil ekstrak v5.5 adalah `C:\koridor_prioritas_app_fresh_v5_5`, jalankan:

```powershell
cd C:\koridor_prioritas_app_fresh_v5

Remove-Item .\pages -Recurse -Force
Remove-Item .\scoring -Recurse -Force
Remove-Item .\config -Recurse -Force
Remove-Item .\scripts -Recurse -Force

Copy-Item C:\koridor_prioritas_app_fresh_v5_5\pages .\pages -Recurse -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\scoring .\scoring -Recurse -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\config .\config -Recurse -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\scripts .\scripts -Recurse -Force

Copy-Item C:\koridor_prioritas_app_fresh_v5_5\app.py .\app.py -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\requirements.txt .\requirements.txt -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\runtime.txt .\runtime.txt -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\README.md .\README.md -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\MULAI_DARI_AWAL.md .\MULAI_DARI_AWAL.md -Force
Copy-Item C:\koridor_prioritas_app_fresh_v5_5\02_CEK_STRUKTUR.ps1 .\02_CEK_STRUKTUR.ps1 -Force

git add .
git commit -m "Update v5.5 grafik jenis produksi"
git push origin main
```

Setelah push, reboot app di Streamlit Cloud bila rebuild tidak otomatis.

## Setelah update

1. Upload ulang Excel dari Admin → Upload Data.
2. Admin → Rumus Perhitungan → Simpan + Hitung Ulang.
3. Buka Pengguna → Dashboard.
4. Cek bagian **Rekap dan Grafik Jenis Produksi**.
