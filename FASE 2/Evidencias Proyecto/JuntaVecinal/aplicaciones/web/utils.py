def normalizar_rut(valor):
    return "".join(c for c in str(valor).upper() if c.isalnum())


def formatear_rut(valor):
    limpio = normalizar_rut(valor)
    if len(limpio) < 2:
        return limpio
    cuerpo, dv = limpio[:-1], limpio[-1]
    if cuerpo.isdigit():
        cuerpo = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo}-{dv}"
