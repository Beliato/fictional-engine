"""Entrenamiento, sellado y persistencia del modelo de clasificación.

Se ubica en `comun/` porque es infraestructura compartida por los pasos del
procedimiento y por las pruebas. El entrenamiento es determinista: todos los
hiperparámetros y `random_state` vienen de `config.modelo`.

Sellado
-------
Un modelo no basta con entrenarlo: hay que poder demostrar **qué** produjo
cada decisión. `ModeloSellado` acompaña al estimador con su versión, el hash
de sus hiperparámetros efectivos, el hash de los datos con que se entrenó y
la versión de scikit-learn que lo produjo. Sin eso, el R5.3 —reconstruir una
decisión ex post— queda en promesa.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import joblib
import sklearn
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.tree import DecisionTreeClassifier

from src.comun.configuracion import ConfiguracionInvalida
from src.comun.utilidades import asegurar_directorio, hash_sha256

if TYPE_CHECKING:
    import pandas as pd
    from sklearn.base import ClassifierMixin

    from src.comun.configuracion import Configuracion

# Modelos admitidos. La lista NO es arbitraria y no puede vivir en
# `config.yaml`: es un mapeo de nombre a clase de Python.
#
# Solo hay modelos de árbol a propósito. El módulo de explicabilidad usa
# `shap.TreeExplainer` (`config.explicabilidad.explainer`), que exige esta
# familia. Admitir un modelo lineal o una red aquí dejaría el pipeline
# entrenando sin problemas y reventaría —o peor, produciría atribuciones
# inválidas— recién en el paso 4. El acoplamiento es deliberado y está
# declarado en el diseño: el modelo de referencia se elige por su
# compatibilidad con las técnicas de atribución adoptadas.
MODELOS_ADMITIDOS: dict[str, type] = {
    "RandomForestClassifier": RandomForestClassifier,
    "ExtraTreesClassifier": ExtraTreesClassifier,
    "GradientBoostingClassifier": GradientBoostingClassifier,
    "DecisionTreeClassifier": DecisionTreeClassifier,
}

_NOMBRE_SERIALIZADO = "modelo.joblib"


@dataclass(frozen=True)
class ModeloSellado:
    """Modelo entrenado junto con su procedencia para auditoría."""

    estimador: "ClassifierMixin"
    version: str
    hash_parametros: str        # hash de los hiperparámetros efectivos
    hash_datos_entrenamiento: str
    ruta_serializado: Path
    version_sklearn: str = sklearn.__version__


def construir_estimador(config: "Configuracion") -> "ClassifierMixin":
    """Instancia el estimador según `config.modelo` sin entrenarlo.

    Raises:
        ConfiguracionInvalida: si `config.modelo.tipo` no está soportado, o
            si sus hiperparámetros no son los que la clase acepta.
    """
    tipo = config.modelo.tipo
    if tipo not in MODELOS_ADMITIDOS:
        raise ConfiguracionInvalida(
            f"modelo.tipo: {tipo!r} no está admitido. Opciones: "
            f"{sorted(MODELOS_ADMITIDOS)}. Solo se admiten modelos de árbol "
            f"porque el módulo de explicabilidad usa "
            f"{config.explicabilidad.explainer}, que exige esa familia."
        )
    try:
        return MODELOS_ADMITIDOS[tipo](**config.modelo.hiperparametros)
    except TypeError as exc:
        raise ConfiguracionInvalida(
            f"modelo.hiperparametros: {tipo} no acepta esos argumentos: {exc}"
        ) from exc


def _hash_parametros(estimador: "ClassifierMixin") -> str:
    """Hash de los hiperparámetros **efectivos** del estimador.

    Se hashea `get_params()`, no el bloque del YAML: incluye los valores por
    defecto que el usuario no declaró y que igualmente condicionan el
    resultado. Un auditor necesita el estado real, no el declarado.
    """
    parametros = estimador.get_params(deep=False)
    canonico = json.dumps(parametros, sort_keys=True, default=repr)
    return hash_sha256(canonico.encode("utf-8"))


def _hash_datos(X: "pd.DataFrame", y: "pd.Series") -> str:
    """Hash conjunto de características y etiquetas de entrenamiento."""
    from src.comun.datos import hash_dataframe

    return hash_sha256(
        (hash_dataframe(X) + hash_dataframe(y.to_frame())).encode("utf-8")
    )


def entrenar(
    X_entrenamiento: "pd.DataFrame",
    y_entrenamiento: "pd.Series",
    config: "Configuracion",
) -> ModeloSellado:
    """Entrena el estimador de forma determinista y lo sella.

    Comprueba la coherencia de semillas antes de entrenar: una semilla
    divergente no rompe nada, solo hace que la corrida deje de ser
    reproducible en silencio, y conviene detectarlo antes de gastar el
    entrenamiento.

    Returns:
        El `ModeloSellado`, ya serializado en
        `config.rutas.artefactos/modelo/`.

    Raises:
        ConfiguracionInvalida: si el modelo o las semillas son incoherentes.
        ValueError: si `X_entrenamiento` e `y_entrenamiento` no coinciden en
            longitud, o si el conjunto está vacío.
    """
    from src.comun.configuracion import verificar_coherencia_semillas

    verificar_coherencia_semillas(config)

    if len(X_entrenamiento) != len(y_entrenamiento):
        raise ValueError(
            f"X ({len(X_entrenamiento)}) e y ({len(y_entrenamiento)}) no "
            "tienen la misma longitud"
        )
    if X_entrenamiento.empty:
        raise ValueError("el conjunto de entrenamiento está vacío")

    estimador = construir_estimador(config)
    estimador.fit(X_entrenamiento, y_entrenamiento)

    destino = asegurar_directorio(
        Path(config.rutas.artefactos) / "modelo"
    ) / _NOMBRE_SERIALIZADO

    sellado = ModeloSellado(
        estimador=estimador,
        version=config.modelo.version,
        hash_parametros=_hash_parametros(estimador),
        hash_datos_entrenamiento=_hash_datos(X_entrenamiento, y_entrenamiento),
        ruta_serializado=destino,
    )
    _serializar(sellado, destino)
    return sellado


def _serializar(sellado: ModeloSellado, destino: Path) -> None:
    """Persiste el modelo y su procedencia en un único archivo."""
    carga: dict[str, Any] = {
        "estimador": sellado.estimador,
        "version": sellado.version,
        "hash_parametros": sellado.hash_parametros,
        "hash_datos_entrenamiento": sellado.hash_datos_entrenamiento,
        "version_sklearn": sellado.version_sklearn,
    }
    joblib.dump(carga, destino)


def predecir_con_confianza(
    modelo: ModeloSellado, X: "pd.DataFrame"
) -> "tuple[pd.Series, pd.Series]":
    """Devuelve `(predicciones, confianza)`.

    La confianza es la probabilidad de la clase predicha
    (`predict_proba().max(axis=1)`). Es el valor que la bitácora registra por
    inferencia, así que debe corresponder a la clase efectivamente emitida y
    no al máximo de otra cosa.

    Raises:
        ValueError: si el estimador no expone `predict_proba`. Sin
            probabilidad no hay campo `confianza`, y el esquema de la
            bitácora lo exige.
    """
    import pandas as pd

    estimador = modelo.estimador
    if not hasattr(estimador, "predict_proba"):
        raise ValueError(
            f"{type(estimador).__name__} no expone predict_proba; el esquema "
            "de la bitácora exige una confianza por inferencia"
        )

    predicciones = pd.Series(estimador.predict(X), index=X.index, name="prediccion")
    probabilidades = estimador.predict_proba(X)
    confianza = pd.Series(
        probabilidades.max(axis=1), index=X.index, name="confianza"
    )
    return predicciones, confianza


def cargar_modelo(ruta: str | Path) -> ModeloSellado:
    """Carga un `ModeloSellado` previamente serializado.

    Raises:
        FileNotFoundError: si `ruta` no existe.
        ModeloIncompatible: si el archivo se produjo con otra versión de
            scikit-learn. Deserializar un estimador bajo una versión distinta
            de la que lo creó puede cambiar su comportamiento sin aviso, y un
            expediente construido así no reconstruye nada.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe el modelo serializado: {ruta}")

    carga = joblib.load(ruta)
    version_origen = carga.get("version_sklearn")
    if version_origen != sklearn.__version__:
        raise ModeloIncompatible(
            f"{ruta}: el modelo se entrenó con scikit-learn {version_origen} "
            f"y aquí corre {sklearn.__version__}; las predicciones podrían no "
            "coincidir con las registradas en la bitácora"
        )

    return ModeloSellado(
        estimador=carga["estimador"],
        version=carga["version"],
        hash_parametros=carga["hash_parametros"],
        hash_datos_entrenamiento=carga["hash_datos_entrenamiento"],
        ruta_serializado=ruta,
        version_sklearn=version_origen,
    )


class ModeloIncompatible(RuntimeError):
    """El modelo serializado no puede cargarse de forma fiable aquí."""
