# حزمة نشر مشروع مسار عبر GitHub Actions إلى خادم Ubuntu

هذه الحزمة تحتوي على الملفات اللازمة للنشر التلقائي من GitHub إلى خادم حقيقي باستخدام SSH وDocker Compose وNginx.

## الملفات
- `.github/workflows/deploy.yml`
- `.env.production.example`
- `docker-compose.prod.yml`
- `deploy/nginx/masar.conf`
- `deploy/server/bootstrap_ubuntu.sh`

## ماذا تحتاج قبل البدء؟
1. خادم Ubuntu بصلاحيات sudo.
2. مستودع GitHub للمشروع.
3. دومين (اختياري لكن موصى به).
4. مفتاح SSH مخصص للنشر.

## أسرار GitHub المطلوبة
- SSH_HOST
- SSH_PORT
- SSH_USER
- SSH_PRIVATE_KEY
- SERVER_APP_DIR
- PROD_ENV_FILE
