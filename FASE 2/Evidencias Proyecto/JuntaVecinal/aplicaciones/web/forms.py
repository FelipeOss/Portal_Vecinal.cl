from django import forms
from django.core.exceptions import ValidationError

from .models import TipoDocumento
from .services import TIPO_MANUAL

TIPOS_HABILITADOS = [
    "Certificado de residencia",
    "Certificado de afiliación",
    "Certificado de antigüedad",
    TIPO_MANUAL,
]


class SolicitudDocumentoForm(forms.Form):
    tipo = forms.ModelChoiceField(queryset=TipoDocumento.objects.none())
    motivo = forms.CharField(max_length=120, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].queryset = TipoDocumento.objects.filter(
            activo=True, nombre__in=TIPOS_HABILITADOS
        )

    def clean_motivo(self):
        motivo = self.cleaned_data["motivo"].strip()
        if not motivo:
            raise ValidationError("Cuéntanos para qué necesitas el certificado.")
        return motivo
