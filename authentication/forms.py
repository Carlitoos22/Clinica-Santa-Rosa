import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario


class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'dni', 'celular',
                'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['dni'].required = True
        self.fields['dni'].widget.attrs['inputmode'] = 'numeric'
        self.fields['celular'].widget.attrs['inputmode'] = 'tel'

    def clean_dni(self):
        dni = self.cleaned_data['dni']
        if not re.match(r'^\d{7,8}$', dni):
            raise forms.ValidationError('El DNI debe contener solo numeros (7 u 8 digitos).')
        return dni

    def clean_celular(self):
        celular = self.cleaned_data.get('celular', '')
        if celular and not re.match(r'^\+?\d{7,15}$', celular):
            raise forms.ValidationError('El celular debe contener solo numeros (7 a 15 digitos). Puede empezar con +.')
        return celular


class LoginForm(AuthenticationForm):
    pass
