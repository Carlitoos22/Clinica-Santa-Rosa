from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('ocupacion-medico/', views.ocupacion_medico_view, name='ocupacion_medico'),
    path('ocupacion-especialidad/', views.ocupacion_especialidad_view, name='ocupacion_especialidad'),
    path('ausentismo/', views.ausentismo_view, name='ausentismo'),
    path('canales/', views.canales_view, name='canales'),
]
