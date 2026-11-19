import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from .models import Documento, Notificacion, Solicitud, TipoDocumento, TipoSolicitud, Usuario
from .pdf import generar_certificado

logger = logging.getLogger(__name__)

TIPO_MANUAL = "Certificado de buena conducta o referencia vecinal"


def es_solicitud_manual(tipo_documento):
    return tipo_documento.nombre.strip().lower() == TIPO_MANUAL.lower()


def nombre_certificado(solicitud):
    nombre = solicitud.tipo_solicitud.nombre
    prefijo = "Certificado de "
    if nombre.lower().startswith(prefijo.lower()):
        nombre = nombre[len(prefijo) :]
    return f"Certificado {nombre.capitalize()} {solicitud.folio}.pdf"


def _tipo_solicitud_para(tipo_documento):
    tipo_solicitud = TipoSolicitud.objects.filter(
        nombre__iexact=tipo_documento.nombre
    ).first()
    if tipo_solicitud is None:
        raise ValidationError(
            f"No existe un tipo de solicitud asociado a '{tipo_documento.nombre}'."
        )
    return tipo_solicitud


def _crear_documento(solicitud, tipo_documento):
    contenido = generar_certificado(solicitud, tipo_documento)
    documento = Documento(
        solicitud=solicitud,
        tipo_documento=tipo_documento,
        fecha_emision=timezone.now(),
    )
    documento.archivo.save(
        f"certificado_{solicitud.folio}.pdf",
        ContentFile(contenido),
        save=False,
    )
    documento.save()
    return documento


@transaction.atomic
def crear_solicitud_documento(usuario, tipo_documento, motivo):
    if not usuario.hogar_id:
        raise ValidationError(
            "Tu usuario no tiene un hogar asignado. Contacta a la directiva."
        )

    tipo_solicitud = _tipo_solicitud_para(tipo_documento)
    solicitud = Solicitud.objects.create(
        tipo_solicitud=tipo_solicitud,
        solicitante=usuario,
        estado="listo",
        observacion=motivo,
        fecha_respuesta=timezone.now(),
    )
    documento = _crear_documento(solicitud, tipo_documento)
    return solicitud, documento


def crear_solicitud_revision(usuario, tipo_documento, motivo):
    if not usuario.hogar_id:
        raise ValidationError(
            "Tu usuario no tiene un hogar asignado. Contacta a la directiva."
        )

    tipo_solicitud = _tipo_solicitud_para(tipo_documento)
    solicitud = Solicitud.objects.create(
        tipo_solicitud=tipo_solicitud,
        solicitante=usuario,
        estado="pendiente",
        observacion=motivo,
    )
    notificar_solicitud_enviada(solicitud)
    return solicitud


def presidentes_de(junta):
    return list(
        Usuario.objects.filter(
            hogar__junta_vecinal=junta,
            tipo_usuario__nombre__iexact="Presidente",
            is_active=True,
        )
    )


def _enviar_correo(asunto, cuerpo, destinatarios, adjunto=None):
    destinatarios = [correo for correo in destinatarios if correo]
    if not destinatarios:
        return
    mensaje = EmailMessage(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, destinatarios)
    if adjunto:
        mensaje.attach(*adjunto)
    try:
        mensaje.send(fail_silently=False)
    except Exception:
        logger.exception("No se pudo enviar el correo %s a %s", asunto, destinatarios)


def _texto_corto(texto, limite=200):
    return texto if len(texto) <= limite else f"{texto[: limite - 3]}..."


def notificar_solicitud_enviada(solicitud):
    vecino = solicitud.solicitante
    junta = vecino.hogar.junta_vecinal
    nombre = vecino.get_full_name() or vecino.username
    presidentes = presidentes_de(junta)

    Notificacion.objects.create(
        destinatario=vecino,
        solicitud=solicitud,
        texto=_texto_corto(
            f"Tu solicitud {solicitud.folio} fue enviada y está en revisión."
        ),
    )
    for presidente in presidentes:
        Notificacion.objects.create(
            destinatario=presidente,
            solicitud=solicitud,
            texto=_texto_corto(
                f"Solicitud {solicitud.folio} de {nombre} pendiente de revisión."
            ),
        )

    _enviar_correo(
        f"Solicitud {solicitud.folio} recibida",
        (
            f"Hola {nombre}:\n\n"
            f"Recibimos tu solicitud {solicitud.folio} de "
            f"'{solicitud.tipo_solicitud.nombre}'.\n"
            "Queda en revisión por la directiva de tu junta. Te avisaremos "
            "cuando exista una decisión.\n\n"
            "Este correo fue generado automáticamente, por favor no responder."
        ),
        [vecino.email],
    )
    _enviar_correo(
        f"Solicitud pendiente {solicitud.folio}",
        (
            f"Hola:\n\n"
            f"El/la vecino/a {nombre}, RUT {vecino.rut}, de la junta "
            f"{junta.nombre}, envió la solicitud {solicitud.folio} de "
            f"'{solicitud.tipo_solicitud.nombre}', que requiere tu revisión.\n\n"
            "Ingresa al portal para aprobarla o rechazarla.\n\n"
            "Este correo fue generado automáticamente, por favor no responder."
        ),
        [presidente.email for presidente in presidentes],
    )


@transaction.atomic
def resolver_solicitud(solicitud, presidente, aprobar, comentario=""):
    solicitud = Solicitud.objects.select_for_update().get(pk=solicitud.pk)
    if solicitud.estado != "pendiente":
        raise ValidationError("Esta solicitud ya fue revisada.")

    tipo_documento = TipoDocumento.objects.get(
        nombre__iexact=solicitud.tipo_solicitud.nombre
    )
    solicitud.revisado_por = presidente
    solicitud.comentario_revision = comentario
    solicitud.fecha_respuesta = timezone.now()
    solicitud.estado = "listo" if aprobar else "rechazada"
    solicitud.save()

    if aprobar:
        _crear_documento(solicitud, tipo_documento)

    notificar_decision(solicitud)
    return solicitud


def notificar_decision(solicitud):
    vecino = solicitud.solicitante
    nombre = vecino.get_full_name() or vecino.username

    if solicitud.estado == "listo":
        Notificacion.objects.create(
            destinatario=vecino,
            solicitud=solicitud,
            texto=_texto_corto(
                f"Tu solicitud {solicitud.folio} fue aprobada. "
                "El certificado está disponible."
            ),
        )
        documento = solicitud.documentos.order_by("-fecha_emision").first()
        adjunto = None
        if documento:
            documento.archivo.open("rb")
            try:
                adjunto = (
                    nombre_certificado(solicitud),
                    documento.archivo.read(),
                    "application/pdf",
                )
            finally:
                documento.archivo.close()
        _enviar_correo(
            f"Solicitud {solicitud.folio} aprobada",
            (
                f"Hola {nombre}:\n\n"
                f"Tu solicitud {solicitud.folio} fue aprobada. Adjuntamos tu "
                "certificado en PDF.\n\n"
                "Este correo fue generado automáticamente, por favor no responder."
            ),
            [vecino.email],
            adjunto=adjunto,
        )
        return

    comentario = solicitud.comentario_revision.strip()
    detalle = f" Motivo: {comentario}" if comentario else ""
    Notificacion.objects.create(
        destinatario=vecino,
        solicitud=solicitud,
        texto=_texto_corto(
            f"Tu solicitud {solicitud.folio} fue rechazada.{detalle}"
        ),
    )
    _enviar_correo(
        f"Solicitud {solicitud.folio} rechazada",
        (
            f"Hola {nombre}:\n\n"
            f"Tu solicitud {solicitud.folio} fue rechazada.{detalle}\n\n"
            "Este correo fue generado automáticamente, por favor no responder."
        ),
        [vecino.email],
    )


def enviar_certificado_por_email(solicitud):
    documento = solicitud.documentos.order_by("-fecha_emision").first()
    if documento is None or not documento.archivo:
        raise ValidationError("La solicitud no tiene un documento adjuntable.")

    nombre = solicitud.solicitante.get_full_name() or solicitud.solicitante.username
    junta = solicitud.solicitante.hogar.junta_vecinal

    documento.archivo.open("rb")
    try:
        adjunto = (
            nombre_certificado(solicitud),
            documento.archivo.read(),
            "application/pdf",
        )
    finally:
        documento.archivo.close()

    _enviar_correo(
        f"Solicitud {solicitud.folio} aprobada",
        (
            f"Hola {nombre}:\n\n"
            f"Adjuntamos tu certificado emitido por la Junta de Vecinos "
            f"{junta.nombre}, con folio {solicitud.folio}.\n\n"
            "Este correo fue generado automáticamente, por favor no responder."
        ),
        [solicitud.solicitante.email],
        adjunto=adjunto,
    )
