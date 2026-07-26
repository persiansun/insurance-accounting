# آموزش ساخت کاربران با دسترسی محدود

## روش ۱: ساخت گروه اپراتور (توصیه شده)

1. برو به: [https://persiansun.pythonanywhere.com/admin/auth/group/add/](https://persiansun.pythonanywhere.com/admin/auth/group/add/)
2. **Name:** `اپراتور`
3. **Permissions:** هیچ گزینه‌ای رو انتخاب نکن (خالی بذار)
4. **Save**

## روش ۲: ساخت کاربر جدید

1. برو به: [https://persiansun.pythonanywhere.com/admin/auth/user/add/](https://persiansun.pythonanywhere.com/admin/auth/user/add/)
2. **Username:** مثلاً `operator1`
3. **Password:** یه رمز بده
4. **Save**
5. توی صفحه بعد:
   - ✅ تیک **Active** رو بزن
   - ❌ تیک **Staff status** رو بردار (این باعث میشه به پنل ادمین دسترسی نداشته باشه)
   - ❌ تیک **Superuser status** رو بردار
   - توی بخش **Groups** گروه `اپراتور` رو انتخاب کن
6. **Save**

## تست:
- با کاربر جدید وارد شو: [https://persiansun.pythonanywhere.com/accounts/login/](https://persiansun.pythonanywhere.com/accounts/login/)
- می‌تونه از برنامه اصلی استفاده کنه (داشبورد، بیمه نامه‌ها، اقساط، ...)
- اگه بره به `/admin/` لاگین میمونه ولی خطای **access denied** می‌بینه
