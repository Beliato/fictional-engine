"""Consolidación del reporte de explicabilidad (Principio 1).

Reúne en un solo artefacto la evidencia de los tres requerimientos del
principio: la explicación local de cada predicción (R3.1), la importancia
global (R3.2) y los enunciados en lenguaje llano (R3.3), a partir de la
plantilla `plantillas/reporte_explicabilidad.md`.

El reporte no lleva marcas de tiempo ni nada que varíe entre corridas
equivalentes: dos ejecuciones con la misma configuración producen el mismo
archivo, byte a byte.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

import numpy as np
import shap

from src.comun.utilidades import asegurar_directorio, rellenar_plantilla
from src.explicabilidad.lenguaje import (
    etiqueta_caracteristica,
    formatear_decimal,
    formatear_miles,
    formatear_porcentaje,
    formatear_valor,
    redactar_explicacion,
)

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.explicabilidad.atribucion_global import ExplicacionGlobal
    from src.explicabilidad.atribucion_local import ExplicacionLocal

_PLANTILLA = "reporte_explicabilidad.md"

_NOTAS = """\
- **Aditividad.** En cada explicación, el valor base más la suma de las
  contribuciones reproduce exactamente la probabilidad que el modelo asignó a
  la clase predicha. El marco lo comprueba para cada inferencia antes de
  guardarla: una explicación que no suma no corresponde a la inferencia que
  dice explicar.
- **Qué se atribuye.** Las contribuciones son a la probabilidad de la **clase
  predicha** de cada inferencia. La importancia global agrega inferencias de
  clases distintas: indica qué características mueven las decisiones en
  general, no qué caracteriza a una actividad concreta.
- **Sentido de una contribución.** "A favor" significa que el valor observado
  empujó la probabilidad de la clase inferida por encima del valor base; no
  significa que ese valor "sea" la actividad. Un conteo bajo puede pesar a
  favor: poca actividad en el dormitorio aumenta la probabilidad de estar
  cocinando. Antes de un despliegue conviene validar esta redacción con las
  personas destinatarias, que es donde una explicación correcta puede leerse
  al revés.
- **Método.** La perturbación `tree_path_dependent` simula la ausencia de una
  característica siguiendo la cobertura de los árboles. Con características
  correlacionadas puede repartir el crédito de forma distinta que un método
  intervencional (Lundberg et al., 2020). Se eligió por determinismo y costo,
  y porque no exige justificar un conjunto de fondo.
- **Alcance.** Se explican todas las inferencias del conjunto de evaluación.
  El documento exige explicar "toda predicción relevante" sin definir el
  término; en el piloto se consideran relevantes todas.
- **Nombres de zona.** Provienen del mapeo `datos.zonas` de la configuración.
  Si están en un idioma distinto al de las personas destinatarias, conviene
  traducirlos antes de un despliegue."""


def seleccionar_ejemplos(
    explicaciones: "list[ExplicacionLocal]",
    y_real: Mapping[str, str],
    config: "Configuracion",
) -> "tuple[list[ExplicacionLocal], list[ExplicacionLocal]]":
    """Elige `ejemplos_por_tipo` aciertos y otros tantos errores.

    La selección es determinista con la semilla del marco y conserva el orden
    original. Si hay menos que los pedidos, se devuelven todos los que haya.
    """
    n = config.explicabilidad.ejemplos_por_tipo
    aciertos = [e for e in explicaciones if y_real[e.id_evento] == e.clase_predicha]
    errores = [e for e in explicaciones if y_real[e.id_evento] != e.clase_predicha]
    rng = np.random.default_rng(config.semilla)

    def elegir(candidatas: "list[ExplicacionLocal]") -> "list[ExplicacionLocal]":
        if len(candidatas) <= n:
            return list(candidatas)
        indices = np.sort(rng.choice(len(candidatas), size=n, replace=False))
        return [candidatas[i] for i in indices]

    return elegir(aciertos), elegir(errores)


def generar_reporte_explicabilidad(
    global_: "ExplicacionGlobal",
    aciertos: "list[ExplicacionLocal]",
    errores: "list[ExplicacionLocal]",
    y_real: Mapping[str, str],
    id_ejecucion: str,
    config: "Configuracion",
) -> Path:
    """Rellena la plantilla y escribe el reporte en
    `config.rutas.reporte_explicabilidad`.

    Returns:
        Ruta del reporte escrito.

    Raises:
        PlantillaIncompleta: si la plantilla declara un marcador sin valor, o
            se le pasa uno que no declara.
    """
    plantilla = (Path(config.rutas.plantillas) / _PLANTILLA).read_text(
        encoding="utf-8"
    )
    destino = Path(config.rutas.reporte_explicabilidad)
    asegurar_directorio(destino.parent)

    valores = {
        "id_ejecucion": id_ejecucion,
        "explainer": config.explicabilidad.explainer,
        "version_shap": shap.__version__,
        "perturbacion": config.explicabilidad.perturbacion,
        "n_explicaciones": formatear_miles(global_.n_explicaciones),
        "muestras_graficos": formatear_miles(config.explicabilidad.muestras_graficos),
        "semilla": str(config.semilla),
        "ejemplos_por_tipo": str(config.explicabilidad.ejemplos_por_tipo),
        "ruta_figura_resumen": _relativa(global_.ruta_figura_resumen, destino),
        "tabla_importancia_global": _tabla_importancia(global_),
        "figuras_dependencia": _figuras_dependencia(global_, destino),
        "ejemplos_locales": _ejemplos(aciertos, errores, y_real, config),
        "notas_interpretacion": _NOTAS,
    }
    texto = rellenar_plantilla(plantilla, valores)
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return destino


def _relativa(ruta: Path, reporte: Path) -> str:
    """Ruta de `ruta` vista desde el directorio del reporte, en POSIX."""
    return Path(os.path.relpath(ruta, reporte.parent)).as_posix()


def _con_signo(valor: float) -> str:
    return ("+" if valor > 0 else "") + formatear_decimal(valor)


def _tabla_importancia(global_: "ExplicacionGlobal") -> str:
    filas = [
        "| # | Característica | Nombre técnico | Contribución media absoluta |",
        "|---:|---|---|---:|",
    ]
    for i, (nombre, valor) in enumerate(global_.importancia_media_abs.items(), 1):
        filas.append(
            f"| {i} | {etiqueta_caracteristica(nombre)} | `{nombre}` | "
            f"{formatear_decimal(valor, 4)} |"
        )
    return "\n".join(filas)


def _figuras_dependencia(global_: "ExplicacionGlobal", destino: Path) -> str:
    if not global_.rutas_dependencias:
        return "_Sin características destacadas._"
    return "\n\n".join(
        f"![Dependencia de {etiqueta_caracteristica(nombre)}]"
        f"({_relativa(ruta, destino)})"
        for nombre, ruta in global_.rutas_dependencias.items()
    )


def _ejemplo(
    explicacion: "ExplicacionLocal", real: str, config: "Configuracion"
) -> str:
    k = config.explicabilidad.caracteristicas_destacadas
    lineas = [
        f"#### `{explicacion.id_evento}` — real «{real}», inferida "
        f"«{explicacion.clase_predicha}» "
        f"({formatear_porcentaje(explicacion.salida_explicada)})",
        "",
        f"> {redactar_explicacion(explicacion, config)}",
        "",
        "| Característica | Valor observado | Contribución |",
        "|---|---:|---:|",
    ]
    for nombre, contribucion in explicacion.caracteristicas_top(k):
        lineas.append(
            f"| {etiqueta_caracteristica(nombre)} | "
            f"{formatear_valor(nombre, explicacion.valores[nombre])} | "
            f"{_con_signo(contribucion)} |"
        )
    return "\n".join(lineas)


def _ejemplos(
    aciertos: "list[ExplicacionLocal]",
    errores: "list[ExplicacionLocal]",
    y_real: Mapping[str, str],
    config: "Configuracion",
) -> str:
    bloques = ["### Aciertos", ""]
    if aciertos:
        bloques.append(
            "\n\n".join(_ejemplo(e, y_real[e.id_evento], config) for e in aciertos)
        )
    else:
        bloques.append("_No hubo aciertos en el conjunto de evaluación._")
    bloques += ["", "### Errores", ""]
    if errores:
        bloques.append(
            "\n\n".join(_ejemplo(e, y_real[e.id_evento], config) for e in errores)
        )
    else:
        bloques.append("_No hubo errores en el conjunto de evaluación._")
    return "\n".join(bloques)
