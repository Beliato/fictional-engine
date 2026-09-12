"""Orquestador del marco: ejecuta el procedimiento de la Tabla 9.

Uso:
    python -m src.procedimiento.orquestador --config config.yaml

Garantías:
    - Verifica el entorno (PYTHONHASHSEED, coherencia de semillas) antes de
      empezar: una corrida que no se puede repetir no sirve como prueba de
      cumplimiento.
    - Fija la semilla global una sola vez, al inicio.
    - Resuelve primero las precondiciones (datos y modelo sellado) y solo
      después ejecuta los 6 pasos del procedimiento, en orden fijo,
      propagando un `ContextoEjecucion` inmutable.
    - Aunque el veredicto de equidad del paso 4 no apruebe, el pipeline
      continúa: un veredicto negativo es evidencia válida, no un error.
    - Devuelve código de salida 0 si el pipeline completó con el veredicto de
      equidad aprobado y los nueve requerimientos cubiertos; 2 si completó
      pero hay hallazgos (la equidad no aprueba, no es evaluable, o falta
      evidencia); 1 si hubo un error de ejecución.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from src.comun.configuracion import cargar_configuracion, verificar_coherencia_semillas
from src.comun.semillas import fijar_semilla_global, verificar_pythonhashseed
from src.procedimiento.pasos import PASOS, PRECONDICIONES, nuevo_contexto


@dataclass(frozen=True)
class ResultadoEjecucion:
    """Resultado global de una corrida del marco."""

    id_ejecucion: str
    completado: bool
    equidad_aprueba: bool | None
    requerimientos_cubiertos: bool | None
    ruta_manifiesto: Path | None
    codigo_salida: int


def _id_por_defecto(marca_inicio: str) -> str:
    """Identificador legible derivado de la marca de inicio de la corrida."""
    return "corrida-" + marca_inicio.replace("-", "").replace(":", "")[:15] + "Z"


def ejecutar_marco(
    ruta_config: str | Path = "config.yaml", id_ejecucion: str | None = None
) -> ResultadoEjecucion:
    """Ejecuta las precondiciones y los 6 pasos del procedimiento.

    Args:
        ruta_config: ruta a `config.yaml`.
        id_ejecucion: identificador de la corrida; si es None se deriva de la
            marca de inicio.

    Returns:
        `ResultadoEjecucion` con el veredicto y la ruta del manifiesto.

    No captura excepciones: un fallo de precondición o de paso es un error de
    ejecución, no un hallazgo de cumplimiento, y debe verse completo. El CLI
    es el que lo traduce a código de salida 1.
    """
    config = cargar_configuracion(ruta_config)
    verificar_pythonhashseed(config.pythonhashseed)
    verificar_coherencia_semillas(config)
    fijar_semilla_global(config.semilla)

    ctx = nuevo_contexto(config, id_ejecucion or "pendiente")
    if id_ejecucion is None:
        ctx = replace(ctx, id_ejecucion=_id_por_defecto(ctx.marca_inicio))

    for precondicion in PRECONDICIONES:
        ctx = precondicion(ctx)
    for paso in PASOS:
        ctx = paso(ctx)

    aprueba = ctx.veredicto_equidad.aprueba if ctx.veredicto_equidad else None
    cubiertos = (
        all(c.cubierto for c in ctx.cobertura_requerimientos)
        if ctx.cobertura_requerimientos
        else None
    )
    return ResultadoEjecucion(
        id_ejecucion=ctx.id_ejecucion,
        completado=True,
        equidad_aprueba=aprueba,
        requerimientos_cubiertos=cubiertos,
        ruta_manifiesto=ctx.artefactos.get("manifiesto"),
        codigo_salida=0 if (aprueba and cubiertos) else 2,
    )


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config.yaml",
        type=Path,
        help="Ruta al archivo de configuración (por defecto: config.yaml)",
    )
    parser.add_argument(
        "--id",
        dest="id_ejecucion",
        default=None,
        help="Identificador de la corrida (por defecto: derivado de la fecha)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI: ejecuta el marco e imprime un resumen."""
    args = _construir_parser().parse_args(argv)
    try:
        resultado = ejecutar_marco(args.config, args.id_ejecucion)
    except Exception as exc:  # noqa: BLE001 - se reporta y se traduce a 1
        print(f"ERROR de ejecución: {type(exc).__name__}: {exc}")
        return 1

    print(f"Ejecución: {resultado.id_ejecucion}")
    estado = "aprueba" if resultado.equidad_aprueba else "no aprueba"
    print(f"Equidad: {estado}")
    cubiertos = resultado.requerimientos_cubiertos
    print(
        "Requerimientos cubiertos: "
        + ("los nueve" if cubiertos else "faltan artefactos")
    )
    print(f"Manifiesto: {resultado.ruta_manifiesto}")
    print(f"Código de salida: {resultado.codigo_salida}")
    return resultado.codigo_salida


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
