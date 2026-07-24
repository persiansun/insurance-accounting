<#
.NOTES
    نرم‌افزار حسابداری بیمه - راه‌انداز PowerShell
    یکبار کلیک راست کنید و Run with PowerShell
#>

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   نرم‌افزار حسابداری بیمه - راه‌انداز" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyVersion = python --version
    Write-Host "✅ پایتون: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ پایتون نصب نیست!" -ForegroundColor Red
    Write-Host "   https://www.python.org/downloads/"
    Read-Host "اینتر بزنید..."
    exit 1
}

# Create venv if needed
if (-not (Test-Path "venv\")) {
    Write-Host "[1/4] ایجاد محیط مجازی..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate
. .\venv\Scripts\Activate.ps1

# Install requirements
Write-Host "[2/4] نصب پیش‌نیازها..." -ForegroundColor Yellow
pip install -r requirements.txt -q

# Migrate
Write-Host "[3/4] راه‌اندازی دیتابیس..." -ForegroundColor Yellow
python manage.py migrate

# Create admin
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" 2>$null

# Done
Write-Host "[4/4] آماده!" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "   نرم‌افزار آماده استفاده است!" -ForegroundColor Green
Write-Host "   آدرس: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "   کاربر: admin" -ForegroundColor White
Write-Host "   رمز:   admin123" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Open browser
Start-Process "http://127.0.0.1:8000"

# Run server
python manage.py runserver 0.0.0.0:8000

Read-Host "اینتر بزنید..."
