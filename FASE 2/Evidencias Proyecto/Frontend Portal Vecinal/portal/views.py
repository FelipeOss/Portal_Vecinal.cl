from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect, render

from . import mock_data as datos

HOME_POR_ROL = {
    "vecino": "vecino_inicio",
    "presidente": "presidente_inicio",
    "administrador": "admin_inicio",
}


def rol_requerido(rol):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            usuario = request.session.get("usuario")
            if not usuario:
                return redirect("ingresar")
            if usuario["rol"] != rol:
                return redirect(HOME_POR_ROL[usuario["rol"]])
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


# ---------- Acceso ----------

def inicio(request):
    usuario = request.session.get("usuario")
    if usuario:
        return redirect(HOME_POR_ROL[usuario["rol"]])
    return redirect("ingresar")


def ingresar(request):
    if request.method == "POST":
        rut = request.POST.get("rut", "")
        correo = request.POST.get("correo", "")
        _, rut_valido = datos.normalizar_rut(rut)
        if not rut_valido:
            messages.error(request, "El RUT ingresado no es válido. Revisa el dígito verificador.")
        else:
            usuario = datos.buscar_usuario(rut, correo)
            if usuario is None:
                messages.error(request, "No encontramos una cuenta con ese RUT y correo.")
            else:
                request.session["usuario"] = usuario
                return redirect(HOME_POR_ROL[usuario["rol"]])
    return render(request, "login.html", {"cuentas_demo": datos.USUARIOS[:3]})


def salir(request):
    request.session.flush()
    return redirect("ingresar")


# ---------- Vecino ----------

def _solicitudes_del_vecino(request):
    nombre = request.session["usuario"]["nombre"]
    return [s for s in datos.SOLICITUDES if s["vecino"] == nombre]


@rol_requerido("vecino")
def vecino_inicio(request):
    mias = _solicitudes_del_vecino(request)
    nombre = request.session["usuario"]["nombre"]
    contexto = {
        "recientes": mias[:4],
        "total": len(mias),
        "en_revision": sum(1 for s in mias if s["estado"] == "en_revision"),
        "documentos": sum(1 for s in mias if s["estado"] == "listo"),
        "notificaciones": datos.notificaciones_de(nombre)[:3],
    }
    return render(request, "vecino/inicio.html", contexto)


@rol_requerido("vecino")
def vecino_solicitar(request):
    categoria = request.POST.get("categoria") or request.GET.get("cat") or ""
    if categoria not in datos.CATEGORIAS:
        categoria = ""

    if request.method == "POST":
        codigo = f"SEG-{max(s['id'] for s in datos.SOLICITUDES) + 1}"

        if categoria == "documento":
            tipo = next((t for t in datos.TIPOS_DOCUMENTO if t["codigo"] == request.POST.get("tipo")), None)
            if tipo:
                messages.success(
                    request,
                    f"Solicitud registrada con el código {codigo}. Estamos preparando tu «{tipo['nombre']}»; "
                    "te avisaremos y recibirás el PDF en tu correo.",
                )
                return redirect("vecino_solicitudes")
            messages.error(request, "Selecciona el documento que necesitas.")

        elif categoria == "espacio_comun":
            espacio = next((e for e in datos.ESPACIOS if e["codigo"] == request.POST.get("espacio")), None)
            completo = all(request.POST.get(c) for c in ("fecha_uso", "hora_inicio", "hora_fin", "personas"))
            if espacio and completo:
                messages.success(
                    request,
                    f"Solicitud registrada con el código {codigo}. El presidente de tu junta revisará tu "
                    f"solicitud de «{espacio['nombre']}» y te notificaremos su decisión.",
                )
                return redirect("vecino_solicitudes")
            messages.error(request, "Completa los datos de la reserva del espacio común.")

        else:
            messages.error(request, "Elige qué quieres solicitar.")

    contexto = {
        "tipos": datos.TIPOS_DOCUMENTO,
        "espacios": datos.ESPACIOS,
        "cat_inicial": categoria,
    }
    return render(request, "vecino/solicitar.html", contexto)


@rol_requerido("vecino")
def vecino_solicitudes(request):
    mias = _solicitudes_del_vecino(request)
    cat = request.GET.get("cat", "")
    filtradas = [s for s in mias if s["categoria"] == cat] if cat in datos.CATEGORIAS else mias
    contexto = {
        "solicitudes": filtradas,
        "cat": cat if cat in datos.CATEGORIAS else "",
        "n_todas": len(mias),
        "n_documentos": sum(1 for s in mias if s["categoria"] == "documento"),
        "n_espacios": sum(1 for s in mias if s["categoria"] == "espacio_comun"),
    }
    return render(request, "vecino/solicitudes.html", contexto)


@rol_requerido("vecino")
def vecino_solicitud_detalle(request, pk):
    s = datos.solicitud_por_id(pk)
    if not s or s["vecino"] != request.session["usuario"]["nombre"]:
        messages.error(request, "No encontramos esa solicitud.")
        return redirect("vecino_solicitudes")
    if request.GET.get("descargar"):
        messages.info(request, "Demo: aquí se descargará el PDF cuando el backend esté conectado.")
        return redirect("vecino_solicitud_detalle", pk=pk)
    return render(request, "vecino/solicitud_detalle.html", {"s": s, "pasos": datos.linea_tiempo(s)})


@rol_requerido("vecino")
def vecino_notificaciones(request):
    nombre = request.session["usuario"]["nombre"]
    return render(request, "vecino/notificaciones.html", {"notificaciones": datos.notificaciones_de(nombre)})


# ---------- Presidente JV ----------
# En el modelo TO-BE el presidente solo revisa solicitudes de espacio común.
# Los documentos los genera el sistema de forma automática.

def _de_la_junta(request):
    junta_id = request.session["usuario"]["junta_id"]
    return [s for s in datos.SOLICITUDES if s["junta_id"] == junta_id]


@rol_requerido("presidente")
def presidente_inicio(request):
    de_mi_junta = _de_la_junta(request)
    espacios = [s for s in de_mi_junta if s["categoria"] == "espacio_comun"]
    contexto = {
        "por_revisar": [s for s in espacios if s["estado"] == "en_revision"],
        "n_por_revisar": sum(1 for s in espacios if s["estado"] == "en_revision"),
        "n_aprobadas": sum(1 for s in espacios if s["estado"] == "aprobada"),
        "n_rechazadas": sum(1 for s in espacios if s["estado"] == "rechazada"),
        "n_documentos": sum(1 for s in de_mi_junta if s["categoria"] == "documento"),
        "n_vecinos": (datos.junta_por_id(request.session["usuario"]["junta_id"]) or {}).get("vecinos", 0),
    }
    return render(request, "presidente/inicio.html", contexto)


@rol_requerido("presidente")
def presidente_solicitudes(request):
    if request.method == "POST":
        accion = request.POST.get("accion")
        codigo = f"SEG-{request.POST.get('solicitud')}"
        if accion == "aprobar":
            messages.success(request, f"Solicitud {codigo} aprobada. Se notificará al vecino.")
        elif accion == "rechazar":
            messages.warning(request, f"Solicitud {codigo} rechazada. Se notificará al vecino.")
        return redirect("presidente_solicitudes")
    espacios = [s for s in _de_la_junta(request) if s["categoria"] == "espacio_comun"]
    return render(request, "presidente/solicitudes.html", {"solicitudes": espacios})


# ---------- Administrador ----------

@rol_requerido("administrador")
def admin_inicio(request):
    docs = [s for s in datos.SOLICITUDES if s["categoria"] == "documento"]
    espacios = [s for s in datos.SOLICITUDES if s["categoria"] == "espacio_comun"]
    contexto = {
        "n_juntas": len(datos.JUNTAS),
        "n_usuarios": len(datos.USUARIOS),
        "n_documentos": len(docs),
        "n_espacios": len(espacios),
        "n_en_revision": sum(1 for s in espacios if s["estado"] == "en_revision"),
        "n_aprobadas": sum(1 for s in espacios if s["estado"] == "aprobada"),
        "n_rechazadas": sum(1 for s in espacios if s["estado"] == "rechazada"),
        "juntas": datos.JUNTAS,
        "sin_presidente": [j for j in datos.JUNTAS if j["presidente"] == "Sin asignar"],
    }
    return render(request, "admin_panel/inicio.html", contexto)


@rol_requerido("administrador")
def admin_juntas(request):
    return render(request, "admin_panel/juntas.html", {"juntas": datos.JUNTAS})


@rol_requerido("administrador")
def admin_usuarios(request):
    usuarios = [{**u, "junta": datos.junta_por_id(u["junta_id"])} for u in datos.USUARIOS]
    return render(request, "admin_panel/usuarios.html", {"usuarios": usuarios})
