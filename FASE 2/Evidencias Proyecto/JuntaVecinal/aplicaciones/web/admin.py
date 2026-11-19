from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Comuna,
    Documento,
    Hogar,
    JuntaVecinal,
    Notificacion,
    Solicitud,
    TipoDocumento,
    TipoSolicitud,
    TipoUsuario,
    Usuario,
)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "rut", "email", "tipo_usuario", "hogar", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Datos vecinales",
            {"fields": ("rut", "fecha_nacimiento", "tipo_usuario", "hogar")},
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Datos vecinales",
            {"fields": ("rut", "email", "fecha_nacimiento", "tipo_usuario", "hogar")},
        ),
    )


admin.site.register(Comuna)
admin.site.register(JuntaVecinal)
admin.site.register(Hogar)
admin.site.register(TipoUsuario)
admin.site.register(TipoDocumento)
admin.site.register(TipoSolicitud)
admin.site.register(Solicitud)
admin.site.register(Documento)
admin.site.register(Notificacion)
