
document.addEventListener("DOMContentLoaded", function () {
    const buscador = document.getElementById("buscarSolicitud");
    const tabla = document.getElementById("tablaSolicitudes");

    if (buscador && tabla) {
        buscador.addEventListener("input", function () {
            const texto = buscador.value
                .trim()
                .toLocaleLowerCase("es-CL");

            const filas = tabla.querySelectorAll("tbody tr");

            filas.forEach(function (fila) {
                const contenido = fila.textContent
                    .toLocaleLowerCase("es-CL");

                fila.hidden = !contenido.includes(texto);
            });
        });
    }

    const rut = document.getElementById("rut");

    if (rut) {
        rut.addEventListener("blur", function () {
            rut.value = rut.value.trim().toUpperCase();
        });
    }
});
