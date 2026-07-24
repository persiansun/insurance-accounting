# Deploy on PythonAnywhere — Step by Step

## 🎯 مرحله ۱: لاگین و باز کردن Bash Console
1. برو به: [https://www.pythonanywhere.com/user/persiansun/](https://www.pythonanywhere.com/user/persiansun/)
2. روی **Consoles** تب کلیک کن
3. **Start a new console** → **Bash**
4. توی کنسول این کدها رو کپی کن و enter بزن:

```bash
# Clone project
cd ~
rm -rf insurance-accounting
git clone https://github.com/persiansun/insurance-accounting.git

# Create virtual environment
cd insurance-accounting
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup database
python manage.py migrate
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')"

# Collect static files
python manage.py collectstatic --noinput
```

## 🎯 مرحله ۲: ساخت Web App
1. برو به **Web** تب
2. **Add a new web app** → Next
3. **Manual configuration** → **Python 3.10** → Next

## 🎯 مرحله ۳: تنظیم WSGI
1. توی صفحه Web، روی لینک **Code** → **WSGI configuration file** کلیک کن
2. همه متن رو پاک کن و این رو جایگزین کن:

```python
import os
import sys

path = '/home/persiansun/insurance-accounting'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'insurance_accounting.settings'
os.environ['PYTHON_EGG_CACHE'] = '/home/persiansun/insurance-accounting/.python-eggs'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

3. **Save** کن

## 🎯 مرحله ۴: تنظیم Virtual Environment
1. توی صفحه Web، به بخش **Virtualenv** برو
2. توی کادر بنویس: `/home/persiansun/insurance-accounting/venv`
3. کلیک کن **OK**

## 🎯 مرحله ۵: Static files
1. توی بخش **Static files**:
   - URL: `/static/`
   - Path: `/home/persiansun/insurance-accounting/policies/static`
   - کلیک **Add**

## 🎯 مرحله ۶: Reload
1. برگرد بالای صفحه
2. کلیک کن **Reload persiansun.pythonanywhere.com**
3. صبر کن ۱۰ ثانیه

## ✅ تمام!
آدرس: [https://persiansun.pythonanywhere.com](https://persiansun.pythonanywhere.com)
کاربر: `admin`
رمز: `admin123`
