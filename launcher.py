"""
Launcher for Insurance Accounting App.
Use this with PyInstaller to create a standalone EXE.
Double-click to run without any command line.
"""
import os
import sys
import threading
import webbrowser
import time
import atexit

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'insurance_accounting.settings')

# Ensure we're in the right directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)


def setup_database():
    """Run migrations and create admin user"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'insurance_accounting.settings')

    import django
    from django.conf import settings
    from django.core.management import call_command

    # Configure Django
    if not settings.configured:
        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
                }
            },
            INSTALLED_APPS=[
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'django.contrib.humanize',
                'policies',
            ],
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [],
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        'django.template.context_processors.request',
                        'django.contrib.auth.context_processors.auth',
                        'django.contrib.messages.context_processors.messages',
                    ],
                },
            }],
            LANGUAGE_CODE='en-us',
            TIME_ZONE='Asia/Tehran',
            USE_I18N=True,
            USE_TZ=True,
            STATIC_URL='/static/',
            ROOT_URLCONF='insurance_accounting.urls',
            SECRET_KEY='exe-secret-key-change-in-production',
            ALLOWED_HOSTS=['*'],
        )

    django.setup()
    call_command('migrate', '--run-syncdb', verbosity=0)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')


def open_browser_delayed():
    """Open browser after server starts"""
    time.sleep(2.5)
    try:
        webbrowser.open('http://127.0.0.1:8000')
    except Exception:
        pass


def print_banner():
    """Print startup banner"""
    print()
    print("=" * 55)
    print("    📋 نرم‌افزار حسابداری بیمه")
    print("    " + "=" * 35)
    print("    🌐 http://127.0.0.1:8000")
    print("    👤 کاربر: admin    🔑 رمز: admin123")
    print("=" * 55)
    print()
    print("    پنجره مرورگر به صورت خودکار باز می‌شود.")
    print("    برای خروج این پنجره را ببندید یا Ctrl+C بزنید.")
    print()


def cleanup():
    print()
    print("سرور متوقف شد.")


if __name__ == '__main__':
    atexit.register(cleanup)

    # Setup database
    print("در حال راه‌اندازی دیتابیس...")
    try:
        setup_database()
        print("✅ دیتابیس آماده است.")
    except Exception as e:
        print(f"⚠️ خطا در راه‌اندازی دیتابیس: {e}")
        print("برنامه همچنان اجرا می‌شود.")

    # Open browser
    threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Print banner
    print_banner()

    # Run server using wsgiref (built-in, no extra deps)
    from wsgiref.simple_server import make_server
    from django.core.wsgi import get_wsgi_application

    try:
        application = get_wsgi_application()
        httpd = make_server('0.0.0.0', 8000, application)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nخداحافظ!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ خطا در اجرای سرور: {e}")
        print("می‌توانید از run.bat استفاده کنید.")
        input("اینتر بزنید...")
