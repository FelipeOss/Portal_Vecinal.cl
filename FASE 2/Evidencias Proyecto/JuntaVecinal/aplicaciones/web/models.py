import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver


def folio_solicitud():
    return f"SOL-{uuid.uuid4().hex[:8].upper()}"


def folio_documento():
    return f"DOC-{uuid.uuid4().hex[:8].upper()}"


class Comuna(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    direccion_municipalidad = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.nombre


class JuntaVecinal(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=200)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT, related_name="juntas")
    rut = models.CharField(max_length=12, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nombre


class Hogar(models.Model):
    direccion = models.CharField(max_length=200)
    junta_vecinal = models.ForeignKey(
        JuntaVecinal, on_delete=models.PROTECT, related_name="hogares"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["junta_vecinal", "direccion"],
                name="hogar_unico_por_junta",
            )
        ]

    def __str__(self):
        return self.direccion


class TipoUsuario(models.Model):
    nombre = models.CharField(max_length=30, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class TipoDocumento(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class TipoSolicitud(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    REQUIRED_FIELDS = ["email", "rut"]

    rut = models.CharField(max_length=12, unique=True)
    email = models.EmailField(unique=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_afiliacion = models.DateField(null=True, blank=True)
    tipo_usuario = models.ForeignKey(
        TipoUsuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
    )
    hogar = models.ForeignKey(
        Hogar,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="residentes",
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.rut})"

    @property
    def nombre(self):
        return self.get_full_name() or self.username

    @property
    def correo(self):
        return self.email

    @property
    def rol(self):
        if self.tipo_usuario_id:
            return self.tipo_usuario.nombre.lower()
        return "administrador" if self.is_staff else "vecino"


class Solicitud(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobada", "Aprobada"),
        ("listo", "Documento listo"),
        ("rechazada", "Rechazada"),
        ("anulada", "Anulada"),
    ]

    folio = models.CharField(
        max_length=20, unique=True, default=folio_solicitud, editable=False
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    tipo_solicitud = models.ForeignKey(
        TipoSolicitud, on_delete=models.PROTECT, related_name="solicitudes"
    )
    solicitante = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="solicitudes"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    observacion = models.TextField(blank=True)
    comentario_revision = models.TextField(blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_revisadas",
    )

    def __str__(self):
        return self.folio


class Documento(models.Model):
    folio = models.CharField(
        max_length=20, unique=True, default=folio_documento, editable=False
    )
    solicitud = models.ForeignKey(
        Solicitud, on_delete=models.CASCADE, related_name="documentos"
    )
    tipo_documento = models.ForeignKey(
        TipoDocumento, on_delete=models.PROTECT, related_name="documentos"
    )
    archivo = models.FileField(upload_to="documentos/%Y/%m/")
    fecha_emision = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.folio


@receiver(post_delete, sender=Documento)
def eliminar_archivo_documento(sender, instance, **kwargs):
    if instance.archivo:
        instance.archivo.delete(save=False)


class Notificacion(models.Model):
    destinatario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="notificaciones"
    )
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="notificaciones",
        null=True,
        blank=True,
    )
    texto = models.CharField(max_length=200)
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return self.texto

    @property
    def enlace(self):
        return "Ver solicitud"
