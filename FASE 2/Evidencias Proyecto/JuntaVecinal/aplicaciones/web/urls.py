from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("salir/", views.salir, name="salir"),
    path("vecino/", views.vecino_inicio, name="vecino_inicio"),
    path("vecino/solicitar/", views.vecino_solicitar, name="vecino_solicitar"),
    path("vecino/solicitudes/", views.vecino_solicitudes, name="vecino_solicitudes"),
    path(
        "vecino/solicitudes/<int:pk>/",
        views.vecino_solicitud_detalle,
        name="vecino_solicitud_detalle",
    ),
    path(
        "vecino/solicitudes/<int:pk>/pdf/",
        views.vecino_solicitud_pdf,
        name="vecino_solicitud_pdf",
    ),
    path(
        "vecino/notificaciones/",
        views.vecino_notificaciones,
        name="vecino_notificaciones",
    ),
    path("presidente/", views.presidente_inicio, name="presidente_inicio"),
    path(
        "presidente/solicitudes/",
        views.presidente_solicitudes,
        name="presidente_solicitudes",
    ),
    path(
        "presidente/solicitudes/<int:pk>/resolver/",
        views.presidente_resolver,
        name="presidente_resolver",
    ),
    path(
        "presidente/notificaciones/",
        views.presidente_notificaciones,
        name="presidente_notificaciones",
    ),
    path("panel/", views.admin_inicio, name="admin_inicio"),
    path("panel/juntas/", views.admin_juntas, name="admin_juntas"),
    path("panel/usuarios/", views.admin_usuarios, name="admin_usuarios"),
]
