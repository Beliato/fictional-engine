"""Métricas de equidad y contraste contra umbrales PRE-DECLARADOS.

Los umbrales provienen exclusivamente de `config.equidad.umbrales` y se leen
ANTES de calcular nada. Este módulo no debe exponer ninguna forma de
"ajustar" un umbral en tiempo de ejecución.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from src.comun.configuracion import Configuracion, Subgrupo


@dataclass(frozen=True)
class ResultadoMetrica:
    """Valor observado de una métrica de equidad frente a su umbral."""

    metrica: str
    subgrupo: str
    valor_observado: float
    umbral: float
    # True si `valor_observado` respeta el umbral (interpretación depende de
    # la métrica: diferencia <= umbral, o ratio >= umbral).
    cumple: bool


@dataclass(frozen=True)
class VeredictoEquidad:
    """Veredicto agregado del principio de equidad."""

    aprueba: bool
    resultados: list[ResultadoMetrica]
    ruta_reporte: Path | None = None

    def metricas_incumplidas(self) -> list[ResultadoMetrica]:
        """Devuelve los `ResultadoMetrica` con `cumple == False`.

        TODO: filtrar `self.resultados`.
        """
        raise NotImplementedError


def calcular_metricas_equidad(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    subgrupo: "Subgrupo",
    config: "Configuracion",
) -> list[ResultadoMetrica]:
    """Calcula para un subgrupo las métricas declaradas en `config.equidad` y
    contrasta con su umbral las de `config.equidad.umbrales`.

    Las métricas posibles son las del catálogo `METRICAS_EQUIDAD` de la
    configuración. Cada actividad se evalúa contra el resto, respetando
    `config.equidad.soporte_minimo` (D42, D43).

    TODO: implementar según D42 y D43.
    """
    raise NotImplementedError


def emitir_veredicto(
    resultados_por_subgrupo: dict[str, list[ResultadoMetrica]],
    config: "Configuracion",
) -> VeredictoEquidad:
    """Combina todos los resultados en un veredicto único.

    Regla: `aprueba` es True si y solo si TODOS los `ResultadoMetrica`
    cumplen su umbral. No hay ponderaciones ni excepciones silenciosas.

    TODO: aplanar, evaluar el AND, construir el `VeredictoEquidad`.
    """
    raise NotImplementedError
