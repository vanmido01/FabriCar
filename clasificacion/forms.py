from django import forms

from .models import ParametroClasificacion


class ParametroClasificacionForm(forms.ModelForm):

    class Meta:
        model = ParametroClasificacion

        fields = (
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "umbral_fast",
            "umbral_slow",
        )

        widgets = {
            "fecha_inicio": forms.DateInput(
                attrs={"type": "date"}
            ),
            "fecha_fin": forms.DateInput(
                attrs={"type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for campo in self.fields.values():
            campo.widget.attrs.update({
                "class": "campo-formulario",
            })

    def clean(self):

        cleaned_data = super().clean()

        inicio = cleaned_data.get("fecha_inicio")
        fin = cleaned_data.get("fecha_fin")

        fast = cleaned_data.get("umbral_fast")
        slow = cleaned_data.get("umbral_slow")

        if inicio and fin and inicio > fin:
            raise forms.ValidationError(
                "La fecha inicial no puede ser mayor que la fecha final."
            )

        if (
            fast is not None
            and slow is not None
            and fast <= slow
        ):
            raise forms.ValidationError(
                "El umbral Fast debe ser mayor que el umbral Slow."
            )

        return cleaned_data