Write-Host "Cek file wajib..." -ForegroundColor Cyan
$required = @(
  "app.py",
  "requirements.txt",
  "scoring\formatting.py",
  "scoring\scoring_engine.py",
  "pages\10_Dashboard_Pengguna.py",
  "pages\11_Detail_Koridor.py",
  "pages\12_Panduan_Aplikasi.py",
  "pages\13_Penjelasan_Rumus_Aktif.py",
  "pages\90_Upload_Data.py",
  "pages\91_Validasi_Data.py",
  "pages\92_Rumus_Perhitungan.py",
  "pages\93_Scoring.py",
  "pages\94_Query_DuckDB.py"
)
foreach ($f in $required) {
  if (Test-Path $f) { Write-Host "OK  $f" -ForegroundColor Green }
  else { Write-Host "MISS $f" -ForegroundColor Red }
}
Write-Host "\nIsi folder pages:" -ForegroundColor Cyan
Get-ChildItem .\pages\*.py | Select-Object Name
