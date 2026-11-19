from django.db import migrations


def normalizar(apps, schema_editor):
    Usuario = apps.get_model("web", "Usuario")
    for usuario in Usuario.objects.all():
        viejo = usuario.rut or ""
        nuevo = "".join(c for c in viejo.upper() if c.isalnum())
        if not nuevo or nuevo == viejo:
            continue
        usuario.rut = nuevo
        campos = ["rut"]
        if usuario.username == viejo:
            usuario.username = nuevo
            campos.append("username")
        usuario.save(update_fields=campos)


def revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0003_alter_solicitud_estado"),
    ]

    operations = [
        migrations.RunPython(normalizar, revertir),
    ]
