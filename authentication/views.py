from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistroForm, LoginForm
from core.models import Paciente


def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            Paciente.objects.create(usuario=usuario)
            login(request, usuario)
            messages.success(request, 'Cuenta creada exitosamente.')
            return redirect('dashboard')
    else:
        form = RegistroForm()
    return render(request, 'authentication/registro.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = LoginForm()
    return render(request, 'authentication/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada.')
    return redirect('login')


@login_required
def dashboard_view(request):
    rol = request.user.rol
    if rol == 'paciente':
        # Crear perfil de paciente si no existe (por si se registró antes del fix)
        Paciente.objects.get_or_create(usuario=request.user)
        return redirect('pacientes:mis_turnos')
    elif rol == 'recepcionista':
        return redirect('recepcion:panel')
    elif rol == 'medico':
        return redirect('medicos:agenda')
    elif rol == 'admin':
        return redirect('reportes:dashboard')
    return render(request, 'authentication/dashboard.html')
