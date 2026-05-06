from django.urls import path
from . import views

app_name = 'medicos'

urlpatterns = [
    path('agenda/', views.agenda_view, name='agenda'),
    path('bloquear/', views.bloquear_horario_view, name='bloquear_horario'),
    path('bloqueos/', views.mis_bloqueos_view, name='mis_bloqueos'),
]
