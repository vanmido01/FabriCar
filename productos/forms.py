from django import forms
from django.core.exceptions import ValidationError

from .models import Producto


class ProductoForm(forms.ModelForm):
    """Formulario para registrar y modificar productos."""

    class Meta:
        model = Producto

        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "tipo",
            "condicion",
            "marca",
            "procedencia",
            "precio_compra",
            "precio_venta",
            "stock_actual",
            "stock_minimo",
            "imagen",
            "estado",
        ]

        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: PROD-001",
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Nombre del repuesto",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": "Descripción del producto",
                }
            ),
            "tipo": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "condicion": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "marca": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Marca del repuesto",
                }
            ),
            "procedencia": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "País o lugar de procedencia",
                }
            ),
            "precio_compra": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "precio_venta": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "stock_actual": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "0",
                }
            ),
            "stock_minimo": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "0",
                }
            ),
            "imagen": forms.ClearableFileInput(
                attrs={
                    "class": "campo-formulario",
                    "accept": "image/*",
                }
            ),
            "estado": forms.CheckboxInput(
                attrs={
                    "class": "campo-checkbox",
                }
            ),
        }

    def clean_codigo(self):
        """Guarda el código sin espacios externos y en mayúsculas."""

        codigo = self.cleaned_data["codigo"]
        return codigo.strip().upper()

    def clean(self):
        """Valida que el precio de venta no sea menor al de compra."""

        datos_limpios = super().clean()

        precio_compra = datos_limpios.get("precio_compra")
        precio_venta = datos_limpios.get("precio_venta")

        if (
            precio_compra is not None
            and precio_venta is not None
            and precio_venta < precio_compra
        ):
            raise ValidationError(
                "El precio de venta no puede ser menor "
                "al precio de compra."
            )

        return datos_limpios