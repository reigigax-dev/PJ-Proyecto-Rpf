from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView,
)
from . import views

'''
    # Endpoints de API para el inicio de sesion mediante JWT
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
'''

urlpatterns = [   
    # Endpoints de la libreria Silk
    path('silk/', include('silk.urls')),

    # Acceso a la documentacion de los endpoints de la API
    path('schema/', SpectacularSwaggerView.as_view(), name='schema-swagger'),
    path('schema/download/', SpectacularAPIView.as_view(), name='schema'),

    # Endpoints de la tabla EVENT SIGN UP
    path('signup/list/', views.EventSignUpListAPIView.as_view(), name='list-signup'),                       # Listar
    path('signup/add/', views.EventSignUpCreateAPIView.as_view(), name='create-list'),                      # Crear
    path('signup/edit/<int:signup_id>/', views.EventSignUpUpdateAPIView.as_view(), name='edit-signup'),     # Modificar
    path('signup/delete/<int:signup_id>/', views.EventSignUpDeleteAPIView.as_view(), name='delete-signup'), # Eliminar
<<<<<<< HEAD
    path('signup/scan/', views.EventSignUpScanAPIView.as_view(), name='scan-signup'),
    path('signup/export/', views.EventSignUpExportAPIView.as_view(), name='export-signups'),
=======
    path('signup/scan/', views.EventSignUpScanAPIView.as_view(), name='scan-signup')
>>>>>>> parent of 432e04e (Se finaliza* la funcion de escaneo de carnet de identidad (se presentan inconvenientes para detectar la ubicacion de nacimiento y el sexo es detectado por el contrario al del carnet))
]