from django.urls import path
from . import views

app_name = 'pacientes'

urlpatterns = [
    path('', views.mis_turnos_view, name='mis_turnos'),
    path('buscar/', views.buscar_especialidad_view, name='buscar_especialidad'),
    path('especialidad/<int:especialidad_id>/', views.seleccionar_turno_view, name='seleccionar_turno'),
    path('reservar/', views.reservar_turno_view, name='reservar_turno'),
    path('cancelar/<int:turno_id>/', views.cancelar_turno_view, name='cancelar_turno'),
    path('reprogramar/<int:turno_id>/', views.reprogramar_turno_view, name='reprogramar_turno'),
]
