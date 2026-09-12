"""Traducción de atribuciones a lenguaje llano (R3.3).

La Tabla 6 describe esta prueba como la "conversión de las atribuciones
dominantes en enunciados descriptivos sobre los sensores y periodos que
motivaron la inferencia". Es lo que convierte un vector SHAP en algo que un
cuidador puede leer y, llegado el caso, impugnar (ENIA, pp. 31-32).

Los enunciados se construyen a partir de la convención de nombres de
características de `src.comun.datos` (`conteo_<zona>`, `temp_<sensor>`...).
Esa convención es del marco y no de un dataset, así que vale para cualquier
sistema que entre por el contrato de ingesta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.explicabilidad.atribucion_local import ExplicacionLocal

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def formatear_decimal(valor: float, decimales: int = 3) -> str:
    """Número con coma decimal, como se lee en el reporte."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def formatear_miles(valor: int) -> str:
    """Entero con punto de miles: 11.175."""
    return f"{int(valor):,}".replace(",", ".")


def formatear_porcentaje(probabilidad: float) -> str:
    """Probabilidad como porcentaje entero: 0,82 -> «82 %»."""
    return f"{round(probabilidad * 100)} %"


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _duracion(segundos: float) -> str:
    s = int(round(segundos))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        minutos, resto = divmod(s, 60)
        return f"{minutos} min" + (f" {resto} s" if resto else "")
    horas, resto = divmod(s, 3600)
    minutos = resto // 60
    return f"{horas} h" + (f" {minutos} min" if minutos else "")


def etiqueta_caracteristica(
    nombre: str, nombres_zona: "dict[str, str] | None" = None
) -> str:
    """Nombre corto y legible de una característica, para ejes y tablas.

    `nombres_zona` traduce el identificador de zona al idioma de las personas
    destinatarias (`config.datos.nombres_zona`). Una zona sin traducción se
    muestra con su identificador: es preferible a ocultar que falta.
    """
    if nombre.startswith("conteo_"):
        zona = nombre.removeprefix("conteo_")
        return f"Movimiento en {(nombres_zona or {}).get(zona, zona)}"
    if nombre.startswith("temp_"):
        return f"Temperatura {nombre.removeprefix('temp_')}"
    return {
        "eventos_puerta": "Eventos de puerta",
        "hora_del_dia": "Hora del día",
        "dia_semana": "Día de la semana",
        "duracion_segundos": "Duración de la ventana",
    }.get(nombre, nombre)


def describir_caracteristica(
    nombre: str, valor: float, nombres_zona: "dict[str, str] | None" = None
) -> str:
    """Frase que describe el valor observado de una característica."""
    if nombre.startswith("conteo_"):
        zona = nombre.removeprefix("conteo_")
        zona = (nombres_zona or {}).get(zona, zona)
        n = int(round(valor))
        return f"{_plural(n, 'activación', 'activaciones')} de movimiento en {zona}"
    if nombre.startswith("temp_"):
        return (
            f"una temperatura de {formatear_decimal(valor, 1)} °C en el sensor "
            f"{nombre.removeprefix('temp_')}"
        )
    if nombre == "eventos_puerta":
        return f"{_plural(int(round(valor)), 'evento', 'eventos')} de puerta"
    if nombre == "hora_del_dia":
        return f"la hora del día ({int(round(valor))} h)"
    if nombre == "dia_semana":
        dia = int(round(valor))
        return f"el día de la semana ({DIAS[dia] if 0 <= dia < 7 else dia})"
    if nombre == "duracion_segundos":
        return f"una ventana de {_duracion(valor)}"
    return f"{nombre} = {valor:g}"


def formatear_valor(nombre: str, valor: float) -> str:
    """Valor observado de una característica, en sus unidades, para tablas.

    La tabla del reporte tiene que decir lo mismo que el enunciado: si la
    frase dice «jueves», la columna no puede decir «3».
    """
    if nombre.startswith("temp_"):
        return f"{formatear_decimal(valor, 1)} °C"
    if nombre == "hora_del_dia":
        return f"{int(round(valor))} h"
    if nombre == "dia_semana":
        dia = int(round(valor))
        return DIAS[dia] if 0 <= dia < 7 else str(dia)
    if nombre == "duracion_segundos":
        return _duracion(valor)
    if float(valor).is_integer():
        return str(int(valor))
    return formatear_decimal(valor, 1)


def _enumerar(partes: list[str]) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def redactar_explicacion(
    explicacion: "ExplicacionLocal", config: "Configuracion"
) -> str:
    """Enunciado en lenguaje llano de por qué se infirió la clase (R3.3).

    Toma las `config.explicabilidad.caracteristicas_destacadas` de mayor
    contribución absoluta y las agrupa por sentido: lo que empujó hacia la
    clase inferida y lo que empujó en contra. La confianza que menciona es la
    que reconstruye la propia atribución, que por aditividad es la que
    registró la bitácora.
    """
    k = config.explicabilidad.caracteristicas_destacadas
    destacadas = explicacion.caracteristicas_top(k)
    nombres_zona = config.datos.nombres_zona
    a_favor = [
        describir_caracteristica(n, explicacion.valores[n], nombres_zona)
        for n, c in destacadas
        if c > 0
    ]
    en_contra = [
        describir_caracteristica(n, explicacion.valores[n], nombres_zona)
        for n, c in destacadas
        if c < 0
    ]

    frases = [
        f"El sistema infirió «{explicacion.clase_predicha}» con una confianza "
        f"del {formatear_porcentaje(explicacion.salida_explicada)}."
    ]
    if a_favor:
        frases.append(f"Pesó a favor: {_enumerar(a_favor)}.")
    if en_contra:
        frases.append(f"Pesó en contra: {_enumerar(en_contra)}.")
    if not a_favor and not en_contra:
        frases.append("Ninguna característica tuvo un efecto apreciable.")
    return " ".join(frases)
