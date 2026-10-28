from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Acceso al panel de administrador
    path('admin/', admin.site.urls),

    #


    # Acceso a vistas de la API
    path('api/v1/', include('rpf_api.urls')),
]
