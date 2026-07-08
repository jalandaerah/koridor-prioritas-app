Write-Host "Membuat virtual environment..." -ForegroundColor Cyan
python -m venv .venv
Write-Host "Mengaktifkan virtual environment..." -ForegroundColor Cyan
.\.venv\Scripts\Activate.ps1
Write-Host "Install requirements..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "Selesai. Jalankan: .\01_RUN.ps1" -ForegroundColor Green
