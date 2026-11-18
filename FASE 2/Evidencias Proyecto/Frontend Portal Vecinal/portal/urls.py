from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("ingresar/", views.ingresar, name="ingresar"),
    path("salir/", views.salir, name="salir"),
    # Vecino
    path("vecino/", views.vecino_inicio, name="vecino_inicio"),
    path("vecino/solicitar/", views.vecino_solicitar, name="vecino_solicitar"),
    path("vecino/solicitudes/", views.vecino_solicitudes, name="vecino_solicitudes"),
    path("vecino/solicitudes/<int:pk>/", views.vecino_solicitud_detalle, name="vecino_solicitud_detalle"),
    path("vecino/notificaciones/", views.vecino_notificaciones, name="vecino_notificaciones"),
    # Presidente JV
    path("presidente/", views.presidente_inicio, name="presidente_inicio"),
    path("presidente/solicitudes/", views.presidente_solicitudes, name="presidente_solicitudes"),
    # Administrador
    path("administrador/", views.admin_inicio, name="admin_inicio"),
    path("administrador/juntas/", views.admin_juntas, name="admin_juntas"),
    path("administrador/usuarios/", views.admin_usuarios, name="admin_usuarios"),
]
