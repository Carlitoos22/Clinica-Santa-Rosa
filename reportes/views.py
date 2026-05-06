from django.shortcuts import render
from django.utils import timezone
from datetime import datetime, timedelta
from core.permissions import admin_requerido
from .utils import (
    reporte_ocupacion_por_medico,
    reporte_ocupacion_por_especialidad,
    reporte_ausentismo,
    reporte_turnos_por_canal,
)


def _parsear_rango(request):
    """Extrae fecha_desde y fecha_hasta del request, con default último mes."""
    fecha_hasta_str = request.GET.get('fecha_hasta')
    fecha_desde_str = request.GET.get('fecha_desde')

    fecha_hasta = (
        datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
        if fecha_hasta_str else timezone.now().date()
    )
    fecha_desde = (
        datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
        if fecha_desde_str else fecha_hasta - timedelta(days=30)
    )
    return fecha_desde, fecha_hasta


@admin_requerido
def dashboard_view(request):
    """CU-06: Dashboard principal del administrador."""
    fecha_desde, fecha_hasta = _parsear_rango(request)

    return render(request, 'reportes/dashboard.html', {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'ocupacion_medico': reporte_ocupacion_por_medico(fecha_desde, fecha_hasta),
        'ocupacion_especialidad': reporte_ocupacion_por_especialidad(fecha_desde, fecha_hasta),
        'ausentismo': reporte_ausentismo(fecha_desde, fecha_hasta),
        'canales': reporte_turnos_por_canal(fecha_desde, fecha_hasta),
    })


@admin_requerido
def ocupacion_medico_view(request):
    """RF-17: Reporte detallado de ocupación por médico."""
    fecha_desde, fecha_hasta = _parsear_rango(request)
    datos = reporte_ocupacion_por_medico(fecha_desde, fecha_hasta)

    return render(request, 'reportes/ocupacion_medico.html', {
        'datos': datos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@admin_requerido
def ocupacion_especialidad_view(request):
    """RF-18: Reporte detallado de ocupación por especialidad."""
    fecha_desde, fecha_hasta = _parsear_rango(request)
    datos = reporte_ocupacion_por_especialidad(fecha_desde, fecha_hasta)

    return render(request, 'reportes/ocupacion_especialidad.html', {
        'datos': datos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@admin_requerido
def ausentismo_view(request):
    """RF-19: Reporte de tasa de ausentismo."""
    fecha_desde, fecha_hasta = _parsear_rango(request)
    datos = reporte_ausentismo(fecha_desde, fecha_hasta)

    return render(request, 'reportes/ausentismo.html', {
        'datos': datos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })


@admin_requerido
def canales_view(request):
    """RF-20: Turnos por canal."""
    fecha_desde, fecha_hasta = _parsear_rango(request)
    datos = reporte_turnos_por_canal(fecha_desde, fecha_hasta)

    return render(request, 'reportes/canales.html', {
        'datos': datos,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    })
