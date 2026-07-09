from __future__ import annotations
import streamlit as st

st.title("📘 Panduan Aplikasi Koridor Prioritas")
st.info("Panduan ini menjelaskan alur kerja aplikasi, fungsi setiap menu, cara membaca dashboard, cara membuat rumus baru, dan cara menjaga hasil ranking tetap bisa diaudit.")

st.header("1. Peta Menu Aplikasi")
st.markdown("""
```text
👤 Pengguna
├── 🛣️ Dashboard
├── 🔎 Detail Koridor
├── 📘 Panduan Aplikasi
└── 📑 Rumus Aktif

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
1. **Admin → Upload Data**: unggah Excel agregasi koridor.
2. **Admin → Validasi Data**: cek data kosong, panjang 0, biaya 0, mismatch kondisi, KML/KMZ, tematik kosong, dan masalah lain.
3. **Admin → Rumus Perhitungan**: atur kebijakan awal, bobot parameter, rumus internal, penalti, bobot komoditas, sumber biaya, dan threshold kategori prioritas.
4. Klik **Simpan + Hitung Ulang**, atau buka **Admin → Scoring** untuk menghitung ulang ranking.
5. **Pengguna → Dashboard**: baca ranking, filter wilayah, komponen skor, rekap, query builder, dan export.
6. **Pengguna → Detail Koridor**: audit satu koridor.
7. **Pengguna → Rumus Aktif**: baca penjelasan rumus yang sedang dipakai tanpa mengubah konfigurasi.
""")

st.warning("Ranking pertama setelah upload jangan langsung dianggap final. Cek validasi, bobot rumus, biaya aktif, dan top ranking dulu.")

st.header("3. Penjelasan menu Pengguna")
with st.expander("🛣️ Dashboard", expanded=True):
    st.markdown("""
    **Tujuan:** melihat hasil ranking dan melakukan eksplorasi cepat.

    Fitur utama:
    - filter provinsi, kabupaten/kota, kategori, tematik, jenis produksi, rentang final score, dan pencarian teks;
    - tab **Overview** untuk ringkasan umum;
    - tab **Ranking** untuk daftar urutan koridor;
    - tab **Komponen Skor** untuk melihat skor per parameter;
    - tab **Rekap Wilayah** untuk rekap provinsi/kabupaten dan rekap jenis produksi;
    - tab **Query Builder** untuk filter tanpa SQL;
    - tab **Export** untuk download hasil filter.

    Pada bagian **Rekap dan Grafik Jenis Produksi**, aplikasi membaca `Jenis Produksi 1-4`, `Jumlah Produksi 1-4`, dan `Luas Lahan 1-4`, lalu menampilkan grafik:
    - total produksi ton/tahun;
    - total luas lahan hektare;
    - jumlah koridor per jenis produksi;
    - rata-rata final score per jenis produksi.

    Hint: jika tabel kosong, biasanya karena filter masih aktif. Reset filter atau longgarkan rentang final score.
    """)

with st.expander("🔎 Detail Koridor", expanded=False):
    st.markdown("""
    **Tujuan:** audit satu koridor.

    Gunakan menu ini untuk menjawab:
    - mengapa koridor mendapat skor tinggi/rendah;
    - berapa `raw_score`, penalti, dan `final_score`;
    - biaya mana yang dipakai scoring: Excel atau kondisi jalan;
    - bagaimana kondisi jalan dinormalisasi;
    - apa saja jenis produksi, produksi tertimbang, dan luas lahan tertimbang;
    - parameter mana yang paling besar kontribusinya.

    Hint: baca **Biaya Aktif**, bukan biaya Excel mentah, karena biaya aktif adalah biaya yang dipakai scoring.
    """)

with st.expander("📑 Rumus Aktif", expanded=False):
    st.markdown("""
    **Tujuan:** membaca rumus scoring yang sedang berlaku dengan bahasa yang lebih mudah.

    Menu ini berisi:
    - daftar parameter aktif;
    - bobot asli dan bobot normalisasi;
    - tipe skor yang dipakai;
    - kolom sumber;
    - settings_json yang sedang berlaku;
    - penjelasan ekonomi komoditas;
    - daftar penalti data;
    - threshold kategori prioritas;
    - audit hasil scoring.

    Hint: menu ini hanya untuk membaca. Mengubah rumus dilakukan di **Admin → Rumus Perhitungan**.
    """)

st.header("4. Penjelasan menu Admin")
with st.expander("📤 Upload Data", expanded=False):
    st.markdown("""
    **Tujuan:** memasukkan Excel agregasi koridor ke aplikasi.

    File yang ideal adalah file level koridor, bukan level ruas. Jika file masih level ruas, fasilitas, produksi, luas lahan, dan biaya bisa dobel hitung.

    Setelah upload, aplikasi menyimpan:
    - `data/processed/koridor_raw.parquet` untuk data mentah;
    - `data/processed/koridor_score.parquet` untuk hasil scoring setelah dihitung.

    Hint: di Streamlit Cloud gratis, file upload bisa hilang saat app reboot. Untuk uji rumus tidak masalah, untuk produksi perlu storage permanen.
    """)

with st.expander("🧪 Validasi Data", expanded=False):
    st.markdown("""
    **Tujuan:** menemukan masalah data sebelum ranking dipercaya.

    Contoh validasi:
    - nama koridor kosong;
    - panjang koridor kosong/0;
    - biaya aktif 0;
    - total kondisi jalan tidak sama dengan panjang;
    - panjang KML/KMZ kosong;
    - tematik kosong;
    - data produksi/lahan kosong.

    Catatan validasi bukan selalu kesalahan mutlak. Beberapa bisa dikesampingkan lewat kebijakan di **Rumus Perhitungan**, misalnya KML kosong boleh memakai Panjang Koridor.
    """)

with st.expander("🧮 Rumus Perhitungan", expanded=True):
    st.markdown("""
    **Tujuan:** mengatur semua logika scoring.

    Bagian penting:
    - **Kebijakan awal perhitungan**: penalti aktif/tidak, fallback KML/KMZ, normalisasi kondisi, sumber biaya, nama koridor kosong, tematik kosong.
    - **Threshold Kategori Prioritas**: batas Rendah/Sedang/Tinggi/Sangat Tinggi yang dipakai setelah `final_score` dihitung.
    - **Editor Rumus / Parameter**: daftar parameter penilaian.
    - **Editor Penalti**: aturan pengurang skor akhir.

    Kolom penting di editor rumus:
    | Kolom | Fungsi |
    |---|---|
    | `id` | Kode unik parameter. Jangan pakai spasi. Contoh: `sppg`, `biaya_per_km`. |
    | `active` | Centang jika parameter ikut dinilai. |
    | `group` | Kelompok indikator, misalnya Ekonomi, Kondisi, Konektivitas. |
    | `name` | Nama yang tampil di dashboard. |
    | `formula_type` | Jenis rumus. Pilih dari daftar yang tersedia. |
    | `source_columns` | Kolom sumber dari Excel/hasil olahan. Jika lebih dari satu, pisahkan koma. |
    | `weight` | Bobot parameter. Total bobot tidak wajib 100 karena sistem menormalkan otomatis. |
    | `cap_quantile` | Batas potong outlier untuk normalisasi angka. Umumnya 0,95. |
    | `settings_json` | Pengaturan internal rumus dalam format JSON. |
    | `description` | Catatan penjelasan parameter. |
    """)

with st.expander("⚖️ Scoring", expanded=False):
    st.markdown("""
    **Tujuan:** menghitung ulang ranking dari data dan konfigurasi terakhir.

    Gunakan menu ini setelah:
    - upload data baru;
    - mengubah bobot;
    - mengubah `settings_json`;
    - mengubah penalti;
    - mengubah biaya berbasis kondisi;
    - mengubah bobot komoditas;
    - mengubah threshold kategori prioritas.
    """)

with st.expander("🦆 Query DuckDB", expanded=False):
    st.markdown("""
    **Tujuan:** analisis SQL langsung untuk admin/data analyst.

    Contoh query:
    ```sql
    SELECT Provinsi, COUNT(*) AS jumlah_koridor, AVG(final_score) AS avg_score
    FROM read_parquet('data/processed/koridor_score.parquet')
    GROUP BY Provinsi
    ORDER BY avg_score DESC;
    ```

    Hint: jika nama kolom mengandung spasi, gunakan tanda kutip ganda. Contoh: `"Panjang (KM)"`.
    """)

st.header("5. Cara membuat rumus baru di editor rumus")
st.markdown("""
Ikuti urutan ini. Jangan langsung mengetik rumus bebas seperti Excel. Aplikasi memakai **tipe rumus terkendali** agar aman dan konsisten.

### Langkah A — Tentukan tujuan parameter
Contoh tujuan:
- menilai apakah koridor terhubung kawasan industri;
- menilai jumlah penduduk terlayani;
- menilai biaya per penerima manfaat;
- menilai jumlah SPPG;
- menilai produksi padi lebih tinggi dari jagung.

### Langkah B — Pastikan kolom sumber ada
Buka bagian **Kolom yang tersedia untuk rumus** di menu Rumus Perhitungan. Cari nama kolomnya. Nama kolom harus sama persis.

### Langkah C — Pilih `formula_type`
| Kondisi data | Pilih formula_type |
|---|---|
| Kolom berisi YA/TIDAK | `yes_no` |
| Kolom harus terisi | `exists` atau `completeness` |
| Angka besar lebih baik | `numeric_higher` |
| Angka kecil lebih baik | `numeric_lower` |
| Biaya kecil lebih baik, tapi 0/kosong tidak boleh bagus | `numeric_lower_positive` |
| Ranking angka kecil lebih baik | `rank_lower` |
| Beberapa kolom dijumlah dengan bobot | `weighted_sum_higher` |
| Kondisi RB/RR/Sedang | `weighted_percent_sum` |
| Produksi dikalikan bobot komoditas | `production_amount_by_type` |
| Luas lahan dikalikan bobot komoditas | `land_area_by_type` |
| Produksi + lahan + bobot komoditas | `production_land_by_type` |

### Langkah D — Isi baris baru
Contoh parameter jumlah SPPG:
```text
id             : sppg_khusus
group          : Fasilitas Publik
name           : Jumlah SPPG
formula_type   : numeric_higher
source_columns : Faslilitas Umum Dilewati - SPPG
weight         : 8
cap_quantile   : 0.95
settings_json  : {"cap_quantile":0.95,"missing_score":0}
description    : Semakin banyak SPPG dilayani, skor semakin tinggi.
```

### Langkah E — Klik Simpan + Hitung Ulang
Jika ada error JSON atau kolom sumber salah, aplikasi akan menolak simpan dan menampilkan pesan error.
""")

st.header("6. Contoh rumus baru siap copy")
with st.expander("Contoh 1 — Parameter YA/TIDAK: Kawasan Industri", expanded=False):
    st.code('''id             : kawasan_industri
group          : Ekonomi
name           : Terhubung Kawasan Industri
formula_type   : yes_no
source_columns : Kawasan Industri
weight         : 8
settings_json  : {"true_values":["YA","YES","Y","TRUE","1","ADA"],"true_score":100,"false_score":0}
description    : YA mendapat skor 100; selain itu 0.''')

with st.expander("Contoh 2 — Angka besar lebih baik: Penduduk Terlayani", expanded=False):
    st.code('''id             : penduduk_terlayani
group          : Pelayanan Publik
name           : Jumlah Penduduk Terlayani
formula_type   : numeric_higher
source_columns : Jumlah Penduduk Terlayani
weight         : 12
cap_quantile   : 0.95
settings_json  : {"cap_quantile":0.95,"missing_score":0}
description    : Semakin banyak penduduk terlayani, skor semakin tinggi.''')

with st.expander("Contoh 3 — Biaya kecil lebih baik: Biaya per Penerima Manfaat", expanded=False):
    st.code('''id             : biaya_per_penerima
group          : VfM
name           : Biaya per Penerima Manfaat
formula_type   : numeric_lower_positive
source_columns : Biaya per Penerima Manfaat
weight         : 10
cap_quantile   : 0.95
settings_json  : {"cap_quantile":0.95,"zero_or_missing_score":0}
description    : Biaya lebih rendah lebih baik; nilai 0/kosong diberi skor 0.''')

with st.expander("Contoh 4 — Fasilitas tertimbang", expanded=False):
    st.code('''id             : fasilitas_prioritas
group          : Fasilitas Publik
name           : Fasilitas Prioritas Tertimbang
formula_type   : weighted_sum_higher
source_columns : Faslilitas Umum Dilewati - Pendidikan, Faslilitas Umum Dilewati - Kesehatan, Faslilitas Umum Dilewati - SPPG
weight         : 12
cap_quantile   : 0.95
settings_json  : {"weights":{"Faslilitas Umum Dilewati - Pendidikan":1,"Faslilitas Umum Dilewati - Kesehatan":2,"Faslilitas Umum Dilewati - SPPG":4},"cap_quantile":0.95}
description    : Pendidikan x1, kesehatan x2, SPPG x4, lalu dinormalisasi 0-100.''')

with st.expander("Contoh 5 — Produksi berbobot komoditas", expanded=False):
    st.code('''id             : produksi_pangan_prioritas
group          : Ekonomi Komoditas
name           : Produksi Pangan Prioritas
formula_type   : production_amount_by_type
source_columns : Jenis Produksi 1, Jumlah Produksi 1 (Ton/Tahun), Jenis Produksi 2, Jumlah Produksi 2 (Ton/Tahun), Jenis Produksi 3, Jumlah Produksi 3 (Ton/Tahun), Jenis Produksi 4, Jumlah Produksi 4 (Ton/Tahun)
weight         : 10
cap_quantile   : 0.95
settings_json  : {"commodity_weights":{"Padi":1.8,"Jagung":1.3,"Kedelai":1.4,"Cabai":1.2},"default_weight":1.0,"cap_quantile":0.95,"missing_score":0}
description    : Jumlah produksi dikalikan bobot jenis komoditas, lalu dinormalisasi.''')

st.header("7. Aturan JSON yang wajib benar")
st.markdown("""
`settings_json` harus valid JSON.

Benar:
```json
{"commodity_weights":{"Padi":1.5,"Jagung":1.2},"default_weight":1.0}
```

Salah:
```text
{'commodity_weights': {'Padi': 1.5}}
```

Kesalahan umum:
- memakai kutip satu `'`, harus kutip dua `"`;
- ada koma terakhir sebelum `}`;
- nama kolom salah ketik;
- `formula_type` tidak sesuai pilihan;
- `weight` aktif semuanya 0.
""")

st.header("8. Cara membaca ekonomi komoditas dan grafik jenis produksi")
st.markdown("""
Parameter ekonomi komoditas membaca empat slot:

```text
Jenis Produksi 1 + Jumlah Produksi 1 + Luas Lahan 1
Jenis Produksi 2 + Jumlah Produksi 2 + Luas Lahan 2
Jenis Produksi 3 + Jumlah Produksi 3 + Luas Lahan 3
Jenis Produksi 4 + Jumlah Produksi 4 + Luas Lahan 4
```

Rumus produksi tertimbang:
```text
produksi_tertimbang = Σ(jumlah_produksi_i × bobot_jenis_produksi_i)
```

Rumus luas lahan tertimbang:
```text
lahan_tertimbang = Σ(luas_lahan_i × bobot_jenis_produksi_i)
```

Contoh:
```text
Padi 1.000 ton × 1,50 = 1.500
Jagung 1.000 ton × 1,20 = 1.200
```

Artinya jumlah produksi sama bisa menghasilkan skor berbeda bila jenis komoditasnya berbeda.

Di dashboard, rekap jenis produksi menampilkan nama komoditas sebagai teks. Jika sebelumnya muncul tanda `-`, penyebabnya adalah format tampilan lama membaca kolom `Jenis Produksi` sebagai angka karena ada kata `produksi` di nama kolom. Versi ini sudah memperbaikinya.

Cara membaca grafik jenis produksi:
- **Produksi**: menunjukkan komoditas dengan total produksi terbesar pada hasil filter.
- **Luas Lahan**: menunjukkan komoditas dengan cakupan lahan terbesar.
- **Jumlah Koridor**: menunjukkan berapa banyak koridor yang melayani komoditas tersebut.
- **Rata-rata Score**: menunjukkan rata-rata `final_score` koridor yang memiliki jenis produksi tersebut. Gunakan batas minimal jumlah koridor agar komoditas yang hanya muncul 1 kali tidak terlalu menyesatkan.
""")

st.header("9. Cara mengubah kategori Rendah/Sedang/Tinggi")
st.markdown("""
Kategori prioritas dibuat dari `final_score` memakai threshold. Default awal:

```text
Rendah        : final_score <= 50
Sedang        : 50 < final_score <= 65
Tinggi        : 65 < final_score <= 80
Sangat Tinggi : final_score > 80
```

Jika kategori terasa terlalu jomplang, buka:

```text
Admin → Rumus Perhitungan → Threshold Kategori Prioritas
```

Ubah tiga batas ini:

```text
Batas maksimum Rendah
Batas maksimum Sedang
Batas maksimum Tinggi
```

Syaratnya:

```text
0 <= Rendah < Sedang < Tinggi <= 100
```

Setelah mengubah threshold, wajib klik:

```text
Simpan + Hitung Ulang
```

Dashboard baru akan berubah setelah scoring ulang selesai. Jika hanya klik simpan tanpa hitung ulang, konfigurasi tersimpan tetapi kategori lama masih berada di file hasil scoring.
""")

st.header("10. Format angka yang digunakan")
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

Data asli di Parquet dan export tetap numerik agar bisa dihitung lagi. Format Indonesia hanya untuk tampilan layar.
""")

st.header("11. Checklist sebelum ranking dipakai")
st.markdown("""
Sebelum ranking dipakai untuk bahan keputusan, cek:

1. Apakah biaya aktif masih banyak yang 0?
2. Apakah sumber biaya sudah sesuai: Excel atau kondisi jalan?
3. Apakah panjang kondisi sudah dinormalisasi terhadap panjang koridor?
4. Apakah KML/KMZ kosong ingin dipenalti, diabaikan, atau memakai panjang koridor?
5. Apakah tematik kosong diperlakukan sebagai masalah?
6. Apakah bobot jenis produksi sudah sesuai kebijakan? Bobot default bukan bobot final.
7. Apakah top 20 masuk akal secara teknis, ekonomi, konektivitas, dan pelayanan publik?
8. Apakah threshold kategori prioritas sudah sesuai distribusi skor dan kebutuhan keputusan?
9. Apakah ada parameter yang double count, misalnya ekonomi lama aktif bersamaan dengan ekonomi komoditas gabungan?
""")
