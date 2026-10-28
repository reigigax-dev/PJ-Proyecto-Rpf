from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Acceso al panel de administrador
    path('admin/', admin.site.urls),

    # Acceso a vistas de la API
    path('api/v1/', include('rpf_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
