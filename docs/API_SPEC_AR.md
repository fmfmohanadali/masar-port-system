# توثيق API - النسخة التشغيلية

الجذر:
```text
/api/
```

## المصادقة
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- يستخدم التوكن في الهيدر:
```text
Authorization: Token <token>
```

## المسارات
### المستخدم الحالي
- `GET /api/me/`

### لوحة التحكم
- `GET /api/dashboard/summary/`
- `GET /api/reports/turnaround/`

### الرحلات
- `GET /api/trips/`
- `GET /api/trips/{id}/`
- `POST /api/trips/quick-create/`
- `POST /api/trips/{id}/generate-qr/`
- `POST /api/trips/{id}/mark-delivered/`

### نقاط العبور والمسح
- `GET /api/scan-points/`
- `POST /api/scan-events/scan/`

### الحجز
- `GET /api/booking-slots/`
- `GET /api/booking-slots/available/?date=2026-04-15`

### الإشعارات
- `GET /api/notifications/`
- `POST /api/notifications/{id}/mark_read/`

## مثال تسجيل الدخول
```json
{
  "username": "broker1",
  "password": "Admin@12345"
}
```

## مثال إنشاء رحلة سريع
```json
{
  "container_no": "MSKU1234567",
  "truck_plate": "ADN-1001",
  "driver_name": "أحمد علي",
  "driver_phone": "777000111",
  "destination": "صنعاء",
  "carrier_company_name": "شركة الأمان للنقل",
  "slot_datetime": "2026-04-15T10:00:00",
  "notes": "نقل اعتيادي"
}
```

## مثال مسح QR
```json
{
  "token": "signed-token-here",
  "point_type": "ENTRY_GATE",
  "note": "تم المسح من بوابة 1"
}
```
