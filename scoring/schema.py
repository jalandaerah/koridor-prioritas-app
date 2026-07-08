from __future__ import annotations

COL = {
    "id_koridor": "ID Koridor",
    "provinsi": "Provinsi",
    "kabupaten": "Kabupaten/Kota",
    "no_koridor": "No. Koridor",
    "nama_koridor": "Nama Koridor",
    "rpjmn": "RPJMN",
    "tematik": "Tematik",
    "kspp": "KSPP",
    "jenis_produksi": "Jenis Produksi",
    "status_pengajuan": "Status Pengajuan",
    "panjang": "Panjang (KM)",
    "baik": "Baik",
    "sedang": "Sedang",
    "rusak_ringan": "Rusak Ringan",
    "rusak_berat": "Rusak Berat",
    "biaya": "Biaya (Rp Miliar)",
    "simpul": "Status Konektivitas - Terhubung ke Simpul Transportasi",
    "pusat": "Status Konektivitas - Terhubung ke pusat kegiatan (PKN/PKW)",
    "koridor_utama": "Status Konektivitas - Terhubung ke koridor utama lainnya",
    "pendidikan": "Faslilitas Umum Dilewati - Pendidikan",
    "kesehatan": "Faslilitas Umum Dilewati - Kesehatan",
    "pemerintahan": "Faslilitas Umum Dilewati - Pemerintahan",
    "sppg": "Faslilitas Umum Dilewati - SPPG",
    "prioritas_kab": "Prioritas Kabupaten/Kota",
    "prioritas_prov": "Prioritas Provinsi",
    "koridor_awal": "Koridor Awal",
    "panjang_kml": "Panjang KML/KMZ (KM)",
    "baik_kml": "Baik KML/KMZ",
    "sedang_kml": "Sedang KML/KMZ",
    "rr_kml": "Rusak Ringan KML/KMZ",
    "rb_kml": "Rusak Berat KML/KMZ",
    "hari_jalan": "Beririsan dengan Program Hari Jalan",
    "diskresi": "Beririsan dengan Diskresi Menteri",
    "rujj": "Beririsan dengan Rencana Umum Jaringan Jalan",
}

PRODUCTION_AMOUNT_COLS = [
    "Jumlah Produksi 1 (Ton/Tahun)",
    "Jumlah Produksi 2 (Ton/Tahun)",
    "Jumlah Produksi 3 (Ton/Tahun)",
    "Jumlah Produksi 4 (Ton/Tahun)",
]

LAND_AREA_COLS = [
    "Luas Lahan 1 (Ha)",
    "Luas Lahan 2 (Ha)",
    "Luas Lahan 3 (Ha)",
    "Luas Lahan 4 (Ha)",
]

NUMERIC_COLS = [
    COL["panjang"], COL["baik"], COL["sedang"], COL["rusak_ringan"], COL["rusak_berat"], COL["biaya"],
    COL["pendidikan"], COL["kesehatan"], COL["pemerintahan"], COL["sppg"],
    COL["prioritas_kab"], COL["prioritas_prov"], COL["panjang_kml"],
    *PRODUCTION_AMOUNT_COLS, *LAND_AREA_COLS,
]

REQUIRED_COLS = [
    COL["id_koridor"], COL["provinsi"], COL["kabupaten"], COL["no_koridor"], COL["nama_koridor"],
    COL["panjang"], COL["baik"], COL["sedang"], COL["rusak_ringan"], COL["rusak_berat"], COL["biaya"],
]
