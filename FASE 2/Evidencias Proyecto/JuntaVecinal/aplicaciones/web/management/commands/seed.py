from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from aplicaciones.web.models import (
    Comuna,
    Hogar,
    JuntaVecinal,
    TipoDocumento,
    TipoSolicitud,
    TipoUsuario,
)

PASSWORD_DEMO = "demo1234"

COMUNAS = {
    "Macul": "Los Plátanos 3130, Macul",
    "La Florida": "Av. Vicuña Mackenna 10777, La Florida",
    "San Joaquín": "Av. Santa Rosa 2606, San Joaquín",
}

JUNTAS = [
    {
        "nombre": "Sede Villa Bancaria Y Santa Elena U.V.17",
        "direccion": "Mauricio Rugendas 5409, Macul",
        "comuna": "Macul",
        "rut": "222222222",
        "email": "villase@gmail.cl",
    },
    {
        "nombre": "Junta de Vecinos de la Unidad Vecinal N°13 Trinidad Villa Los Peumos La Florida",
        "direccion": "Dr. Sótero del Río 564, La Florida",
        "comuna": "La Florida",
        "rut": "333333333",
        "email": "trinidadvlp@gmail.cl",
    },
    {
        "nombre": "Junta de Vecinos N°9",
        "direccion": "Vecinal 5379, San Joaquín",
        "comuna": "San Joaquín",
        "rut": "444444444",
        "email": "juntavecinos9@gmail.cl",
    },
]

HOGARES = [
    {
        "direccion": "Alfonso Leng 5569, Macul",
        "junta": "Sede Villa Bancaria Y Santa Elena U.V.17",
    },
    {
        "direccion": "Alfonso Leng 5579, Macul",
        "junta": "Sede Villa Bancaria Y Santa Elena U.V.17",
    },
    {
        "direccion": "Av. Colo-Colo 777, Macul",
        "junta": "Sede Villa Bancaria Y Santa Elena U.V.17",
    },
    {
        "direccion": "Vicuña Mackenna con Departamental, Macul",
        "junta": "Sede Villa Bancaria Y Santa Elena U.V.17",
    },
    {
        "direccion": "Celia Solar 63, San Joaquín",
        "junta": "Junta de Vecinos N°9",
    },
    {
        "direccion": "Froilán Roa 6542, La Florida",
        "junta": "Junta de Vecinos de la Unidad Vecinal N°13 Trinidad Villa Los Peumos La Florida",
    },
]

TIPOS_USUARIO = ["Vecino", "Presidente", "Administrador"]

TIPOS_DOCUMENTO = [
    "Certificado de residencia",
    "Certificado de afiliación",
    "Certificado de antigüedad",
    "Certificado de buena conducta o referencia vecinal",
]

TIPOS_SOLICITUD = TIPOS_DOCUMENTO + ["Uso de espacio común"]

USUARIOS = [
    {
        "rut": "198765436",
        "email": "camila.rojas@example.cl",
        "nombres": "Camila",
        "apellidos": "Rojas Fuentes",
        "tipo": "Vecino",
        "hogar": "Alfonso Leng 5569, Macul",
        "is_staff": False,
        "fecha_afiliacion": "2019-03-12",
    },
    {
        "rut": "154876321",
        "email": "jorge.medina@example.cl",
        "nombres": "Jorge",
        "apellidos": "Medina Salas",
        "tipo": "Presidente",
        "hogar": "Froilán Roa 6542, La Florida",
        "is_staff": False,
        "fecha_afiliacion": "2015-08-20",
    },
    {
        "rut": "17654321K",
        "email": "paula.herrera@example.cl",
        "nombres": "Paula",
        "apellidos": "Herrera Soto",
        "tipo": "Administrador",
        "hogar": None,
        "is_staff": True,
        "fecha_afiliacion": "2020-01-15",
    },
    {
        "rut": "201009049",
        "email": "mi.montero@duocuc.cl",
        "nombres": "Miguel Angel",
        "apellidos": "Montero Lobos",
        "tipo": "Vecino",
        "hogar": "Alfonso Leng 5579, Macul",
        "is_staff": False,
        "fecha_afiliacion": "2021-05-10",
    },
    {
        "rut": "182778379",
        "email": "yer.paredes@profesor.duoc.cl",
        "nombres": "Yerko",
        "apellidos": "Paredes Orellana",
        "tipo": "Vecino",
        "hogar": "Av. Colo-Colo 777, Macul",
        "is_staff": False,
        "fecha_nacimiento": "1990-12-09",
        "fecha_afiliacion": "2023-04-18",
    },
    {
        "rut": "208066498",
        "email": "feli.guajardo@duocuc.cl",
        "nombres": "Felipe Alberto",
        "apellidos": "Guajardo",
        "tipo": "Presidente",
        "hogar": "Vicuña Mackenna con Departamental, Macul",
        "is_staff": False,
        "fecha_nacimiento": "2001-07-21",
        "fecha_afiliacion": "2022-09-05",
        "password": "5633124",
    },
]


class Command(BaseCommand):
    help = "Carga catálogos, comunas, juntas, hogares y usuarios demo (idempotente)."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.creados = 0
        self.existentes = 0

    def _get_or_create(self, model, defaults=None, **lookup):
        obj, created = model.objects.get_or_create(defaults=defaults, **lookup)
        if created:
            self.creados += 1
        else:
            self.existentes += 1
        return obj

    @transaction.atomic
    def handle(self, *args, **options):
        Usuario = get_user_model()

        comunas = {
            nombre: self._get_or_create(
                Comuna, nombre=nombre, defaults={"direccion_municipalidad": direccion}
            )
            for nombre, direccion in COMUNAS.items()
        }

        juntas = {}
        for data in JUNTAS:
            juntas[data["nombre"]] = self._get_or_create(
                JuntaVecinal,
                nombre=data["nombre"],
                defaults={
                    "direccion": data["direccion"],
                    "comuna": comunas[data["comuna"]],
                    "rut": data["rut"],
                    "email": data["email"],
                },
            )

        hogares = {}
        for data in HOGARES:
            hogares[data["direccion"]] = self._get_or_create(
                Hogar,
                junta_vecinal=juntas[data["junta"]],
                direccion=data["direccion"],
            )

        tipos_usuario = {}
        for nombre in TIPOS_USUARIO:
            tipos_usuario[nombre] = self._get_or_create(TipoUsuario, nombre=nombre)

        for nombre in TIPOS_DOCUMENTO:
            self._get_or_create(TipoDocumento, nombre=nombre)

        for nombre in TIPOS_SOLICITUD:
            self._get_or_create(TipoSolicitud, nombre=nombre)

        for data in USUARIOS:
            usuario, created = Usuario.objects.get_or_create(
                username=data["rut"],
                defaults={
                    "rut": data["rut"],
                    "email": data["email"],
                    "first_name": data["nombres"],
                    "last_name": data["apellidos"],
                    "tipo_usuario": tipos_usuario[data["tipo"]],
                    "hogar": hogares[data["hogar"]] if data["hogar"] else None,
                    "is_staff": data["is_staff"],
                    "fecha_nacimiento": data.get("fecha_nacimiento") or None,
                    "fecha_afiliacion": data.get("fecha_afiliacion") or None,
                },
            )
            if created:
                usuario.set_password(data.get("password", PASSWORD_DEMO))
                usuario.save()
                self.creados += 1
            else:
                self.existentes += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Semillas listas: {self.creados} creados, {self.existentes} ya existían."
            )
        )
