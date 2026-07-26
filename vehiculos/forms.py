from django import forms

from productos.models import Producto

from .models import CompatibilidadProducto, Vehiculo


class VehiculoForm(forms.ModelForm):
    """Formulario para registrar y modificar vehículos."""

    class Meta:
        model = Vehiculo
        fields = [
            "marca",
            "modelo",
            "anio_desde",
            "anio_hasta",
            "motor",
            "estado",
        ]

        widgets = {
            "marca": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: Toyota",
                }
            ),
            "modelo": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: Corolla",
                }
            ),
            "anio_desde": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "1900",
                    "max": "2100",
                }
            ),
            "anio_hasta": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "1900",
                    "max": "2100",
                }
            ),
            "motor": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: 1.8 gasolina",
                }
            ),
            "estado": forms.CheckboxInput(
                attrs={
                    "class": "campo-checkbox",
                }
            ),
        }

    def clean_marca(self):
        marca = self.cleaned_data["marca"]
        return marca.strip()

    def clean_modelo(self):
        modelo = self.cleaned_data["modelo"]
        return modelo.strip()

    def clean_motor(self):
        motor = self.cleaned_data.get("motor", "")
        return motor.strip()


class CompatibilidadProductoForm(forms.ModelForm):
    """Formulario para relacionar productos con vehículos."""

    class Meta:
        model = CompatibilidadProducto
        fields = [
            "producto",
            "vehiculo",
            "observaciones",
        ]

        widgets = {
            "producto": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "vehiculo": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": (
                        "Información adicional sobre la compatibilidad"
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["producto"].queryset = (
            Producto.objects.filter(estado=True)
            .order_by("nombre")
        )

        self.fields["vehiculo"].queryset = (
            Vehiculo.objects.filter(estado=True)
            .order_by(
                "marca",
                "modelo",
                "anio_desde",
            )
        )