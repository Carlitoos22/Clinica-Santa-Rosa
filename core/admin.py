from django.contrib import admin
from .models import (
    Especialidad, Medico, Paciente, FamiliarPaciente,
    DisponibilidadMedica, BloqueoHorario, Turno, Notificacion,
)


@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activa')
    list_filter = ('activa',)


class DisponibilidadInline(admin.TabularInline):
    model = DisponibilidadMedica
    extra = 1


class BloqueoInline(admin.TabularInline):
    model = BloqueoHorario
    extra = 0


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'matricula', 'listar_especialidades')
    search_fields = ('usuario__first_name', 'usuario__last_name', 'matricula')
    filter_horizontal = ('especialidades',)
    inlines = [DisponibilidadInline, BloqueoInline]

    @admin.display(description='Especialidades')
    def listar_especialidades(self, obj):
        return ', '.join(e.nombre for e in obj.especialidades.all())


class FamiliarInline(admin.TabularInline):
    model = FamiliarPaciente
    extra = 0


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'estado')
    list_filter = ('estado',)
    search_fields = ('usuario__first_name', 'usuario__last_name', 'usuario__dni')
    inlines = [FamiliarInline]


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'medico', 'especialidad', 'fecha_hora', 'estado', 'canal')
    list_filter = ('estado', 'canal', 'especialidad', 'medico')
    search_fields = (
        'paciente__usuario__first_name',
        'paciente__usuario__last_name',
        'paciente__usuario__dni',
    )
    date_hierarchy = 'fecha_hora'
    readonly_fields = ('creado_en', 'actualizado_en')


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'destinatario', 'turno', 'canal_envio', 'estado_envio', 'creada_en')
    list_filter = ('tipo', 'estado_envio', 'canal_envio')
    readonly_fields = ('creada_en',)
