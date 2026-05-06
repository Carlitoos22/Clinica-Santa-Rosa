from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, time
from authentication.models import Usuario
from core.models import (
    Especialidad, Medico, Paciente, DisponibilidadMedica, Turno,
)


class Command(BaseCommand):
    help = 'Carga datos de prueba: especialidades, médicos, pacientes, disponibilidades y turnos.'

    def handle(self, *args, **options):
        self.stdout.write('Creando especialidades...')
        especialidades = {}
        for nombre, desc in [
            ('Clínica Médica', 'Medicina general y atención primaria'),
            ('Pediatría', 'Atención médica para niños y adolescentes'),
            ('Cardiología', 'Diagnóstico y tratamiento de enfermedades del corazón'),
            ('Ginecología', 'Salud del sistema reproductor femenino'),
            ('Traumatología', 'Lesiones del sistema musculoesquelético'),
            ('Dermatología', 'Enfermedades de la piel, cabello y uñas'),
        ]:
            esp, _ = Especialidad.objects.get_or_create(nombre=nombre, defaults={'descripcion': desc})
            especialidades[nombre] = esp

        self.stdout.write('Creando médicos...')
        medicos_data = [
            ('mlopez', 'María', 'López', '20301234', 'MP-1001', ['Clínica Médica']),
            ('jramirez', 'Jorge', 'Ramírez', '20305678', 'MP-1002', ['Clínica Médica']),
            ('afernandez', 'Ana', 'Fernández', '20309012', 'MP-1003', ['Pediatría']),
            ('cmorales', 'Carlos', 'Morales', '20313456', 'MP-1004', ['Pediatría']),
            ('lgarcia', 'Laura', 'García', '20317890', 'MP-1005', ['Cardiología']),
            ('rcastro', 'Ricardo', 'Castro', '20321234', 'MP-1006', ['Cardiología']),
            ('sparedes', 'Silvia', 'Paredes', '20325678', 'MP-1007', ['Ginecología']),
            ('mherrera', 'Martín', 'Herrera', '20329012', 'MP-1008', ['Ginecología']),
            ('dsilva', 'Diego', 'Silva', '20333456', 'MP-1009', ['Traumatología']),
            ('vmedina', 'Valeria', 'Medina', '20337890', 'MP-1010', ['Traumatología']),
            ('pruiz', 'Pablo', 'Ruiz', '20341234', 'MP-1011', ['Dermatología']),
            ('ngomez', 'Natalia', 'Gómez', '20345678', 'MP-1012', ['Dermatología']),
        ]

        medicos = []
        for username, nombre, apellido, dni, matricula, esps in medicos_data:
            usuario, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'dni': dni,
                    'rol': Usuario.Rol.MEDICO,
                    'email': f'{username}@clinicasantarosa.com',
                },
            )
            if created:
                usuario.set_password('medico123')
                usuario.save()

            medico, _ = Medico.objects.get_or_create(
                usuario=usuario,
                defaults={'matricula': matricula},
            )
            for esp_nombre in esps:
                medico.especialidades.add(especialidades[esp_nombre])
            medicos.append(medico)

        self.stdout.write('Creando disponibilidades...')
        for medico in medicos:
            if not medico.disponibilidades.exists():
                for dia in range(5):  # Lunes a viernes
                    DisponibilidadMedica.objects.create(
                        medico=medico,
                        dia_semana=dia,
                        hora_inicio=time(8, 0),
                        hora_fin=time(12, 0),
                        duracion_turno=30,
                    )

        self.stdout.write('Creando pacientes...')
        pacientes = []
        pacientes_data = [
            ('rgonzalez', 'Roberto', 'González', '35678901', '3794100001'),
            ('mdiaz', 'Marta', 'Díaz', '28456789', '3794100002'),
            ('fmartinez', 'Federico', 'Martínez', '40123456', '3794100003'),
            ('lsanchez', 'Lucía', 'Sánchez', '33789012', '3794100004'),
            ('eacosta', 'Eduardo', 'Acosta', '29567890', '3794100005'),
        ]

        for username, nombre, apellido, dni, celular in pacientes_data:
            usuario, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'dni': dni,
                    'celular': celular,
                    'rol': Usuario.Rol.PACIENTE,
                    'email': f'{username}@mail.com',
                },
            )
            if created:
                usuario.set_password('paciente123')
                usuario.save()

            paciente, _ = Paciente.objects.get_or_create(usuario=usuario)
            pacientes.append(paciente)

        self.stdout.write('Creando recepcionista...')
        recep_user, created = Usuario.objects.get_or_create(
            username='recepcion1',
            defaults={
                'first_name': 'Carolina',
                'last_name': 'Méndez',
                'dni': '31000001',
                'rol': Usuario.Rol.RECEPCIONISTA,
                'email': 'recepcion@clinicasantarosa.com',
            },
        )
        if created:
            recep_user.set_password('recepcion123')
            recep_user.save()

        self.stdout.write('Creando administrador...')
        admin_user, created = Usuario.objects.get_or_create(
            username='admin1',
            defaults={
                'first_name': 'Director',
                'last_name': 'Clínica',
                'dni': '22000001',
                'rol': Usuario.Rol.ADMIN,
                'email': 'admin@clinicasantarosa.com',
                'is_staff': True,
            },
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()

        self.stdout.write('Creando turnos de ejemplo...')
        if not Turno.objects.exists():
            ahora = timezone.now()
            hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

            turnos_ejemplo = [
                (pacientes[0], medicos[0], 'Clínica Médica', hoy + timedelta(hours=8, minutes=30), Turno.Canal.ONLINE),
                (pacientes[1], medicos[0], 'Clínica Médica', hoy + timedelta(hours=9, minutes=0), Turno.Canal.TELEFONO),
                (pacientes[2], medicos[2], 'Pediatría', hoy + timedelta(hours=10, minutes=0), Turno.Canal.ONLINE),
                (pacientes[3], medicos[4], 'Cardiología', hoy + timedelta(hours=8, minutes=0), Turno.Canal.PRESENCIAL),
                (pacientes[0], medicos[6], 'Ginecología', hoy + timedelta(days=1, hours=9, minutes=0), Turno.Canal.ONLINE),
                (pacientes[1], medicos[8], 'Traumatología', hoy + timedelta(days=1, hours=10, minutes=30), Turno.Canal.TELEFONO),
                (pacientes[4], medicos[10], 'Dermatología', hoy + timedelta(days=2, hours=11, minutes=0), Turno.Canal.ONLINE),
                (pacientes[2], medicos[1], 'Clínica Médica', hoy + timedelta(days=3, hours=8, minutes=0), Turno.Canal.ONLINE),
            ]

            for paciente, medico, esp_nombre, fecha_hora, canal in turnos_ejemplo:
                Turno.objects.create(
                    paciente=paciente,
                    medico=medico,
                    especialidad=especialidades[esp_nombre],
                    fecha_hora=fecha_hora,
                    canal=canal,
                )

        self.stdout.write(self.style.SUCCESS(
            '\nDatos de prueba cargados:\n'
            '  - 6 especialidades\n'
            '  - 12 médicos (user: mlopez..ngomez / pass: medico123)\n'
            '  - 5 pacientes (user: rgonzalez..eacosta / pass: paciente123)\n'
            '  - 1 recepcionista (user: recepcion1 / pass: recepcion123)\n'
            '  - 1 administrador (user: admin1 / pass: admin123)\n'
            '  - 8 turnos de ejemplo'
        ))
