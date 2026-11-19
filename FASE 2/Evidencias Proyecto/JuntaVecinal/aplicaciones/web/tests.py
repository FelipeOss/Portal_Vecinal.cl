import shutil
import tempfile
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import (
    Comuna,
    Hogar,
    JuntaVecinal,
    Solicitud,
    TipoDocumento,
    TipoSolicitud,
    TipoUsuario,
    Usuario,
)
from .services import (
    TIPO_MANUAL,
    crear_solicitud_documento,
    crear_solicitud_revision,
    resolver_solicitud,
)

MEDIA_PRUEBAS = tempfile.mkdtemp()


@override_settings(
    MEDIA_ROOT=MEDIA_PRUEBAS,
    MAILERS={
        "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}
    },
)
class DescargaCertificadoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        comuna = Comuna.objects.create(
            nombre="Macul", direccion_municipalidad="Los Plátanos 3130"
        )
        junta = JuntaVecinal.objects.create(
            nombre="JV Pruebas", direccion="Calle Uno 123", comuna=comuna
        )
        hogar = Hogar.objects.create(direccion="Calle Uno 123", junta_vecinal=junta)
        tipo_vecino = TipoUsuario.objects.create(nombre="Vecino")
        cls.tipos_documento = {}
        for nombre in (
            "Certificado de residencia",
            "Certificado de afiliación",
            "Certificado de antigüedad",
            TIPO_MANUAL,
        ):
            cls.tipos_documento[nombre] = TipoDocumento.objects.create(nombre=nombre)
            TipoSolicitud.objects.create(nombre=nombre)
        cls.tipo_documento = cls.tipos_documento["Certificado de residencia"]

        cls.vecino = Usuario.objects.create_user(
            username="111111111",
            rut="111111111",
            email="vecino@test.cl",
            password="demo1234",
            first_name="Ana",
            last_name="Paz",
            tipo_usuario=tipo_vecino,
            hogar=hogar,
        )
        cls.otro_vecino = Usuario.objects.create_user(
            username="222222222",
            rut="222222222",
            email="otro@test.cl",
            password="demo1234",
            first_name="Luis",
            last_name="Soto",
            tipo_usuario=tipo_vecino,
            hogar=hogar,
        )

        tipo_presidente = TipoUsuario.objects.create(nombre="Presidente")
        cls.presidente = Usuario.objects.create_user(
            username="333333333",
            rut="333333333",
            email="presidente@test.cl",
            password="demo1234",
            first_name="Paula",
            last_name="Presi",
            tipo_usuario=tipo_presidente,
            hogar=hogar,
        )

        otra_junta = JuntaVecinal.objects.create(
            nombre="JV Otra", direccion="Calle Dos 456", comuna=comuna
        )
        otro_hogar = Hogar.objects.create(
            direccion="Calle Dos 456", junta_vecinal=otra_junta
        )
        cls.presidente_ajeno = Usuario.objects.create_user(
            username="444444444",
            rut="444444444",
            email="presidente2@test.cl",
            password="demo1234",
            first_name="Rosa",
            last_name="Ajena",
            tipo_usuario=tipo_presidente,
            hogar=otro_hogar,
        )

    def _crear_solicitud(self):
        return crear_solicitud_documento(
            self.vecino, self.tipo_documento, "Trámite bancario"
        )

    def _url_descarga(self, solicitud):
        return reverse("vecino_solicitud_pdf", args=[solicitud.pk])

    def test_descarga_documento_propio(self):
        solicitud, documento = self._crear_solicitud()
        self.client.force_login(self.vecino)

        respuesta = self.client.get(self._url_descarga(solicitud))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn("attachment", respuesta["Content-Disposition"])
        self.assertIn("Certificado", respuesta["Content-Disposition"])
        self.assertTrue(documento.archivo.name.endswith(".pdf"))

    def test_descarga_documento_ajeno_da_404(self):
        solicitud, _ = self._crear_solicitud()
        self.client.force_login(self.otro_vecino)

        respuesta = self.client.get(self._url_descarga(solicitud))

        self.assertEqual(respuesta.status_code, 404)

    def test_descarga_sin_sesion_redirige_al_login(self):
        solicitud, _ = self._crear_solicitud()

        respuesta = self.client.get(self._url_descarga(solicitud))

        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/login/", respuesta["Location"])

    def test_post_genera_solicitud_lista_y_descarga(self):
        self.client.force_login(self.vecino)

        respuesta = self.client.post(
            reverse("vecino_solicitar"),
            {"tipo": self.tipo_documento.pk, "motivo": "Trámite bancario"},
        )

        solicitud = Solicitud.objects.get(solicitante=self.vecino)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(solicitud.estado, "listo")
        self.assertTrue(solicitud.folio.startswith("SOL-"))
        self.assertEqual(solicitud.documentos.count(), 1)
        self.assertIn("/vecino/solicitudes/", respuesta["Location"])
        self.assertIn(f"descargar={solicitud.pk}", respuesta["Location"])

        listado = self.client.get(respuesta["Location"])
        self.assertEqual(listado.status_code, 200)
        self.assertContains(listado, "<iframe")
        self.assertContains(listado, f"/vecino/solicitudes/{solicitud.pk}/pdf/")

        self.assertEqual(len(mail.outbox), 1)
        enviado = mail.outbox[0]
        self.assertIn(solicitud.folio, enviado.subject)
        self.assertEqual(enviado.to, [self.vecino.email])
        self.assertEqual(len(enviado.attachments), 1)
        nombre, contenido, tipo = enviado.attachments[0]
        self.assertTrue(nombre.endswith(".pdf"))
        self.assertEqual(tipo, "application/pdf")
        self.assertTrue(contenido.startswith(b"%PDF"))

    def test_fallo_de_correo_no_pierde_la_solicitud(self):
        self.client.force_login(self.vecino)

        with patch(
            "aplicaciones.web.views.enviar_certificado_por_email",
            side_effect=RuntimeError("smtp caido"),
        ):
            respuesta = self.client.post(
                reverse("vecino_solicitar"),
                {"tipo": self.tipo_documento.pk, "motivo": "Trámite bancario"},
            )

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Solicitud.objects.filter(solicitante=self.vecino).exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_login_no_expone_cuentas_demo(self):
        respuesta = self.client.get(reverse("login"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "Cuentas de demostración")
        self.assertNotContains(respuesta, "camila.rojas@example.cl")

    def test_detalle_muestra_los_tres_pasos_completos(self):
        solicitud, _ = self._crear_solicitud()
        self.client.force_login(self.vecino)

        respuesta = self.client.get(
            reverse("vecino_solicitud_detalle", args=[solicitud.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Solicitud registrada")
        self.assertContains(respuesta, "Seguimiento")
        self.assertContains(respuesta, "Documento listo")
        self.assertEqual(respuesta.content.decode().count('class="hecho"'), 3)

    def test_genera_los_tres_certificados(self):
        for nombre, tipo in self.tipos_documento.items():
            solicitud, documento = crear_solicitud_documento(
                self.vecino, tipo, "Trámite de prueba"
            )
            self.assertEqual(solicitud.estado, "listo")
            documento.archivo.open("rb")
            inicio = documento.archivo.read(4)
            documento.archivo.close()
            self.assertEqual(inicio, b"%PDF", f"PDF inválido para {nombre}")

    def test_motivo_vacio_no_crea_solicitud(self):
        self.client.force_login(self.vecino)

        respuesta = self.client.post(
            reverse("vecino_solicitar"),
            {"tipo": self.tipo_documento.pk, "motivo": "   "},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Solicitud.objects.filter(solicitante=self.vecino).exists())

    def test_solicitud_manual_queda_pendiente_y_notifica(self):
        self.client.force_login(self.vecino)

        respuesta = self.client.post(
            reverse("vecino_solicitar"),
            {
                "tipo": self.tipos_documento[TIPO_MANUAL].pk,
                "motivo": "Trámite municipal",
            },
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], reverse("vecino_solicitudes"))
        solicitud = Solicitud.objects.get(solicitante=self.vecino)
        self.assertEqual(solicitud.estado, "pendiente")
        self.assertFalse(solicitud.documentos.exists())
        self.assertEqual(self.vecino.notificaciones.count(), 1)
        self.assertEqual(self.presidente.notificaciones.count(), 1)
        self.assertEqual(len(mail.outbox), 2)
        for correo in mail.outbox:
            self.assertEqual(correo.attachments, [])

    def test_presidente_aprueba_y_envia_pdf(self):
        solicitud = crear_solicitud_revision(
            self.vecino, self.tipos_documento[TIPO_MANUAL], "Trámite"
        )
        self.client.force_login(self.presidente)

        respuesta = self.client.post(
            reverse("presidente_resolver", args=[solicitud.pk]),
            {"accion": "aprobar"},
        )

        self.assertEqual(respuesta.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, "listo")
        self.assertEqual(solicitud.documentos.count(), 1)
        decision = mail.outbox[-1]
        self.assertEqual(len(decision.attachments), 1)
        self.assertTrue(decision.attachments[0][1].startswith(b"%PDF"))
        self.assertTrue(
            self.vecino.notificaciones.filter(texto__icontains="aprobada").exists()
        )

    def test_presidente_rechaza_con_comentario(self):
        solicitud = crear_solicitud_revision(
            self.vecino, self.tipos_documento[TIPO_MANUAL], "Trámite"
        )
        self.client.force_login(self.presidente)

        respuesta = self.client.post(
            reverse("presidente_resolver", args=[solicitud.pk]),
            {"accion": "rechazar", "comentario": "Falta acreditar domicilio"},
        )

        self.assertEqual(respuesta.status_code, 302)
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, "rechazada")
        self.assertFalse(solicitud.documentos.exists())
        self.assertEqual(mail.outbox[-1].attachments, [])
        self.assertIn("Falta acreditar domicilio", mail.outbox[-1].body)

    def test_solicitud_ya_revisada_no_se_puede_cambiar(self):
        solicitud = crear_solicitud_revision(
            self.vecino, self.tipos_documento[TIPO_MANUAL], "Trámite"
        )
        resolver_solicitud(solicitud, self.presidente, True)

        with self.assertRaises(ValidationError):
            resolver_solicitud(solicitud, self.presidente, False)

        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, "listo")

    def test_presidente_ajeno_no_puede_resolver(self):
        solicitud = crear_solicitud_revision(
            self.vecino, self.tipos_documento[TIPO_MANUAL], "Trámite"
        )
        self.client.force_login(self.presidente_ajeno)

        respuesta = self.client.post(
            reverse("presidente_resolver", args=[solicitud.pk]),
            {"accion": "aprobar"},
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_notificaciones_marcan_como_leidas(self):
        solicitud = crear_solicitud_revision(
            self.vecino, self.tipos_documento[TIPO_MANUAL], "Trámite"
        )

        self.client.force_login(self.vecino)
        respuesta = self.client.get(reverse("vecino_notificaciones"))
        self.assertContains(respuesta, solicitud.folio)
        self.assertFalse(self.vecino.notificaciones.filter(leida=False).exists())

        self.client.force_login(self.presidente)
        respuesta = self.client.get(reverse("presidente_notificaciones"))
        self.assertContains(respuesta, solicitud.folio)
        self.assertFalse(self.presidente.notificaciones.filter(leida=False).exists())
