"""Pruebas del entrenamiento, sellado y persistencia del modelo."""

from __future__ import annotations

import dataclasses

import pytest

from tests.conftest import aislar_rutas
import sklearn

from src.comun import modelado as M
from src.comun.configuracion import ConfiguracionInvalida
from src.comun.modelado import ModeloIncompatible, ModeloSellado


@pytest.fixture
def config_rapida(config, tmp_path):
    """Config con artefactos en `tmp_path` y un bosque chico.

    300 árboles sobre datos sintéticos no aportan nada a lo que se prueba
    aquí —el sellado y el determinismo— y multiplican el tiempo de la
    batería.
    """
    rutas = aislar_rutas(config.rutas, tmp_path / "artefactos")
    modelo = dataclasses.replace(
        config.modelo,
        hiperparametros={**config.modelo.hiperparametros, "n_estimators": 8},
    )
    return dataclasses.replace(config, rutas=rutas, modelo=modelo)


@pytest.fixture
def conjunto():
    """Conjunto tabular pequeño, separable y determinista."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(0)
    n = 120
    X = pd.DataFrame(
        {
            "conteo_Kitchen": rng.integers(0, 10, n),
            "conteo_Bedroom": rng.integers(0, 10, n),
            "hora_del_dia": rng.integers(0, 24, n),
        }
    )
    y = pd.Series(
        ["Meal_Preparation" if k > b else "Sleeping"
         for k, b in zip(X["conteo_Kitchen"], X["conteo_Bedroom"])],
        name="actividad",
    )
    return X, y


# --- Construcción del estimador ----------------------------------------------


def test_construye_el_estimador_declarado(config_rapida):
    estimador = M.construir_estimador(config_rapida)

    assert type(estimador).__name__ == config_rapida.modelo.tipo
    assert estimador.get_params()["random_state"] == config_rapida.semilla


def test_rechaza_un_tipo_de_modelo_desconocido(config_rapida):
    c = dataclasses.replace(
        config_rapida,
        modelo=dataclasses.replace(config_rapida.modelo, tipo="MiModeloFavorito"),
    )
    with pytest.raises(ConfiguracionInvalida, match="MiModeloFavorito"):
        M.construir_estimador(c)


def test_solo_admite_modelos_de_arbol(config_rapida):
    """TreeExplainer exige esa familia; admitir otra rompería el paso 4."""
    c = dataclasses.replace(
        config_rapida,
        modelo=dataclasses.replace(
            config_rapida.modelo, tipo="LogisticRegression"
        ),
    )
    with pytest.raises(ConfiguracionInvalida, match="árbol"):
        M.construir_estimador(c)

    assert set(M.MODELOS_ADMITIDOS) == {
        "RandomForestClassifier",
        "ExtraTreesClassifier",
        "GradientBoostingClassifier",
        "DecisionTreeClassifier",
    }


def test_rechaza_hiperparametros_que_el_modelo_no_acepta(config_rapida):
    c = dataclasses.replace(
        config_rapida,
        modelo=dataclasses.replace(
            config_rapida.modelo,
            hiperparametros={"parametro_inventado": 1},
        ),
    )
    with pytest.raises(ConfiguracionInvalida, match="no acepta"):
        M.construir_estimador(c)


# --- Entrenamiento y sellado --------------------------------------------------


def test_entrenar_produce_un_modelo_sellado(config_rapida, conjunto):
    X, y = conjunto
    sellado = M.entrenar(X, y, config_rapida)

    assert isinstance(sellado, ModeloSellado)
    assert sellado.version == config_rapida.modelo.version
    assert sellado.version_sklearn == sklearn.__version__
    assert len(sellado.hash_parametros) == 64
    assert len(sellado.hash_datos_entrenamiento) == 64
    assert sellado.ruta_serializado.is_file()


def test_el_entrenamiento_es_determinista(config_rapida, conjunto):
    """Dos corridas con la misma semilla producen el mismo modelo."""
    X, y = conjunto
    a = M.entrenar(X, y, config_rapida)
    b = M.entrenar(X, y, config_rapida)

    assert a.hash_parametros == b.hash_parametros
    assert a.hash_datos_entrenamiento == b.hash_datos_entrenamiento
    pred_a, conf_a = M.predecir_con_confianza(a, X)
    pred_b, conf_b = M.predecir_con_confianza(b, X)
    assert pred_a.equals(pred_b)
    assert conf_a.equals(conf_b)


def test_el_hash_de_datos_cambia_si_cambian_los_datos(config_rapida, conjunto):
    X, y = conjunto
    a = M.entrenar(X, y, config_rapida)
    X2 = X.copy()
    X2.loc[0, "conteo_Kitchen"] = int(X2.loc[0, "conteo_Kitchen"]) + 1
    b = M.entrenar(X2, y, config_rapida)

    assert a.hash_datos_entrenamiento != b.hash_datos_entrenamiento


def test_el_hash_de_datos_distingue_las_etiquetas(config_rapida, conjunto):
    """Mismas características con otras etiquetas no son el mismo dato."""
    X, y = conjunto
    a = M.entrenar(X, y, config_rapida)
    b = M.entrenar(X, y.iloc[::-1].reset_index(drop=True), config_rapida)

    assert a.hash_datos_entrenamiento != b.hash_datos_entrenamiento


def test_el_hash_de_parametros_refleja_los_efectivos(config_rapida, conjunto):
    """Se hashea get_params(), no el YAML: incluye los valores por defecto."""
    X, y = conjunto
    a = M.entrenar(X, y, config_rapida)
    c = dataclasses.replace(
        config_rapida,
        modelo=dataclasses.replace(
            config_rapida.modelo,
            hiperparametros={
                **config_rapida.modelo.hiperparametros,
                "max_depth": 3,
            },
        ),
    )
    b = M.entrenar(X, y, c)

    assert a.hash_parametros != b.hash_parametros


def test_entrenar_verifica_la_coherencia_de_semillas(config_rapida, conjunto):
    """Una semilla divergente mata la reproducibilidad en silencio."""
    X, y = conjunto
    c = dataclasses.replace(
        config_rapida,
        modelo=dataclasses.replace(
            config_rapida.modelo,
            hiperparametros={
                **config_rapida.modelo.hiperparametros,
                "random_state": 7,
            },
        ),
    )
    with pytest.raises(ConfiguracionInvalida, match="random_state"):
        M.entrenar(X, y, c)


@pytest.mark.parametrize("caso", ["desalineado", "vacio"])
def test_entrenar_rechaza_conjuntos_invalidos(config_rapida, conjunto, caso):
    X, y = conjunto
    if caso == "desalineado":
        y = y.iloc[:-5]
        patron = "misma longitud"
    else:
        X, y = X.iloc[:0], y.iloc[:0]
        patron = "vacío"

    with pytest.raises(ValueError, match=patron):
        M.entrenar(X, y, config_rapida)


# --- Predicción ---------------------------------------------------------------


def test_predecir_devuelve_prediccion_y_confianza(config_rapida, conjunto):
    X, y = conjunto
    sellado = M.entrenar(X, y, config_rapida)
    predicciones, confianza = M.predecir_con_confianza(sellado, X)

    assert len(predicciones) == len(X)
    assert set(predicciones) <= set(y)
    assert confianza.between(0.0, 1.0).all()
    assert list(predicciones.index) == list(X.index)


def test_la_confianza_corresponde_a_la_clase_predicha(config_rapida, conjunto):
    """No es el máximo de cualquier cosa: es la probabilidad de lo emitido."""
    X, y = conjunto
    sellado = M.entrenar(X, y, config_rapida)
    predicciones, confianza = M.predecir_con_confianza(sellado, X)

    clases = list(sellado.estimador.classes_)
    probabilidades = sellado.estimador.predict_proba(X)
    for i, prediccion in enumerate(predicciones):
        esperada = probabilidades[i][clases.index(prediccion)]
        assert confianza.iloc[i] == pytest.approx(esperada)


# --- Persistencia -------------------------------------------------------------


def test_cargar_recupera_la_procedencia(config_rapida, conjunto):
    X, y = conjunto
    original = M.entrenar(X, y, config_rapida)
    recuperado = M.cargar_modelo(original.ruta_serializado)

    assert recuperado.version == original.version
    assert recuperado.hash_parametros == original.hash_parametros
    assert recuperado.hash_datos_entrenamiento == original.hash_datos_entrenamiento
    assert recuperado.version_sklearn == original.version_sklearn


def test_el_modelo_cargado_predice_igual(config_rapida, conjunto):
    X, y = conjunto
    original = M.entrenar(X, y, config_rapida)
    recuperado = M.cargar_modelo(original.ruta_serializado)

    assert M.predecir_con_confianza(original, X)[0].equals(
        M.predecir_con_confianza(recuperado, X)[0]
    )


def test_cargar_falla_si_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError):
        M.cargar_modelo(tmp_path / "no_existe.joblib")


def test_rechaza_un_modelo_de_otra_version_de_sklearn(config_rapida, conjunto):
    """Un estimador deserializado bajo otra versión puede cambiar de conducta.

    Un expediente construido así no reconstruye las decisiones registradas.
    """
    import joblib

    X, y = conjunto
    sellado = M.entrenar(X, y, config_rapida)
    carga = joblib.load(sellado.ruta_serializado)
    carga["version_sklearn"] = "0.0.1"
    joblib.dump(carga, sellado.ruta_serializado)

    with pytest.raises(ModeloIncompatible, match="0.0.1"):
        M.cargar_modelo(sellado.ruta_serializado)
