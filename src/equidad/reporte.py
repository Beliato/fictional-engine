"""Consolidación del reporte de equidad (Principio 2).

Reúne la evidencia de los dos requerimientos del principio —desempeño
desagregado (R4.1) y disparidad medida contra umbrales pre-declarados
(R4.2)— a partir de la plantilla `plantillas/reporte_equidad.md`.

Como el de explicabilidad, el reporte no lleva marcas de tiempo: dos
ejecuciones con la misma configuración producen el mismo archivo, byte a
byte.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.comun.configuracion import METRICAS_EQUIDAD
from src.comun.utilidades import asegurar_directorio, rellenar_plantilla
from src.explicabilidad.lenguaje import formatear_decimal, formatear_miles

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.equidad.desempeno_desagregado import DesempenoSubgrupo
    from src.equidad.metricas_equidad import (
        ResultadoMetrica,
        TasaCategoria,
        VeredictoEquidad,
    )

_PLANTILLA = "reporte_equidad.md"

ESTADOS = {
    "aprueba": "APRUEBA",
    "no_aprueba": "NO APRUEBA",
    "no_evaluable": "NO EVALUABLE",
}

# Nombre de cada métrica del catálogo: completo, para el protocolo, y
# abreviado, para las tablas de resultados.
NOMBRES_METRICA = {
    "true_positive_rate_difference": (
        "Diferencia de tasas de verdaderos positivos (igualdad de oportunidades)",
        "Dif. TVP",
    ),
    "false_positive_rate_difference": (
        "Diferencia de tasas de falsos positivos",
        "Dif. TFP",
    ),
    "equalized_odds_difference": (
        "Probabilidades igualadas (la mayor de las dos diferencias anteriores)",
        "Prob. igualadas",
    ),
    "demographic_parity_difference": (
        "Diferencia de paridad demográfica (tasas de selección)",
        "Dif. paridad",
    ),
    "selection_rate_ratio": (
        "Cociente de tasas de selección (regla del 80 %)",
        "Cociente selección",
    ),
}

_NOMBRES_TASA = {"tvp": "TVP", "tfp": "TFP", "seleccion": "Selección"}


def generar_reporte_equidad(
    desempeno: "list[DesempenoSubgrupo]",
    veredicto: "VeredictoEquidad",
    id_ejecucion: str,
    config: "Configuracion",
) -> Path:
    """Rellena la plantilla y escribe el reporte en
    `config.rutas.reporte_equidad`.

    Returns:
        Ruta del reporte escrito.

    Raises:
        PlantillaIncompleta: si la plantilla declara un marcador sin valor, o
            se le pasa uno que no declara.
    """
    plantilla = (Path(config.rutas.plantillas) / _PLANTILLA).read_text(
        encoding="utf-8"
    )
    destino = Path(config.rutas.reporte_equidad)
    asegurar_directorio(destino.parent)

    evaluables = [r for r in veredicto.que_deciden() if r.evaluable]
    valores = {
        "id_ejecucion": id_ejecucion,
        "veredicto": ESTADOS[veredicto.estado],
        "resumen_veredicto": _resumen(veredicto),
        "tabla_incumplidas": tabla_resultados(
            veredicto.metricas_incumplidas(), "_Ninguna._"
        ),
        "tabla_protocolo": tabla_protocolo(config),
        "soporte_minimo": formatear_miles(config.equidad.soporte_minimo),
        "lista_subgrupos": _lista_subgrupos(config),
        "tabla_desempeno_desagregado": tabla_desempeno(desempeno),
        "tabla_metricas_veredicto": tabla_resultados(
            evaluables, "_Ninguna combinación fue evaluable._"
        ),
        "tabla_no_evaluables": _tabla_no_evaluables(veredicto.no_evaluables()),
        "tabla_descriptivas": tabla_resultados(
            veredicto.descriptivas(), "_No se declararon métricas descriptivas._"
        ),
        "notas_interpretacion": _notas(config),
        "limitaciones": lista_limitaciones(config),
    }
    texto = rellenar_plantilla(plantilla, valores)
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return destino


def _num(valor: float | None, decimales: int = 3) -> str:
    return "—" if valor is None else formatear_decimal(valor, decimales)


def _resumen(veredicto: "VeredictoEquidad") -> str:
    evaluadas, posibles = veredicto.cobertura
    lineas = [
        "- Combinaciones que deciden el veredicto (subgrupo × actividad × "
        f"métrica): {formatear_miles(posibles)}",
        f"- Evaluadas: {formatear_miles(evaluadas)}",
        f"- No evaluables: {formatear_miles(posibles - evaluadas)}",
        f"- Incumplen su umbral: {formatear_miles(len(veredicto.metricas_incumplidas()))}",
        "",
    ]
    if veredicto.estado == "no_evaluable":
        lineas.append(
            "Ninguna combinación llegó al soporte mínimo. Un veredicto no "
            "evaluable no es un aprobado: con este conjunto de evaluación no se "
            "puede afirmar nada sobre la equidad del sistema."
        )
    elif veredicto.estado == "no_aprueba":
        lineas.append(
            "Al menos una combinación evaluable excede su umbral; el detalle "
            "está en la tabla siguiente."
        )
    else:
        lineas.append(
            "Todas las combinaciones evaluables respetan su umbral. Las no "
            "evaluables no cuentan como aprobadas: el veredicto vale solo para "
            "lo que se pudo medir."
        )
    return "\n".join(lineas)


def tabla_protocolo(config: "Configuracion") -> str:
    """Métricas declaradas, su papel y su umbral.

    La comparten el protocolo del paso 3 y este reporte: si divergieran, el
    expediente afirmaría dos protocolos distintos para la misma corrida.
    """
    filas = [
        "| Métrica | Nombre técnico | Papel | Umbral | Cumple si |",
        "|---|---|---|---:|---|",
    ]
    for metrica, umbral in config.equidad.umbrales.items():
        condicion = (
            "valor ≤ umbral"
            if METRICAS_EQUIDAD[metrica] == "diferencia"
            else "valor ≥ umbral"
        )
        filas.append(
            f"| {NOMBRES_METRICA[metrica][0]} | `{metrica}` | decide | "
            f"{formatear_decimal(umbral, 2)} | {condicion} |"
        )
    for metrica in config.equidad.descriptivas:
        filas.append(
            f"| {NOMBRES_METRICA[metrica][0]} | `{metrica}` | describe | — | — |"
        )
    return "\n".join(filas)


def _lista_subgrupos(config: "Configuracion") -> str:
    lineas = []
    for s in config.equidad.subgrupos:
        categorias = (
            ", ".join(s.categorias) if s.categorias else "las presentes en los datos"
        )
        lineas.append(
            f"- **{s.nombre}** (columna `{s.columna}`; categorías: {categorias})."
            f" {s.justificacion}"
        )
    return "\n".join(lineas)


def tabla_desempeno(filas: "list[DesempenoSubgrupo]") -> str:
    if not filas:
        return "_Sin subgrupos que desagregar._"
    lineas = [
        "| Subgrupo | Categoría | Ventanas | Actividades | Exactitud | "
        "Precisión macro | Exhaustividad macro | F1 macro |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for f in filas:
        lineas.append(
            f"| {f.subgrupo} | {f.categoria} | {formatear_miles(f.n)} | "
            f"{f.n_actividades} | {_num(f.accuracy)} | {_num(f.precision_macro)} | "
            f"{_num(f.recall_macro)} | {_num(f.f1_macro)} |"
        )
    return "\n".join(lineas)


def _celda(t: "TasaCategoria") -> str:
    fuera = "" if t.en_comparacion else ", fuera"
    return f"{t.categoria} {_num(t.valor)} ({formatear_miles(t.denominador)}{fuera})"


def _detalle_tasas(resultado: "ResultadoMetrica") -> str:
    grupos: dict[str, list[TasaCategoria]] = {}
    for t in resultado.tasas:
        grupos.setdefault(t.tasa, []).append(t)
    return "; ".join(
        f"{_NOMBRES_TASA[tasa]}: " + " · ".join(_celda(t) for t in tasas)
        for tasa, tasas in grupos.items()
    )


def tabla_resultados(resultados: "list[ResultadoMetrica]", vacia: str) -> str:
    if not resultados:
        return vacia
    filas = [
        "| Subgrupo | Actividad | Métrica | Valor | Umbral | Estado | "
        "Tasas por categoría (denominador) |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for r in resultados:
        filas.append(
            f"| {r.subgrupo} | {r.actividad} | {NOMBRES_METRICA[r.metrica][1]} | "
            f"{_num(r.valor_observado)} | {_num(r.umbral, 2)} | {r.estado} | "
            f"{_detalle_tasas(r)} |"
        )
    return "\n".join(filas)


def _tabla_no_evaluables(resultados: "list[ResultadoMetrica]") -> str:
    if not resultados:
        return "_Ninguna: todas las combinaciones que deciden fueron evaluables._"
    filas = [
        "| Subgrupo | Actividad | Métrica | Motivo | "
        "Tasas por categoría (denominador) |",
        "|---|---|---|---|---|",
    ]
    for r in resultados:
        filas.append(
            f"| {r.subgrupo} | {r.actividad} | {NOMBRES_METRICA[r.metrica][1]} | "
            f"{r.motivo} | {_detalle_tasas(r)} |"
        )
    return "\n".join(filas)


def _notas(config: "Configuracion") -> str:
    soporte = formatear_miles(config.equidad.soporte_minimo)
    return "\n".join(
        [
            "- **Qué pregunta cada tasa.** La TVP: de las veces que la actividad "
            "ocurrió, ¿el sistema la reconoce igual en todas las categorías? La "
            "TFP: de las veces que no ocurrió, ¿la anuncia por error con la misma "
            "frecuencia? Las dos condicionan en la actividad real, así que no "
            "castigan que una actividad sea más frecuente en unas categorías que "
            "en otras.",
            "- **Paridad demográfica.** Compara cuánto se predice cada actividad "
            "sin mirar la real. Si las actividades ocurren con frecuencias "
            "distintas en cada categoría, un sistema perfecto la incumple; por "
            "eso puede declararse descriptiva (D42).",
            "- **No evaluable no es aprobado.** Una combinación sin soporte "
            "suficiente no dice nada sobre la equidad del sistema: el veredicto "
            "vale solo para las combinaciones evaluadas.",
            "- **Incertidumbre.** Una tasa sobre pocos casos es inestable. Con "
            f"denominadores cercanos al soporte mínimo ({soporte}), una "
            "diferencia del tamaño del umbral puede deberse al azar: léase cada "
            "diferencia junto a los denominadores de sus tasas.",
            "- **Contraste exacto.** Las diferencias se comparan con el umbral en "
            "aritmética exacta; una diferencia igual al umbral lo cumple.",
            "- **Desempeño macro.** Precisión, exhaustividad y F1 se promedian "
            "sobre las actividades presentes en las etiquetas reales de cada "
            "categoría; una actividad que ocurre y nunca se predice aporta cero.",
        ]
    )


def lista_limitaciones(config: "Configuracion") -> str:
    """Limitaciones declaradas en la configuración, como viñetas."""
    if not config.equidad.limitaciones:
        return "_La configuración no declara limitaciones._"
    return "\n".join(f"- {texto}" for texto in config.equidad.limitaciones)
