# آموزش ساخت فایل EXE (یک فایل اجرایی مستقل)

## روش ۱: استفاده از PyInstaller (توصیه شده)

### مرحله ۱: نصب PyInstaller
روی سیستم خودت (ویندوز) در پوشه پروژه اجرا کن:

```bash
pip install pyinstaller
```

### مرحله ۲: فایل запуска (launcher.py)
یک فایل به اسم `launcher.py` توی پوشه پروژه بساز با این محتوا:

```python
"""Launcher for the Insurance Accounting app - creates EXE entry point"""
import os
import sys
import threading
import webbrowser
import time

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'insurance_accounting.settings')

# Add project root to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Run migrations
import django
from django.core.management import call_command

django.setup()
call_command('migrate', '--run-syncdb')

# Create admin user if not exists
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

# Run server in background
from wsgiref.simple_server import make_server
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Open browser after a short delay
def open_browser():
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:8000')

threading.Thread(target=open_browser, daemon=True).start()

print("=" * 50)
print("  نرم‌افزار حسابداری بیمه")
print("  آدرس: http://127.0.0.1:8000")
print("  کاربر: admin")
print("  رمز:   admin123")
print("=" * 50)
print("برای خروج Ctrl+C بزنید")
print()

# Run server
from django.core.management.commands.runserver import Command as RunServer
server = RunServer()
server.run('0.0.0.0:8000')
```

### مرحله ۳: ساخت EXE
در ترمینال داخل پوشه پروژه اجرا کن:

```bash
pyinstaller --onefile --windowed --name "HesabdarBime" ^
  --add-data "policies/templates;policies/templates" ^
  --add-data "policies/static;policies/static" ^
  --add-data "insurance_accounting;insurance_accounting" ^
  --hidden-import django ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  --hidden-import jdatetime ^
  --hidden-import django.contrib.humanize ^
  launcher.py
```

### مرحله ۴: فایل EXE رو می‌گیری
فایل `dist/HesabdarBime.exe` ساخته میشه. 
- این فایل **حدود ۱۵۰-۲۰۰ مگابایت** حجم داره (چون پایتون + کتابخونه‌ها + دجانگو + پاندا رو داره)
- برای اجرا فقط کافیه دوبار کلیک کنی
- اولین بار دیتابیس رو می‌سازه و مرورگر رو باز می‌کنه

---

## روش ۲: استفاده از auto-py-to-exe (راحت‌تر)

```bash
pip install auto-py-to-exe
auto-py-to-exe
```
یک محیط گرافیکی باز میشه که توش راحت تنظیمات رو می‌کنی.

---

## روش ۳: Nuitka (EXE سبک‌تر و سریع‌تر)

```bash
pip install nuitka
nuitka --standalone --onefile --enable-plugin=django-freezer ^
  --include-data-dir=policies/templates=policies/templates ^
  --include-data-dir=policies/static=policies/static ^
  --output-dir=dist launcher.py
```

---

## ⚠️ نکات مهم

1. **حجم فایل:** چون pandas و openpyxl سنگین هستند، EXE حداقل ۱۵۰ مگابایت میشه
2. **اولین اجرا:** کندتر از حالت معمولی اجرا میشه (چون فایل باید از حالت فشرده خارج بشه)
3. **فولدر media:** فایل‌های اکسل آپلود شده توی پوشه `media/` ذخیره میشن
4. **دیتابیس:** فایل `db.sqlite3` توی همون پوشه EXE ساخته میشه
5. **آنتی‌ویروس:** بعضی آنتی‌ویروس‌ها فایل EXE ساخته شده با PyInstaller رو مشکوک تشخیص میدن

---

## راه ساده‌تر: همون run.bat

به جای EXE می‌تونی از فایل `run.bat` استفاده کنی:
- فقط کافیه دوبار کلیک کنی
- اولین بار یه محیط مجازی می‌سازه و پیش‌نیازها رو نصب می‌کنه
- بعد سرور رو اجرا می‌کنه و مرورگر رو باز می‌کنه
- تنها شرطش اینه که پایتون روی سیستم نصب باشه
