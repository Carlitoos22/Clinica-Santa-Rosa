from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('pacientes/', include('pacientes.urls')),
    path('recepcion/', include('recepcion.urls')),
    path('medicos/', include('medicos.urls')),
    path('reportes/', include('reportes.urls')),
]
