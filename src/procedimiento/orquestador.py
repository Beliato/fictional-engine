"""Orquestador del marco: ejecuta el procedimiento de la Tabla 9.

Uso:
    python -m src.procedimiento.orquestador --config config.yaml

Garantías:
    - Verifica el entorno (PYTHONHASHSEED, versiones) antes de empezar.
    - Fija la semilla global una sola vez, al inicio.
    - Resuelve primero las precondiciones (datos y modelo sellado) y solo
      después ejecuta los 6 pasos del procedimiento, en orden fijo,
      propagando un `ContextoEjecucion` inmutable.
    - Aunque el veredicto de equidad del paso 4 no apruebe, el pipeline
      continúa: un veredicto negativo es evidencia válida, no un error.
    - Devuelve código de salida 0 si el pipeline completó, 2 si el veredicto
      de equidad no aprueba o no es evaluable, 1 si hubo un error de
      ejecución.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ResultadoEjecucion:
    """Resultado global de una corrida del marco."""

    id_ejecucion: str
    completado: bool
    equidad_aprueba: bool | None
    ruta_manifiesto: Path | None
    codigo_salida: int


def ejecutar_marco(ruta_config: str | Path = "config.yaml") -> ResultadoEjecucion:
    """Ejecuta las precondiciones y los 6 pasos del procedimiento.

    Args:
        ruta_config: ruta a `config.yaml`.

    Returns:
        `ResultadoEjecucion` con el veredicto y la ruta del manifiesto.

    TODO:
        1. `cargar_configuracion(ruta_config)`.
        2. `verificar_pythonhashseed` + comprobación de versiones de libs.
        3. `fijar_semilla_global(config.semilla)`.
        4. Crear `ContextoEjecucion` (id_ejecucion = UUID determinista o
           timestamp+hash de config).
        5. Recorrer `pasos.PRECONDICIONES` (datos y modelo sellado) y luego
           `pasos.PASOS`, encadenando el contexto. La separación importa: si
           una precondición falla es un error de ejecución (código 1), no un
           hallazgo de cumplimiento.
        6. Derivar `codigo_salida` del veredicto de equidad.
        7. Devolver `ResultadoEjecucion`.
    """
    raise NotImplementedError


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default="config.yaml",
        type=Path,
        help="Ruta al archivo de configuración (por defecto: config.yaml)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI.

    TODO: parsear args, llamar a `ejecutar_marco`, imprimir un resumen
        legible (pasos, veredicto, ruta del manifiesto) y devolver
        `resultado.codigo_salida`.
    """
    raise NotImplementedError


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
