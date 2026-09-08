"""Verificación de integridad y completitud de la bitácora de inferencias.

Responde a la pregunta de auditoría: "¿el registro es confiable y está
completo?". Ejecutable de forma independiente:

    python -m src.trazabilidad.verificacion --config config.yaml
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion


@dataclass(frozen=True)
class InformeVerificacion:
    """Resultado de verificar una bitácora."""

    ruta: Path
    n_registros: int
    valido: bool
    problemas: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        """Devuelve un resumen legible del informe.

        TODO: formatear estado + lista de problemas.
        """
        raise NotImplementedError


def verificar_registro(
    ruta: str | Path, config: "Configuracion"
) -> InformeVerificacion:
    """Verifica una bitácora JSONL completa.

    Comprobaciones:
        - Toda línea es JSON válido y conforme al esquema.
        - `version_esquema` coincide con `config.trazabilidad.version_esquema`.
        - `id_evento` sin duplicados.
        - `marca_temporal` en ISO 8601 UTC y en orden no decreciente.
        - `confianza` en [0, 1].
        - `version_modelo` == `config.modelo.version` para todos los registros.
        - `referencia_explicacion` apunta a un artefacto existente (si
          `config.explicabilidad.guardar_local_por_inferencia`).
        - `responsable` no vacío ni con el texto placeholder "TODO".

    Returns:
        El `InformeVerificacion` con la lista de problemas encontrados.

    TODO: implementar las comprobaciones anteriores acumulando problemas.
    """
    raise NotImplementedError


def verificar_cobertura(
    ruta_registro: str | Path, ids_esperados: set[str], config: "Configuracion"
) -> InformeVerificacion:
    """Comprueba que hay exactamente un registro por cada inferencia esperada.

    Args:
        ruta_registro: bitácora JSONL.
        ids_esperados: `id_evento` de todas las filas del set de prueba.

    TODO: comparar el conjunto de `id_evento` registrados con `ids_esperados`
        y reportar faltantes/sobrantes.
    """
    raise NotImplementedError


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI. Devuelve 0 si la bitácora es válida, 1 si no.

    TODO: cargar config, resolver la ruta del registro, llamar a
        `verificar_registro`, imprimir `informe.resumen()`, devolver el código.
    """
    raise NotImplementedError


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
