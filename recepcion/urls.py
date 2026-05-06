from django.urls import path
from . import views

app_name = 'recepcion'

urlpatterns = [
    path('', views.panel_view, name='panel'),
    path('telefonico/', views.registrar_turno_telefonico_view, name='registrar_telefonico'),
    path('checkin/<int:turno_id>/', views.checkin_view, name='checkin'),
    path('noshow/<int:turno_id>/', views.noshow_view, name='noshow'),
    path('atendido/<int:turno_id>/', views.atendido_view, name='atendido'),
    path('cancelar/<int:turno_id>/', views.cancelar_turno_recepcion_view, name='cancelar_turno'),
    path('buscar/', views.buscar_turnos_view, name='buscar_turnos'),
]
