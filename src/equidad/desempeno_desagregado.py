"""Desempeño del modelo desagregado por subgrupo.

No emite veredicto: solo calcula y tabula métricas de desempeño estándar
(accuracy, precision, recall, F1, tasa de selección, matriz de confusión)
por cada categoría de cada subgrupo definido en la configuración.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from src.comun.configuracion import Configuracion, Subgrupo


@dataclass(frozen=True)
class DesempenoSubgrupo:
    """Métricas de desempeño para una categoría de un subgrupo."""

    subgrupo: str
    categoria: str
    n: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    tasa_seleccion: float


def calcular_desempeno_desagregado(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    subgrupo: "Subgrupo",
    config: "Configuracion",
) -> list[DesempenoSubgrupo]:
    """Calcula las métricas por categoría para un subgrupo.

    Args:
        y_verdadero: etiquetas reales del set de prueba.
        y_predicho: predicciones del modelo.
        sensibles: DataFrame con las columnas sensibles alineado con `y_*`.
        subgrupo: definición del subgrupo (`nombre`, `columna`, `categorias`).
        config: configuración del marco.

    TODO: agrupar por `sensibles[subgrupo.columna]` y calcular métricas con
        `sklearn.metrics`; incluir categorías con n pequeño marcándolas.
    """
    raise NotImplementedError


def tabla_desempeno(
    filas: list[DesempenoSubgrupo], config: "Configuracion"
) -> Path:
    """Escribe la tabla de desempeño desagregado como CSV determinista.

    TODO: volcar a `config.rutas.artefactos/equidad/desempeno_desagregado.csv`.
    """
    raise NotImplementedError
