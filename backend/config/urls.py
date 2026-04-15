from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root(_request):
    return JsonResponse({
        'name': 'Masar Port Flow System',
        'status': 'ok',
        'admin': '/admin/',
        'api': '/api/'
    })

urlpatterns = [
    path('', root),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
