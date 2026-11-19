def portal(request):
    usuario = request.user if request.user.is_authenticated else None
    junta = usuario.hogar.junta_vecinal if usuario and usuario.hogar_id else None
    no_leidas = (
        usuario.notificaciones.filter(leida=False).count() if usuario else 0
    )
    return {
        "usuario": usuario,
        "junta": junta,
        "n_notif": no_leidas,
    }
