from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('authtoken', '0003_tokenproxy'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('action', models.CharField(max_length=120)),
                ('model_name', models.CharField(max_length=120)),
                ('object_id', models.CharField(blank=True, max_length=120, null=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='BookingSlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('date', models.DateField()),
                ('hour', models.PositiveIntegerField(help_text='0-23')),
                ('capacity', models.PositiveIntegerField(default=0)),
                ('booked_count', models.PositiveIntegerField(default=0)),
                ('is_closed', models.BooleanField(default=False)),
                ('active_cranes', models.PositiveIntegerField(default=1)),
                ('avg_load_minutes', models.PositiveIntegerField(default=30)),
                ('active_gate_lanes', models.PositiveIntegerField(default=1)),
                ('lane_rate_per_hour', models.PositiveIntegerField(default=10)),
                ('yard_slots', models.PositiveIntegerField(default=20)),
            ],
            options={'ordering': ('date', 'hour'), 'unique_together': {('date', 'hour')}},
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('company_type', models.CharField(choices=[('broker', 'مخلص'), ('carrier', 'ناقل'), ('port', 'ميناء'), ('customs', 'جمارك'), ('other', 'أخرى')], default='other', max_length=20)),
                ('contact_name', models.CharField(blank=True, max_length=255, null=True)),
                ('contact_phone', models.CharField(blank=True, max_length=30, null=True)),
            ],
            options={'ordering': ('name',)},
        ),
        migrations.CreateModel(
            name='Container',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('container_no', models.CharField(max_length=30, unique=True)),
                ('weight', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('destination', models.CharField(max_length=255)),
                ('customs_status', models.CharField(default='released', max_length=50)),
            ],
            options={'ordering': ('container_no',)},
        ),
        migrations.CreateModel(
            name='Driver',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('full_name', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=30)),
                ('national_id', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={'ordering': ('full_name',), 'unique_together': {('full_name', 'phone')}},
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='ScanPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=120)),
                ('point_type', models.CharField(choices=[('ENTRY_GATE', 'بوابة الدخول'), ('BERTH', 'الرصيف'), ('CUSTOMS_ZONE', 'منطقة الجمارك'), ('EXIT_GATE', 'بوابة الخروج'), ('DELIVERY', 'التسليم')], max_length=30, unique=True)),
                ('location_description', models.CharField(blank=True, max_length=255, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('name',)},
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(choices=[('broker', 'مخلص جمركي'), ('carrier', 'شركة نقل'), ('gate_guard', 'حارس بوابة'), ('port_admin', 'إدارة الميناء'), ('ops', 'عمليات')], default='broker', max_length=20)),
                ('phone', models.CharField(blank=True, max_length=30, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Truck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plate_number', models.CharField(max_length=50, unique=True)),
                ('truck_type', models.CharField(blank=True, max_length=100, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('owner_company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trucks', to='core.company')),
            ],
            options={'ordering': ('plate_number',)},
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('trip_code', models.UUIDField(default=__import__('uuid').uuid4, editable=False, unique=True)),
                ('destination', models.CharField(max_length=255)),
                ('qr_token', models.TextField(blank=True, null=True)),
                ('qr_image', models.ImageField(blank=True, null=True, upload_to='qr_codes/')),
                ('status', models.CharField(choices=[('CREATED', 'Created'), ('BOOKED', 'Booked'), ('APPROVED', 'Approved'), ('ARRIVED_GATE', 'Arrived Gate'), ('ENTERED_PORT', 'Entered Port'), ('AT_BERTH', 'At Berth'), ('LOADING_COMPLETE', 'Loading Complete'), ('PASSED_CUSTOMS', 'Passed Customs'), ('EXITED_PORT', 'Exited Port'), ('IN_TRANSIT', 'In Transit'), ('DELIVERED', 'Delivered'), ('CANCELLED', 'Cancelled')], default='CREATED', max_length=30)),
                ('notes', models.TextField(blank=True, null=True)),
                ('broker', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='broker_trips', to=settings.AUTH_USER_MODEL)),
                ('carrier_company', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='carrier_trips', to='core.company')),
                ('container', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.container')),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.driver')),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='trips', to='core.bookingslot')),
                ('truck', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.truck')),
            ],
            options={'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='ScanEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('scanned_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('note', models.TextField(blank=True, null=True)),
                ('scan_point', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.scanpoint')),
                ('scanned_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scan_events', to='core.trip')),
            ],
            options={'ordering': ('-scanned_at',)},
        ),
    ]
