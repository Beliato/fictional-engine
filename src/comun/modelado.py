"""Entrenamiento, sellado y persistencia del modelo de clasificación.

Se ubica en `comun/` porque es infraestructura compartida por los pasos del
procedimiento y por las pruebas. El entrenamiento es determinista: todos los
hiperparámetros y `random_state` vienen de `config.modelo`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from sklearn.base import ClassifierMixin

    from src.comun.configuracion import Configuracion


@dataclass(frozen=True)
class ModeloSellado:
    """Modelo entrenado junto con su procedencia para auditoría."""

    estimador: "ClassifierMixin"
    version: str
    hash_parametros: str        # hash de los hiperparámetros efectivos
    hash_datos_entrenamiento: str
    ruta_serializado: Path


def construir_estimador(config: "Configuracion") -> "ClassifierMixin":
    """Instancia el estimador según `config.modelo` sin entrenarlo.

    Raises:
        ConfiguracionInvalida: si `config.modelo.tipo` no está soportado.

    TODO: mapear `config.modelo.tipo` -> clase de sklearn y pasar
        `**config.modelo.hiperparametros`.
    """
    raise NotImplementedError


def entrenar(
    X_entrenamiento: "pd.DataFrame",
    y_entrenamiento: "pd.Series",
    config: "Configuracion",
) -> ModeloSellado:
    """Entrena el estimador de forma determinista y lo sella.

    TODO: construir estimador, `fit`, calcular hashes, serializar con
        `joblib`/`pickle` a `config.rutas.artefactos/modelo/` y devolver
        `ModeloSellado`.
    """
    raise NotImplementedError


def predecir_con_confianza(
    modelo: ModeloSellado, X: "pd.DataFrame"
) -> "tuple[pd.Series, pd.Series]":
    """Devuelve `(predicciones, confianza)` donde confianza es la probabilidad
    de la clase predicha (`predict_proba().max(axis=1)`).

    TODO: implementar.
    """
    raise NotImplementedError


def cargar_modelo(ruta: str | Path) -> ModeloSellado:
    """Carga un `ModeloSellado` previamente serializado.

    TODO: deserializar y reconstruir la procedencia.
    """
    raise NotImplementedError
