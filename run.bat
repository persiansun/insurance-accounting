@echo off
title نرم‌افزار حسابداری بیمه
chcp 65001 >nul

echo ============================================
echo    نرم‌افزار حسابداری بیمه - راه‌انداز
echo ============================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] پایتون روی سیستم نصب نیست!
    echo لطفاً از پایتون 3.10 یا بالاتر نصب کنید:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: Use a local venv if exists, otherwise create one
if not exist "venv\" (
    echo [1/4] ایجاد محیط مجازی...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] خطا در ایجاد محیط مجازی
        pause
        exit /b 1
    )
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install requirements
echo [2/4] نصب پیش‌نیازها...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] خطا در نصب پیش‌نیازها
    pause
    exit /b 1
)

:: Run migrations
echo [3/4] راه‌اندازی دیتابیس...
python manage.py migrate
if %errorlevel% neq 0 (
    echo [ERROR] خطا در راه‌اندازی دیتابیس
    pause
    exit /b 1
)

:: Ensure admin user exists
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" >nul

:: Start server
echo [4/4] در حال راه‌اندازی سرور...
echo.
echo ============================================
echo    نرم‌افزار آماده استفاده است!
echo.
echo    آدرس: http://127.0.0.1:8000
echo    کاربر: admin
echo    رمز:   admin123
echo.
echo    برای خروج پنجره را ببندید.
echo ============================================
echo.

:: Open browser
start http://127.0.0.1:8000

:: Run server
python manage.py runserver 0.0.0.0:8000

pause
