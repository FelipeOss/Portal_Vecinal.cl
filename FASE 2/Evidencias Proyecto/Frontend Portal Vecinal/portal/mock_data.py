"""Datos de ejemplo para demostrar el front end sin backend.

Cuando exista la API / base de datos, reemplazar estas funciones por
consultas reales (ORM o llamadas a los otros servicios).

Modelo TO-BE:
- Solicitud de DOCUMENTO: el sistema registra, actualiza el seguimiento,
  prepara el PDF y lo envía al vecino (sin intervención del presidente).
- Solicitud de ESPACIO COMÚN: el presidente de la junta la revisa y
  la aprueba o rechaza; el vecino recibe una notificación con el resultado.
"""
import re


def calcular_dv(cuerpo: str) -> str:
    suma, mult = 0, 2
    for d in reversed(str(cuerpo)):
        suma += int(d) * mult
        mult = 2 if mult == 7 else mult + 1
    r = 11 - suma % 11
    return "0" if r == 11 else "K" if r == 10 else str(r)


def formatear_rut(cuerpo: str) -> str:
    return f"{int(cuerpo):,}".replace(",", ".") + "-" + calcular_dv(cuerpo)


def normalizar_rut(texto: str):
    """Devuelve (rut_formateado, es_valido)."""
    limpio = re.sub(r"[^0-9kK]", "", texto or "").upper()
    if len(limpio) < 2:
        return texto, False
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        return texto, False
    return formatear_rut(cuerpo), calcular_dv(cuerpo) == dv


CATEGORIAS = {"documento": "Documento", "espacio_comun": "Espacio común"}

JUNTAS = [
    {"id": 1, "nombre": "JV Villa Los Aromos", "sector": "Sector Norte", "vecinos": 214, "presidente": "Marta Rojas Pizarro"},
    {"id": 2, "nombre": "JV Población Santa Rosa", "sector": "Sector Centro", "vecinos": 342, "presidente": "Jorge Tapia Contreras"},
    {"id": 3, "nombre": "JV El Mirador", "sector": "Sector Poniente", "vecinos": 128, "presidente": "Carolina Araya Soto"},
    {"id": 4, "nombre": "JV Las Palmeras", "sector": "Sector Sur", "vecinos": 187, "presidente": "Sin asignar"},
]

USUARIOS = [
    {"rut": formatear_rut("11111111"), "correo": "admin@municipio.cl", "nombre": "Administrador Municipal", "rol": "administrador", "junta_id": None},
    {"rut": formatear_rut("12345678"), "correo": "presidente@jv.cl", "nombre": "Marta Rojas Pizarro", "rol": "presidente", "junta_id": 1},
    {"rut": formatear_rut("18765432"), "correo": "vecino@correo.cl", "nombre": "Felipe Andrade Mora", "rol": "vecino", "junta_id": 1},
    {"rut": formatear_rut("9876543"), "correo": "ana.molina@correo.cl", "nombre": "Ana Molina Vera", "rol": "vecino", "junta_id": 1},
    {"rut": formatear_rut("15432109"), "correo": "luis.soto@correo.cl", "nombre": "Luis Soto Fuentes", "rol": "vecino", "junta_id": 2},
]

TIPOS_DOCUMENTO = [
    {"codigo": "residencia", "nombre": "Certificado de residencia", "descripcion": "Acredita tu domicilio dentro del territorio de la junta de vecinos."},
    {"codigo": "afiliacion", "nombre": "Certificado de afiliación", "descripcion": "Acredita que eres socio/a activo/a de la junta de vecinos."},
    {"codigo": "antiguedad", "nombre": "Certificado de antigüedad", "descripcion": "Indica desde cuándo resides en el sector."},
]

ESPACIOS = [
    {"codigo": "sede", "nombre": "Sede vecinal", "capacidad": 60},
    {"codigo": "multicancha", "nombre": "Multicancha", "capacidad": 40},
    {"codigo": "plaza", "nombre": "Plaza / área verde", "capacidad": 100},
]

# Estados: "listo" (documento enviado), "en_revision", "aprobada", "rechazada"
SOLICITUDES = [
    {"id": 1045, "categoria": "espacio_comun", "tipo": "Sede vecinal", "vecino": "Felipe Andrade Mora", "rut": formatear_rut("18765432"),
     "fecha": "15-11-2026", "estado": "en_revision", "motivo": "Cumpleaños familiar", "junta_id": 1,
     "uso": {"fecha": "05-12-2026", "horario": "18:00 a 22:00", "personas": 30}},
    {"id": 1042, "categoria": "documento", "tipo": "Certificado de residencia", "vecino": "Felipe Andrade Mora", "rut": formatear_rut("18765432"),
     "fecha": "12-11-2026", "estado": "listo", "motivo": "Trámite bancario", "junta_id": 1},
    {"id": 1040, "categoria": "espacio_comun", "tipo": "Multicancha", "vecino": "Ana Molina Vera", "rut": formatear_rut("9876543"),
     "fecha": "11-11-2026", "estado": "en_revision", "motivo": "Campeonato de baby fútbol", "junta_id": 1,
     "uso": {"fecha": "28-11-2026", "horario": "15:00 a 19:00", "personas": 20}},
    {"id": 1038, "categoria": "documento", "tipo": "Certificado de afiliación", "vecino": "Ana Molina Vera", "rut": formatear_rut("9876543"),
     "fecha": "10-11-2026", "estado": "listo", "motivo": "Postulación a subsidio", "junta_id": 1},
    {"id": 1036, "categoria": "documento", "tipo": "Certificado de antigüedad", "vecino": "Felipe Andrade Mora", "rut": formatear_rut("18765432"),
     "fecha": "04-11-2026", "estado": "listo", "motivo": "Matrícula escolar", "junta_id": 1},
    {"id": 1031, "categoria": "espacio_comun", "tipo": "Multicancha", "vecino": "Felipe Andrade Mora", "rut": formatear_rut("18765432"),
     "fecha": "03-11-2026", "estado": "aprobada", "motivo": "Partido entre vecinos", "junta_id": 1,
     "uso": {"fecha": "14-11-2026", "horario": "16:00 a 18:00", "personas": 12}},
    {"id": 1027, "categoria": "documento", "tipo": "Certificado de residencia", "vecino": "Ana Molina Vera", "rut": formatear_rut("9876543"),
     "fecha": "29-10-2026", "estado": "listo", "motivo": "Trámite en notaría", "junta_id": 1},
    {"id": 1019, "categoria": "espacio_comun", "tipo": "Sede vecinal", "vecino": "Felipe Andrade Mora", "rut": formatear_rut("18765432"),
     "fecha": "20-10-2026", "estado": "rechazada", "motivo": "Reunión de curso", "junta_id": 1,
     "comentario": "La sede ya estaba reservada para esa fecha.",
     "uso": {"fecha": "31-10-2026", "horario": "20:00 a 23:00", "personas": 40}},
]

for _s in SOLICITUDES:
    _s["codigo"] = f"SEG-{_s['id']}"


def buscar_usuario(rut: str, correo: str):
    rut_fmt, ok = normalizar_rut(rut)
    if not ok:
        return None
    for u in USUARIOS:
        if u["rut"] == rut_fmt and u["correo"].lower() == (correo or "").strip().lower():
            return u
    return None


def junta_por_id(junta_id):
    return next((j for j in JUNTAS if j["id"] == junta_id), None)


def solicitud_por_id(pk):
    return next((s for s in SOLICITUDES if s["id"] == pk), None)


def linea_tiempo(s):
    """Pasos del seguimiento de una solicitud, según el modelo TO-BE."""
    registro = {"texto": "Solicitud registrada", "detalle": f"Código de seguimiento {s['codigo']}", "estado": "hecho"}

    if s["categoria"] == "documento":
        listo = s["estado"] == "listo"
        marca = "hecho" if listo else "pendiente"
        return [
            registro,
            {"texto": "Seguimiento actualizado", "detalle": "El sistema procesa tu solicitud automáticamente", "estado": marca},
            {"texto": "PDF preparado", "detalle": "Se genera el documento con tus datos", "estado": marca},
            {"texto": "PDF enviado a tu correo", "detalle": "También puedes descargarlo desde aquí", "estado": marca},
        ]

    # Espacio común
    estado = s["estado"]
    revision = {
        "texto": "Revisión del presidente",
        "detalle": "El presidente de tu junta revisa la solicitud",
        "estado": "actual" if estado == "en_revision" else "hecho",
    }
    if estado == "en_revision":
        decision = {"texto": "Decisión", "detalle": "Te notificaremos cuando haya una respuesta", "estado": "pendiente"}
    elif estado == "aprobada":
        decision = {"texto": "Solicitud aprobada", "detalle": "El espacio queda reservado para ti", "estado": "hecho"}
    else:
        decision = {"texto": "Solicitud rechazada", "detalle": s.get("comentario", ""), "estado": "error"}
    return [registro, revision, decision]


def notificaciones_de(nombre):
    """Notificaciones del vecino: una por cada solicitud ya resuelta."""
    resueltas = sorted(
        (s for s in SOLICITUDES if s["vecino"] == nombre and s["estado"] != "en_revision"),
        key=lambda s: s["id"],
        reverse=True,
    )
    notifs = []
    for i, s in enumerate(resueltas):
        if s["estado"] == "listo":
            texto = f"Tu {s['tipo'].lower()} está listo. Te enviamos el PDF a tu correo."
            enlace = "Ver documento"
        elif s["estado"] == "aprobada":
            texto = f"Tu solicitud de {s['tipo'].lower()} fue aprobada por el presidente."
            enlace = "Ver solicitud"
        else:
            texto = f"Tu solicitud de {s['tipo'].lower()} fue rechazada."
            enlace = "Ver solicitud"
        notifs.append({"solicitud": s, "texto": texto, "enlace": enlace, "fecha": s["fecha"], "leida": i >= 2})
    return notifs
