# Portal Vecinal · Front end (MVP, modelo TO-BE)

Front end del MVP de la plataforma para juntas de vecinos, hecho con **Django + Bootstrap 5**.
Por ahora funciona sin base de datos: usa datos de ejemplo en `portal/mock_data.py`.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python manage.py runserver
```

Abre http://127.0.0.1:8000

## Cuentas de demostración

| Rol           | RUT          | Correo               |
|---------------|--------------|----------------------|
| Vecino        | 18.765.432-7 | vecino@correo.cl     |
| Presidente JV | 12.345.678-5 | presidente@jv.cl     |
| Administrador | 11.111.111-1 | admin@municipio.cl   |

## Flujo según el modelo TO-BE

Toda solicitud queda registrada y **genera un código de seguimiento** (`SEG-xxxx`).

| Tipo de solicitud | ¿Quién interviene? | Resultado |
|-------------------|--------------------|-----------|
| **Documento** | Nadie: el sistema actualiza el seguimiento y prepara el PDF | Notificación al vecino + PDF a su correo, descargable desde el portal |
| **Espacio común** | El presidente de la junta revisa y aprueba o rechaza | Notificación al vecino (aprobada o rechazada, con comentario) |

El vecino recibe una notificación y desde ahí accede al documento o verifica su solicitud.

## Pantallas

- **Login**: RUT + correo, formato de RUT automático y validación del dígito verificador.
- **Vecino**: inicio, nueva solicitud (documento o espacio común), mis solicitudes con filtro,
  seguimiento de cada solicitud (línea de tiempo y descarga del PDF) y notificaciones.
- **Presidente JV**: resumen y revisión de solicitudes de espacio común (aprobar / rechazar con comentario).
- **Administrador**: resumen, juntas de vecinos y usuarios. En el modelo TO-BE este rol no
  interviene en el flujo de solicitudes, por lo que solo gestiona juntas y usuarios.

## Estructura

```
config/                Configuración Django
portal/views.py        Vistas, con control de acceso por rol
portal/mock_data.py    Datos de ejemplo y reglas del seguimiento (reemplazar por backend / API)
templates/             Plantillas por rol (base.html compartido)
static/css/app.css     Estilos propios sobre Bootstrap
```

## Para conectar el backend

1. Reemplazar las funciones de `mock_data.py` por modelos / consultas reales.
2. Configurar PostgreSQL en `settings.py` (hay un comentario con el ejemplo).
3. Cambiar `SESSION_ENGINE` a sesiones en base de datos y usar `django.contrib.auth`.
4. Generar el PDF y enviarlo por correo al crear una solicitud de documento
   (hoy solo se muestra un mensaje y el botón de descarga es una demo).
5. Guardar las decisiones del presidente y generar las notificaciones al vecino.
