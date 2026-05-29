// ✅ خريطة الحالات - عربي مع ألوان
const STATUS_MAP = {
  CREATED:         { ar: 'تم الإنشاء',       color: '#94a3b8', bg: '#f1f5f9' },
  BOOKED:          { ar: 'محجوزة',           color: '#3b82f6', bg: '#eff6ff' },
  APPROVED:        { ar: 'معتمدة',           color: '#06b6d4', bg: '#ecfeff' },
  ARRIVED_GATE:    { ar: 'وصلت البوابة',     color: '#f59e0b', bg: '#fffbeb' },
  ENTERED_PORT:    { ar: 'داخل الميناء',     color: '#f97316', bg: '#fff7ed' },
  AT_BERTH:        { ar: 'في الرصيف',       color: '#8b5cf6', bg: '#f5f3ff' },
  LOADING_COMPLETE:{ ar: 'اكتمل التحميل',    color: '#6366f1', bg: '#eef2ff' },
  PASSED_CUSTOMS:  { ar: 'اجتازت الجمارك',   color: '#14b8a6', bg: '#f0fdfa' },
  EXITED_PORT:     { ar: 'خرجت من الميناء',  color: '#84cc16', bg: '#f7fee7' },
  IN_TRANSIT:      { ar: 'في الطريق',       color: '#eab308', bg: '#fefce8' },
  DELIVERED:       { ar: 'تم التسليم',       color: '#10b981', bg: '#ecfdf5' },
  CANCELLED:       { ar: 'ملغاة',           color: '#ef4444', bg: '#fef2f2' },
};

function getStatusLabel(status) {
  return STATUS_MAP[status]?.ar || status || '-';
}

function getStatusBadgeHTML(status) {
  const info = STATUS_MAP[status] || { ar: status, color: '#6b7280', bg: '#f3f4f6' };
  return `<span style="
    background: ${info.bg};
    color: ${info.color};
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  ">${info.ar}</span>`;
}
