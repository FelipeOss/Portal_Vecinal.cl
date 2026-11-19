import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import SolicitudDocumentoForm
from .models import Documento, JuntaVecinal, Solicitud, TipoDocumento, Usuario
from .services import (
    TIPO_MANUAL,
    crear_solicitud_documento,
    crear_solicitud_revision,
    enviar_certificado_por_email,
    es_solicitud_manual,
    nombre_certificado,
    resolver_solicitud,
)
from .utils import normalizar_rut

logger = logging.getLogger(__name__)

ESTADOS_PLANTILLA = {
    "pendiente": "en_revision",
    "aprobada": "aprobada",
    "listo": "listo",
    "rechazada": "rechazada",
    "anulada": "rechazada",
}

ESPACIO_COMUN = "uso de espacio común"


def _respuesta_pdf(solicitud):
    documento = solicitud.documentos.order_by("-fecha_emision").first()
    if documento is None or not documento.archivo:
        raise Http404("La solicitud no tiene un documento disponible.")
    return FileResponse(
        documento.archivo.open("rb"),
        as_attachment=True,
        filename=nombre_certificado(solicitud),
        content_type="application/pdf",
    )


def destino_por_rol(usuario):
    if usuario.rol == "vecino":
        return "vecino_inicio"
    if usuario.rol == "presidente":
        return "presidente_inicio"
    return "admin_inicio"


def solo_roles(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required(login_url="login")
        def envoltorio(request, *args, **kwargs):
            if request.user.rol not in roles:
                messages.error(request, "No tienes permiso para acceder a esa sección.")
                return redirect(destino_por_rol(request.user))
            return vista(request, *args, **kwargs)

        return envoltorio

    return decorador


def presentar_solicitud(solicitud):
    es_espacio = solicitud.tipo_solicitud.nombre.lower() == ESPACIO_COMUN
    return {
        "id": solicitud.pk,
        "codigo": solicitud.folio,
        "tipo": solicitud.tipo_solicitud.nombre,
        "categoria": "espacio_comun" if es_espacio else "documento",
        "fecha": timezone.localtime(solicitud.fecha_solicitud).strftime("%d-%m-%Y %H:%M"),
        "estado": ESTADOS_PLANTILLA.get(solicitud.estado, "rechazada"),
        "vecino": solicitud.solicitante.get_full_name() or solicitud.solicitante.username,
        "rut": solicitud.solicitante.rut,
        "motivo": solicitud.observacion,
        "comentario": solicitud.comentario_revision,
        "uso": None,
    }


def inicio(request):
    if request.user.is_authenticated:
        return redirect(destino_por_rol(request.user))
    return redirect("login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect(destino_por_rol(request.user))

    if request.method == "POST":
        email = request.POST.get("correo", "").strip()
        clave = request.POST.get("clave", "").strip()
        usuario = (
            Usuario.objects.select_related("tipo_usuario")
            .filter(email__iexact=email)
            .first()
        )

        if usuario is None or not usuario.is_active:
            messages.error(request, "No existe una cuenta activa con ese correo.")
        else:
            es_vecino = (
                usuario.tipo_usuario is not None
                and usuario.tipo_usuario.nombre.lower() == "vecino"
            )
            if es_vecino:
                valido = bool(clave) and normalizar_rut(clave) == usuario.rut
            else:
                valido = usuario.check_password(clave)

            if valido:
                login(
                    request,
                    usuario,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                return redirect(destino_por_rol(usuario))

            messages.error(
                request,
                "Credenciales incorrectas. Revisa tu correo y tu contraseña o RUT.",
            )

    return render(request, "web/login.html")


def salir(request):
    logout(request)
    return redirect("login")


@solo_roles("vecino")
def vecino_inicio(request):
    solicitudes = Solicitud.objects.filter(solicitante=request.user)
    recientes = [presentar_solicitud(s) for s in solicitudes.order_by("-fecha_solicitud")[:5]]
    contexto = {
        "total": solicitudes.count(),
        "en_revision": solicitudes.filter(estado="pendiente").count(),
        "documentos": Documento.objects.filter(solicitud__solicitante=request.user).count(),
        "recientes": recientes,
        "notificaciones": request.user.notificaciones.all()[:5],
    }
    return render(request, "web/vecino/inicio.html", contexto)


@solo_roles("vecino")
def vecino_solicitar(request):
    if request.method == "POST":
        form = SolicitudDocumentoForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data["tipo"]
            motivo = form.cleaned_data["motivo"]

            if es_solicitud_manual(tipo):
                try:
                    solicitud = crear_solicitud_revision(request.user, tipo, motivo)
                except ValidationError as error:
                    form.add_error(None, error)
                else:
                    messages.success(
                        request,
                        f"Solicitud {solicitud.folio} enviada. Está en revisión "
                        "por la directiva de tu junta.",
                    )
                    return redirect("vecino_solicitudes")
            else:
                try:
                    solicitud, _ = crear_solicitud_documento(
                        request.user, tipo, motivo
                    )
                except ValidationError as error:
                    form.add_error(None, error)
                else:
                    try:
                        enviar_certificado_por_email(solicitud)
                    except Exception:
                        logger.exception(
                            "No se pudo enviar el certificado %s", solicitud.folio
                        )
                        messages.warning(
                            request,
                            "El certificado se generó correctamente, pero no se pudo "
                            "enviar por correo. Puedes descargarlo desde Mis solicitudes.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Solicitud {solicitud.folio} generada y enviada a "
                            f"{request.user.email}.",
                        )
                    return redirect(
                        f"{reverse('vecino_solicitudes')}?descargar={solicitud.pk}"
                    )
        else:
            messages.error(request, "Revisa los datos del formulario.")
    else:
        form = SolicitudDocumentoForm()

    habilitados = set(form.fields["tipo"].queryset.values_list("pk", flat=True))
    tipos = [
        {
            "codigo": tipo.pk,
            "nombre": tipo.nombre,
            "descripcion": "",
            "disponible": tipo.pk in habilitados,
        }
        for tipo in TipoDocumento.objects.filter(activo=True)
    ]
    contexto = {
        "tipos": tipos,
        "cat_inicial": request.GET.get("cat", "documento"),
    }
    return render(request, "web/vecino/solicitar.html", contexto)


@solo_roles("vecino")
def vecino_solicitudes(request):
    categoria = request.GET.get("cat")
    solicitudes = Solicitud.objects.filter(solicitante=request.user)
    items = [presentar_solicitud(s) for s in solicitudes.order_by("-fecha_solicitud")]
    n_documentos = sum(1 for i in items if i["categoria"] == "documento")
    n_espacios = len(items) - n_documentos

    if categoria == "documento":
        items = [i for i in items if i["categoria"] == "documento"]
    elif categoria == "espacio_comun":
        items = [i for i in items if i["categoria"] == "espacio_comun"]

    contexto = {
        "solicitudes": items,
        "cat": categoria,
        "n_todas": len(items) if categoria is None else len(solicitudes),
        "n_documentos": n_documentos,
        "n_espacios": n_espacios,
        "descarga_url": "",
    }

    descargar = request.GET.get("descargar")
    if descargar and descargar.isdigit():
        propia = Solicitud.objects.filter(
            pk=descargar, solicitante=request.user
        ).first()
        if propia:
            contexto["descarga_url"] = reverse(
                "vecino_solicitud_pdf", args=[propia.pk]
            )

    return render(request, "web/vecino/solicitudes.html", contexto)


@solo_roles("vecino")
def vecino_solicitud_detalle(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk, solicitante=request.user)

    if request.GET.get("descargar"):
        return _respuesta_pdf(solicitud)

    presentada = presentar_solicitud(solicitud)
    pasos = [
        {
            "texto": "Solicitud registrada",
            "detalle": presentada["fecha"],
            "estado": "hecho",
        },
        {"texto": "Seguimiento", "detalle": "", "estado": "hecho"},
        {"texto": "Documento listo", "detalle": "", "estado": "hecho"},
    ]
    return render(
        request, "web/vecino/solicitud_detalle.html", {"s": presentada, "pasos": pasos}
    )


@solo_roles("vecino")
def vecino_solicitud_pdf(request, pk):
    solicitud = get_object_or_404(Solicitud, pk=pk, solicitante=request.user)
    return _respuesta_pdf(solicitud)


@solo_roles("vecino")
def vecino_notificaciones(request):
    notificaciones = list(
        request.user.notificaciones.select_related("solicitud")[:50]
    )
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return render(
        request, "web/vecino/notificaciones.html", {"notificaciones": notificaciones}
    )


def _junta_de(usuario):
    return usuario.hogar.junta_vecinal if usuario.hogar_id else None


def _solicitudes_manuales(usuario):
    junta = _junta_de(usuario)
    if junta is None:
        return Solicitud.objects.none()
    return Solicitud.objects.filter(
        solicitante__hogar__junta_vecinal=junta,
        tipo_solicitud__nombre__iexact=TIPO_MANUAL,
    ).select_related(
        "solicitante__hogar__junta_vecinal",
        "tipo_solicitud",
        "revisado_por",
    )


@solo_roles("presidente")
def presidente_inicio(request):
    solicitudes = _solicitudes_manuales(request.user)
    junta = _junta_de(request.user)
    contexto = {
        "n_por_revisar": solicitudes.filter(estado="pendiente").count(),
        "n_aprobadas": solicitudes.filter(estado="listo").count(),
        "n_rechazadas": solicitudes.filter(estado="rechazada").count(),
        "n_vecinos": Usuario.objects.filter(hogar__junta_vecinal=junta).count()
        if junta
        else 0,
        "por_revisar": [
            presentar_solicitud(s) for s in solicitudes.filter(estado="pendiente")[:5]
        ],
        "n_documentos": Documento.objects.filter(
            solicitud__solicitante__hogar__junta_vecinal=junta
        ).count()
        if junta
        else 0,
    }
    return render(request, "web/presidente/inicio.html", contexto)


@solo_roles("presidente")
def presidente_solicitudes(request):
    items = [
        presentar_solicitud(s)
        for s in _solicitudes_manuales(request.user).order_by("-fecha_solicitud")
    ]
    items.sort(key=lambda item: item["estado"] != "en_revision")
    return render(
        request, "web/presidente/solicitudes.html", {"solicitudes": items}
    )


@solo_roles("presidente")
def presidente_notificaciones(request):
    notificaciones = list(
        request.user.notificaciones.select_related("solicitud")[:50]
    )
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return render(
        request,
        "web/presidente/notificaciones.html",
        {"notificaciones": notificaciones},
    )


@solo_roles("presidente")
def presidente_resolver(request, pk):
    if request.method != "POST":
        return redirect("presidente_solicitudes")

    solicitud = get_object_or_404(_solicitudes_manuales(request.user), pk=pk)
    accion = request.POST.get("accion")
    if accion not in ("aprobar", "rechazar"):
        messages.error(request, "Acción inválida.")
        return redirect("presidente_solicitudes")

    comentario = request.POST.get("comentario", "").strip()
    try:
        resolver_solicitud(
            solicitud, request.user, accion == "aprobar", comentario
        )
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        if accion == "aprobar":
            messages.success(
                request,
                f"Solicitud {solicitud.folio} aprobada. Se envió el certificado.",
            )
        else:
            messages.success(request, f"Solicitud {solicitud.folio} rechazada.")
    return redirect("presidente_solicitudes")


def _juntas_para_panel():
    juntas = JuntaVecinal.objects.all().order_by("nombre")
    filas = []
    sin_presidente = []
    for junta in juntas:
        presidentes = Usuario.objects.filter(
            hogar__junta_vecinal=junta, tipo_usuario__nombre__iexact="Presidente"
        )
        presidente = presidentes.first()
        filas.append(
            {
                "nombre": junta.nombre,
                "sector": "",
                "vecinos": Usuario.objects.filter(hogar__junta_vecinal=junta).count(),
                "presidente": (
                    presidente.get_full_name() or presidente.username
                    if presidente
                    else "Sin asignar"
                ),
            }
        )
        if presidente is None:
            sin_presidente.append(junta)
    return filas, sin_presidente


@solo_roles("administrador")
def admin_inicio(request):
    filas, sin_presidente = _juntas_para_panel()
    espacios = Solicitud.objects.filter(tipo_solicitud__nombre__iexact=ESPACIO_COMUN)
    contexto = {
        "n_juntas": JuntaVecinal.objects.count(),
        "n_usuarios": Usuario.objects.count(),
        "n_documentos": Documento.objects.count(),
        "n_espacios": espacios.count(),
        "n_en_revision": espacios.filter(estado="pendiente").count(),
        "n_aprobadas": espacios.filter(estado="aprobada").count(),
        "n_rechazadas": espacios.filter(estado="rechazada").count(),
        "juntas": filas,
        "sin_presidente": sin_presidente,
    }
    return render(request, "web/admin_panel/inicio.html", contexto)


@solo_roles("administrador")
def admin_juntas(request):
    filas, _ = _juntas_para_panel()
    return render(request, "web/admin_panel/juntas.html", {"juntas": filas})


@solo_roles("administrador")
def admin_usuarios(request):
    usuarios = [
        {
            "nombre": usuario.get_full_name() or usuario.username,
            "rut": usuario.rut,
            "correo": usuario.email,
            "rol": usuario.rol,
            "junta": usuario.hogar.junta_vecinal if usuario.hogar_id else None,
        }
        for usuario in Usuario.objects.select_related(
            "hogar__junta_vecinal", "tipo_usuario"
        ).order_by("first_name", "last_name")
    ]
    return render(request, "web/admin_panel/usuarios.html", {"usuarios": usuarios})
