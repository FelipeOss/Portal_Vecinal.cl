from .mock_data import junta_por_id, notificaciones_de


def usuario_sesion(request):
    usuario = request.session.get("usuario")
    if not usuario:
        return {"usuario": None}
    contexto = {"usuario": usuario, "junta": junta_por_id(usuario.get("junta_id"))}
    if usuario["rol"] == "vecino":
        contexto["n_notif"] = sum(1 for n in notificaciones_de(usuario["nombre"]) if not n["leida"])
    return contexto
