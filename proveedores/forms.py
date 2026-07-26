from django import forms

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    """Formulario para registrar y modificar proveedores."""

    class Meta:
        model = Proveedor

        fields = [
            "razon_social",
            "nit",
            "persona_contacto",
            "telefono",
            "correo",
            "direccion",
            "estado",
        ]

        widgets = {
            "razon_social": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Nombre o razón social",
                }
            ),
            "nit": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Número de Identificación Tributaria",
                }
            ),
            "persona_contacto": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Nombre de la persona de contacto",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: 70707070",
                }
            ),
            "correo": forms.EmailInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "correo@proveedor.com",
                }
            ),
            "direccion": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": "Dirección del proveedor",
                }
            ),
            "estado": forms.CheckboxInput(
                attrs={
                    "class": "campo-checkbox",
                }
            ),
        }

    def clean_razon_social(self):
        razon_social = self.cleaned_data["razon_social"]

        return razon_social.strip()

    def clean_nit(self):
        nit = self.cleaned_data["nit"]

        return nit.strip().upper()

    def clean_persona_contacto(self):
        persona_contacto = self.cleaned_data.get(
            "persona_contacto",
            "",
        )

        return persona_contacto.strip()

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