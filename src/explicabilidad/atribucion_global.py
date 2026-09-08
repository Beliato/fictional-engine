"""Atribución global: qué características impulsan al modelo en conjunto.

Agrega los valores SHAP sobre una muestra de datos
(`config.explicabilidad.muestras_globales`) para obtener importancia global
y dependencias, y produce las figuras del reporte de explicabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    import shap

    from src.comun.configuracion import Configuracion


@dataclass(frozen=True)
class ExplicacionGlobal:
    """Resumen de importancia global de características."""

    importancia_media_abs: dict[str, float]  # media |SHAP| por característica
    n_muestras: int
    ruta_figura_resumen: Path
    rutas_dependencias: dict[str, Path]


def muestrear_para_global(
    X: "pd.DataFrame", config: "Configuracion"
) -> "pd.DataFrame":
    """Toma una submuestra determinista de `X` para la atribución global.

    Usa `config.semilla` y `config.explicabilidad.muestras_globales`. Si `X`
    tiene menos filas que el objetivo, devuelve `X` completo.

    TODO: `X.sample(n=..., random_state=config.semilla)` con tope al tamaño.
    """
    raise NotImplementedError


def calcular_importancia_global(
    explainer: "shap.Explainer",
    X_muestra: "pd.DataFrame",
    config: "Configuracion",
) -> ExplicacionGlobal:
    """Calcula la importancia global agregando |SHAP| y genera las figuras.

    Figuras (PNG con `matplotlib`, tamaño y DPI fijos para reproducibilidad):
        - resumen (beeswarm o barras) -> `ruta_figura_resumen`
        - dependencia por característica top -> `rutas_dependencias`

    Los artefactos se escriben bajo
    `config.rutas.artefactos/explicaciones/global/`.

    TODO: calcular SHAP sobre `X_muestra`, agregar, dibujar, guardar.
    """
    raise NotImplementedError
