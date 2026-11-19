from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib.staticfiles import finders
from django.utils import timezone
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .utils import formatear_rut

MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

TITULOS = {
    "residencia": "CERTIFICADO DE RESIDENCIA",
    "afiliacion": "CERTIFICADO DE AFILIACIÓN",
    "antiguedad": "CERTIFICADO DE ANTIGÜEDAD",
    "buena_conducta": "CERTIFICADO DE BUENA CONDUCTA",
}

EN_BLANCO = "_" * 50


def _fecha_larga(fecha):
    return f"{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def _ruta_imagen(nombre):
    return finders.find(f"img/{nombre}")


def _logo_chile():
    ruta = _ruta_imagen("logo_chile.png")
    if not ruta:
        return []
    lector = ImageReader(ruta)
    ancho_px, alto_px = lector.getSize()
    ancho = 2.6 * cm
    alto = ancho * alto_px / ancho_px
    logo = Image(ruta, width=ancho, height=alto)
    logo.hAlign = "CENTER"
    return [logo, Spacer(1, 0.7 * cm)]


class BloqueFirma(Flowable):
    def __init__(self, ruta_firma, nombre_junta):
        super().__init__()
        self.ruta_firma = ruta_firma
        self.nombre_junta = nombre_junta
        self._ancho_imagen = 0
        self._alto_imagen = 0

    def wrap(self, availWidth, availHeight):
        self.ancho_disponible = availWidth
        if self.ruta_firma:
            lector = ImageReader(self.ruta_firma)
            ancho_px, alto_px = lector.getSize()
            ancho = 4.8 * cm
            alto = ancho * alto_px / ancho_px
            if alto > 2.2 * cm:
                alto = 2.2 * cm
                ancho = alto * ancho_px / alto_px
            self._ancho_imagen = ancho
            self._alto_imagen = alto
        self.height = self._alto_imagen + 1.6 * cm
        return availWidth, self.height

    def draw(self):
        lienzo = self.canv
        centro = self.ancho_disponible / 2
        linea_y = 1.2 * cm

        if self.ruta_firma:
            lienzo.drawImage(
                ImageReader(self.ruta_firma),
                centro - self._ancho_imagen / 2,
                linea_y,
                width=self._ancho_imagen,
                height=self._alto_imagen,
                mask="auto",
            )

        lienzo.saveState()
        lienzo.setLineWidth(0.8)
        lienzo.line(centro - 3 * cm, linea_y, centro + 3 * cm, linea_y)
        lienzo.restoreState()

        lienzo.setFont("Helvetica", 10.5)
        lienzo.drawCentredString(centro, linea_y - 0.55 * cm, "Directiva")
        lienzo.setFont("Helvetica", 9.5)
        lienzo.drawCentredString(
            centro, linea_y - 0.95 * cm, f"Junta de Vecinos {self.nombre_junta}"
        )


def _fecha_afiliacion(usuario):
    return usuario.fecha_afiliacion or timezone.localtime(usuario.date_joined).date()


def _antiguedad(desde, hasta):
    anios = hasta.year - desde.year
    meses = hasta.month - desde.month
    if hasta.day < desde.day:
        meses -= 1
    if meses < 0:
        anios -= 1
        meses += 12
    if anios < 0:
        return 0, 0
    return anios, meses


def _clave_tipo(nombre):
    nombre = nombre.lower()
    if "afiliaci" in nombre:
        return "afiliacion"
    if "antig" in nombre:
        return "antiguedad"
    if "conducta" in nombre or "referencia" in nombre:
        return "buena_conducta"
    return "residencia"


def _cuerpo(clave, usuario, junta):
    nombre = escape(usuario.get_full_name() or usuario.username)
    rut = formatear_rut(usuario.rut)
    direccion = escape(usuario.hogar.direccion)
    comuna = escape(junta.comuna.nombre)
    junta_nombre = escape(junta.nombre)
    afiliacion = _fecha_afiliacion(usuario)
    hoy = timezone.localdate()

    if clave == "afiliacion":
        return (
            f"La Junta de Vecinos <b>{junta_nombre}</b>, de la comuna de "
            f"<b>{comuna}</b>, certifica que don/doña <b>{nombre}</b>, RUT "
            f"<b>{rut}</b>, domiciliado/a en <b>{direccion}</b>, se encuentra "
            "inscrito/a como socio/a de esta unidad vecinal desde el "
            f"<b>{_fecha_larga(afiliacion)}</b>, con sus datos actualizados en "
            "el registro de socios."
        )

    if clave == "antiguedad":
        anios, meses = _antiguedad(afiliacion, hoy)
        return (
            f"La Junta de Vecinos <b>{junta_nombre}</b>, de la comuna de "
            f"<b>{comuna}</b>, certifica que don/doña <b>{nombre}</b>, RUT "
            f"<b>{rut}</b>, domiciliado/a en <b>{direccion}</b>, es socio/a de "
            f"esta unidad vecinal desde el <b>{_fecha_larga(afiliacion)}</b>, "
            f"con una antigüedad de <b>{anios} años y {meses} meses</b> a la "
            "fecha de emisión."
        )

    if clave == "buena_conducta":
        return (
            f"La Junta de Vecinos <b>{junta_nombre}</b>, de la comuna de "
            f"<b>{comuna}</b>, certifica que don/doña <b>{nombre}</b>, RUT "
            f"<b>{rut}</b>, domiciliado/a en <b>{direccion}</b>, es socio/a de "
            "esta unidad vecinal y no registra reclamos ni observaciones en su "
            "contra, contando con una buena referencia vecinal dentro de la "
            "comunidad."
        )

    return (
        f"La Junta de Vecinos <b>{junta_nombre}</b>, de la comuna de "
        f"<b>{comuna}</b>, certifica que don/doña <b>{nombre}</b>, RUT "
        f"<b>{rut}</b>, domiciliado/a en <b>{direccion}</b>, es socio/a de "
        "esta unidad vecinal."
    )


def generar_certificado(solicitud, tipo_documento):
    usuario = solicitud.solicitante
    junta = usuario.hogar.junta_vecinal
    clave = _clave_tipo(tipo_documento.nombre)
    fecha = timezone.localtime(solicitud.fecha_solicitud)

    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle(
        "Titulo",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        alignment=TA_CENTER,
        spaceAfter=24,
    )
    cuerpo = ParagraphStyle(
        "Cuerpo",
        parent=estilos["BodyText"],
        fontName="Helvetica",
        fontSize=11.5,
        leading=18,
        alignment=TA_JUSTIFY,
        spaceAfter=16,
    )

    cierre = (
        "Se extiende el presente certificado a solicitud de el/la persona "
        f"interesada para ser presentada en {EN_BLANCO}"
    )
    emision = (
        f"Emitido en {escape(junta.comuna.nombre)}, el "
        f"{_fecha_larga(fecha)}, con folio {solicitud.folio}."
    )

    elementos = []
    elementos.extend(_logo_chile())
    elementos.append(Paragraph(TITULOS.get(clave, TITULOS["residencia"]), titulo))
    elementos.append(Paragraph(_cuerpo(clave, usuario, junta), cuerpo))
    elementos.append(Paragraph(cierre, cuerpo))
    elementos.append(Paragraph(emision, cuerpo))
    elementos.append(Spacer(1, 1 * cm))
    elementos.append(
        BloqueFirma(_ruta_imagen("firma_directiva.png"), junta.nombre)
    )

    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=3 * cm,
        rightMargin=3 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title=TITULOS.get(clave, TITULOS["residencia"]).title(),
        author=junta.nombre,
    )
    documento.build(elementos)
    return buffer.getvalue()
