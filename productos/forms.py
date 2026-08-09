from django import forms

from proveedores.models import Proveedor
from vehiculos.models import Vehiculo

from .models import Producto


class ProductoForm(forms.ModelForm):
    """Formulario para registrar y modificar la ficha del producto."""

    vehiculos_compatibles = forms.ModelMultipleChoiceField(
        queryset=Vehiculo.objects.none(),
        required=False,
        label="Vehículos compatibles",
        widget=forms.CheckboxSelectMultiple(
            attrs={
                "class": "lista-opciones-multiples",
            }
        ),
    )

    class Meta:
        model = Producto

        fields = [
            "codigo",
            "nombre",
            "tipo",
            "condicion",
            "marca",
            "procedencia",
            "descripcion",
            "proveedores_habituales",
            "vehiculos_compatibles",
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
            "descripcion": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": (
                        "Características técnicas del producto"
                    ),
                }
            ),
            "proveedores_habituales": forms.CheckboxSelectMultiple(
                attrs={
                    "class": "lista-opciones-multiples",
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

    def __init__(self, *args, **kwargs):
        """Carga proveedores y vehículos activos."""

        super().__init__(*args, **kwargs)

        self.fields["proveedores_habituales"].queryset = (
            Proveedor.objects
            .filter(estado=True)
            .order_by("razon_social")
        )

        self.fields["proveedores_habituales"].required = False

        self.fields["vehiculos_compatibles"].queryset = (
            Vehiculo.objects
            .filter(estado=True)
            .order_by(
                "marca",
                "modelo",
                "anio_desde",
            )
        )

        if self.instance and self.instance.pk:
            self.fields["vehiculos_compatibles"].initial = (
                self.instance.compatibilidades.values_list(
                    "vehiculo_id",
                    flat=True,
                )
            )

    def clean_codigo(self):
        """Normaliza el código y evita fichas duplicadas."""

        codigo = self.cleaned_data["codigo"].strip().upper()

        productos_existentes = Producto.objects.filter(
            codigo=codigo,
        )

        if self.instance and self.instance.pk:
            productos_existentes = productos_existentes.exclude(
                pk=self.instance.pk,
            )

        if productos_existentes.exists():
            raise forms.ValidationError(
                (
                    "Ya existe una ficha de producto con este código. "
                    "Para aumentar sus existencias deberá registrar "
                    "una nueva compra de ese producto."
                )
            )

        return codigo