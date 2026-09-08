"""Atribución local: por qué el modelo produjo una salida concreta.

Genera, para cada inferencia, los valores SHAP de sus características y los
persiste como artefacto referenciable desde la bitácora de trazabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd
    import shap

    from src.comun.configuracion import Configuracion


@dataclass(frozen=True)
class ExplicacionLocal:
    """Atribución SHAP de una única inferencia."""

    id_evento: str
    clase_predicha: str
    valor_base: float
    contribuciones: dict[str, float]  # característica -> valor SHAP
    ruta_artefacto: Path

    def caracteristicas_top(self, k: int = 5) -> list[tuple[str, float]]:
        """Devuelve las `k` características de mayor contribución absoluta.

        TODO: ordenar `contribuciones` por |valor| descendente.
        """
        raise NotImplementedError


def construir_explainer(
    modelo: object, X_fondo: "pd.DataFrame", config: "Configuracion"
) -> "shap.Explainer":
    """Crea el `shap.Explainer` apropiado (TreeExplainer para el bosque).

    Args:
        modelo: estimador ya entrenado.
        X_fondo: datos de fondo/background para el explainer.
        config: usa `config.explicabilidad.explainer` y `config.semilla`.

    TODO: instanciar `shap.TreeExplainer(modelo, data=X_fondo,
        feature_perturbation=...)` de forma determinista.
    """
    raise NotImplementedError


def explicar_inferencia(
    explainer: "shap.Explainer",
    fila: "pd.Series",
    id_evento: str,
    config: "Configuracion",
) -> ExplicacionLocal:
    """Calcula la atribución SHAP de una fila y guarda el artefacto.

    El artefacto se escribe en
    `config.rutas.artefactos/explicaciones/local/{id_evento}.json` y su ruta
    se devuelve en `ExplicacionLocal.ruta_artefacto` para enlazarla desde la
    bitácora.

    TODO: calcular valores SHAP, serializar de forma determinista, devolver
        el objeto.
    """
    raise NotImplementedError


def explicar_lote(
    explainer: "shap.Explainer",
    X: "pd.DataFrame",
    ids_evento: "list[str]",
    config: "Configuracion",
) -> list[ExplicacionLocal]:
    """Versión por lotes de `explicar_inferencia`, preservando el orden.

    TODO: vectorizar el cálculo SHAP sobre `X` y desglosar por fila.
    """
    raise NotImplementedError
