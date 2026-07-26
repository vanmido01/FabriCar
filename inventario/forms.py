from django import forms

from productos.models import Producto

from .models import MovimientoInventario


class AjusteInventarioForm(forms.Form):
    """Formulario para registrar ajustes manuales de inventario."""

    producto = forms.ModelChoiceField(
        queryset=Producto.objects.none(),
        empty_label="Seleccione un producto",
        label="Producto",
        widget=forms.Select(
            attrs={
                "class": "campo-formulario",
            }
        ),
    )

    tipo_ajuste = forms.ChoiceField(
        choices=[
            (
                MovimientoInventario.TipoMovimiento.AJUSTE_ENTRADA,
                "Ajuste de entrada",
            ),
            (
                MovimientoInventario.TipoMovimiento.AJUSTE_SALIDA,
                "Ajuste de salida",
            ),
        ],
        label="Tipo de ajuste",
        widget=forms.Select(
            attrs={
                "class": "campo-formulario",
            }
        ),
    )

    cantidad = forms.IntegerField(
        min_value=1,
        label="Cantidad",
        widget=forms.NumberInput(
            attrs={
                "class": "campo-formulario",
                "min": "1",
                "placeholder": "Cantidad del ajuste",
            }
        ),
    )

    motivo = forms.CharField(
        max_length=200,
        label="Motivo",
        widget=forms.TextInput(
            attrs={
                "class": "campo-formulario",
                "placeholder": (
                    "Ejemplo: corrección por conteo físico"
                ),
            }
        ),
    )

    observaciones = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "class": "campo-formulario",
                "rows": 4,
                "placeholder": (
                    "Información adicional sobre el ajuste"
                ),
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["producto"].queryset = (
            Producto.objects.filter(estado=True)
            .order_by("nombre")
        )

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"]

        return motivo.strip()

    def clean_observaciones(self):
        observaciones = self.cleaned_data.get(
            "observaciones",
            "",
        )

        return observaciones.strip()

    def clean(self):
        datos_limpios = super().clean()

        producto = datos_limpios.get("producto")
        tipo_ajuste = datos_limpios.get("tipo_ajuste")
        cantidad = datos_limpios.get("cantidad")

        if (
            producto
            and cantidad
            and tipo_ajuste
            == MovimientoInventario.TipoMovimiento.AJUSTE_SALIDA
            and cantidad > producto.stock_actual
        ):
            self.add_error(
                "cantidad",
                (
                    "La cantidad de salida no puede ser mayor "
                    f"al stock actual de {producto.stock_actual}."
                ),
            )

        return datos_limpios