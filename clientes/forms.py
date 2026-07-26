from django import forms

from .models import Cliente


class ClienteForm(forms.ModelForm):
    """Formulario para registrar y modificar clientes."""

    class Meta:
        model = Cliente

        fields = [
            "tipo_cliente",
            "nombre",
            "documento",
            "telefono",
            "correo",
            "direccion",
            "estado",
        ]

        widgets = {
            "tipo_cliente": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Nombre completo o razón social",
                }
            ),
            "documento": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Cédula de identidad o NIT",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: 70707071",
                }
            ),
            "correo": forms.EmailInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "cliente@correo.com",
                }
            ),
            "direccion": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": "Dirección del cliente",
                }
            ),
            "estado": forms.CheckboxInput(
                attrs={
                    "class": "campo-checkbox",
                }
            ),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"]
        return nombre.strip()

    def clean_documento(self):
        documento = self.cleaned_data["documento"]
        return documento.strip().upper()

    def clean_telefono(self):
        telefono = self.cleaned_data.get(
            "telefono",
            "",
        )

        return telefono.strip()

    def clean_correo(self):
        correo = self.cleaned_data.get(
            "correo",
            "",
        )

        return correo.strip().lower()