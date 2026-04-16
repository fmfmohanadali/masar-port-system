# نظام مسار - النسخة التشغيلية الكاملة

هذه نسخة تشغيلية متكاملة من مشروع **مسار** لإدارة وتتبع حركة القواطر والشاحنات داخل الميناء باستخدام **Python / Django + REST API + HTML/PWA للجوال**.

## المزايا الجاهزة في هذه النسخة
- تسجيل دخول فعلي عبر API Token.
- إدارة الأدوار: مخلص، ناقل، حارس بوابة، إدارة، عمليات.
- إنشاء رحلة سريع من واجهة الجوال أو من الـ API.
- حجز موعد وإنشاء/تحديث نافذة زمنية تلقائياً.
- توليد **QR Token** و**QR Image** فعليين لكل رحلة.
- تتبع المرور بين نقاط العبور وتحديث الحالة تلقائياً.
- لوحة تحكم وملخص حي للرحلات.
- إشعارات داخلية للمستخدمين.
- HTML/PWA للجوال مع:
  - شاشة دخول
  - إنشاء رحلة
  - عرض الرحلات
  - مزامنة Offline Queue
  - مسح QR بالكاميرا (إذا كان المتصفح يدعم BarcodeDetector)
- Docker Compose جاهز للإقلاع السريع.
- Seeder لبيانات تجريبية.

## هيكل المشروع
- `backend/` مشروع Django
- `frontend/mobile/` تطبيق الجوال HTML/PWA
- `docs/` التوثيق
- `docker-compose.yml` تشغيل سريع
- `.env.example` إعدادات البيئة

## التشغيل السريع محليًا
```bash
python -m venv .venv
source .venv/bin/activate   # أو .venv\Scriptsctivate على ويندوز
pip install -r requirements.txt
cp .env.example .env
cd backend
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

ثم:
- افتح الـ API: `http://127.0.0.1:8000/api/`
- افتح واجهة الجوال من الملف: `frontend/mobile/mobile_masar.html`
  - أو شغّلها من أي static server

## التشغيل عبر Docker
```bash
docker compose up --build
```
ثم افتح:
- `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## حسابات التجربة بعد seed_demo_data
- المستخدم: `admin`
- كلمة المرور: `Admin@12345`

- المستخدم: `broker1`
- كلمة المرور: `Admin@12345`

> **مهم جدًا:** غيّر كلمات المرور والمفاتيح السرية قبل الإطلاق الفعلي.

## أوامر مفيدة
```bash
python manage.py createsuperuser
python manage.py seed_demo_data
python manage.py collectstatic --noinput
```

## الربط مع واجهة الجوال
في شاشة الإعدادات داخل HTML ضع:
- API Base: `http://127.0.0.1:8000/api`
ثم سجّل الدخول باسم المستخدم وكلمة المرور.

## ملاحظات تشغيلية
- في التطوير المحلي يتم استخدام SQLite افتراضيًا.
- في Docker يتم استخدام PostgreSQL.
- رفع الملفات (مثل صور QR) يتم في `backend/media/`.
- الواجهة تدعم العمل بدون إنترنت جزئيًا عبر طابور مزامنة محلي.
