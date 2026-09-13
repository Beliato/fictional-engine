"""Pruebas de equidad: desempeño desagregado, métricas y veredicto (R4.1, R4.2)."""

from __future__ import annotations

import dataclasses
import json

import pandas as pd
import pytest

from tests.conftest import aislar_rutas

from src.comun.configuracion import METRICAS_EQUIDAD, Subgrupo
from src.equidad import desempeno_desagregado as D
from src.equidad import metricas_equidad as ME
from src.equidad import reporte as R
from src.equidad.entradas import CategoriaNoDeclarada, EntradasDesalineadas

TVP = "true_positive_rate_difference"
TFP = "false_positive_rate_difference"
PROB_IGUALADAS = "equalized_odds_difference"
PARIDAD = "demographic_parity_difference"
COCIENTE = "selection_rate_ratio"

FRANJA = Subgrupo(
    nombre="franja",
    columna="franja",
    categorias=("dia", "noche"),
    justificacion="Subgrupo de prueba.",
)

# Sleeping se reconoce en 3 de 4 ventanas de día y en 4 de 4 de noche:
# diferencia de TVP de 0,25.
DISPARIDAD_TVP = (
    ("dia", "Sleeping", "Sleeping", 3),
    ("dia", "Sleeping", "Relax", 1),
    ("noche", "Sleeping", "Sleeping", 4),
    ("dia", "Relax", "Relax", 4),
    ("noche", "Relax", "Relax", 4),
)


def _con(config, tmp_path, *, soporte=2, umbrales=None, descriptivas=None):
    """Config con un único subgrupo de dos categorías y artefactos en
    `tmp_path`: cada caso cabe en una docena de ventanas."""
    equidad = dataclasses.replace(
        config.equidad,
        subgrupos=(FRANJA,),
        soporte_minimo=soporte,
        umbrales=umbrales if umbrales is not None else {TVP: 0.10, TFP: 0.10},
        descriptivas=(
            tuple(descriptivas) if descriptivas is not None else (PARIDAD, COCIENTE)
        ),
    )
    rutas = aislar_rutas(config.rutas, tmp_path / "artefactos")
    return dataclasses.replace(config, equidad=equidad, rutas=rutas)


@pytest.fixture
def config_eq(config, tmp_path):
    return _con(config, tmp_path)


def _ventanas(*bloques):
    """(categoría, real, predicha, veces) -> etiquetas, predicciones, sensibles."""
    filas = [(c, r, p) for c, r, p, veces in bloques for _ in range(veces)]
    categorias, reales, predichas = zip(*filas)
    return pd.Series(reales), pd.Series(predichas), pd.DataFrame({"franja": categorias})


def _resultado(veredicto, metrica, actividad):
    (encontrado,) = [
        r
        for r in veredicto.resultados
        if r.metrica == metrica and r.actividad == actividad
    ]
    return encontrado


# --- Métricas -----------------------------------------------------------------


def test_un_modelo_perfecto_aprueba_aunque_la_paridad_difiera(config_eq):
    """D42 hecho prueba: con frecuencias distintas por categoría, un modelo
    perfecto no tiene disparidad de TVP ni de TFP, pero sí de paridad."""
    y, p, s = _ventanas(
        ("dia", "Sleeping", "Sleeping", 2),
        ("dia", "Relax", "Relax", 8),
        ("noche", "Sleeping", "Sleeping", 8),
        ("noche", "Relax", "Relax", 2),
    )
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    assert veredicto.estado == "aprueba"
    assert _resultado(veredicto, TVP, "Sleeping").valor_observado == 0.0
    paridad = _resultado(veredicto, PARIDAD, "Sleeping")
    assert paridad.valor_observado == pytest.approx(0.6)
    assert paridad.estado == "descriptiva"


def test_la_paridad_multiclase_no_devuelve_cero_en_silencio(config_eq):
    """`fairlearn` 0.10 devuelve 0,0 aquí, porque toma `pos_label=1`, que no
    existe: un "aprueba" falso (D43)."""
    y, p, s = _ventanas(("dia", "A", "A", 5), ("noche", "B", "B", 5))
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    assert _resultado(veredicto, PARIDAD, "A").valor_observado == 1.0


def test_una_disparidad_de_tvp_sobre_el_umbral_no_aprueba(config_eq):
    y, p, s = _ventanas(*DISPARIDAD_TVP)
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    tvp = _resultado(veredicto, TVP, "Sleeping")
    assert tvp.valor_observado == pytest.approx(0.25)
    assert tvp.estado == "incumple"
    assert tvp in veredicto.metricas_incumplidas()
    assert veredicto.estado == "no_aprueba"
    assert not veredicto.aprueba


def test_la_tfp_se_calcula_sobre_las_ventanas_de_otra_actividad(config_eq):
    """Sleeping nunca ocurre, pero se predice: tiene TFP aunque no TVP."""
    y, p, s = _ventanas(
        ("dia", "Relax", "Sleeping", 1),
        ("dia", "Relax", "Relax", 3),
        ("noche", "Relax", "Relax", 4),
    )
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    tfp = _resultado(veredicto, TFP, "Sleeping")
    assert [(t.categoria, t.numerador, t.denominador) for t in tfp.tasas] == [
        ("dia", 1, 4),
        ("noche", 0, 4),
    ]
    assert tfp.valor_observado == pytest.approx(0.25)
    assert not _resultado(veredicto, TVP, "Sleeping").evaluable


def test_una_diferencia_exactamente_igual_al_umbral_cumple(config_eq):
    """En coma flotante, 0,8 - 0,7 da 0,10000000000000009 y reprobaría (D45)."""
    assert 0.8 - 0.7 > 0.10
    y, p, s = _ventanas(
        ("dia", "Sleeping", "Sleeping", 7),
        ("dia", "Sleeping", "Relax", 3),
        ("noche", "Sleeping", "Sleeping", 8),
        ("noche", "Sleeping", "Relax", 2),
    )
    tvp = _resultado(ME.evaluar_equidad(y, p, s, config_eq), TVP, "Sleeping")

    assert tvp.cumple is True


@pytest.mark.parametrize(("umbral", "estado"), [(0.30, "aprueba"), (0.20, "no_aprueba")])
def test_el_umbral_es_exactamente_el_de_la_configuracion(
    config, tmp_path, umbral, estado
):
    config_eq = _con(config, tmp_path, umbrales={TVP: umbral})
    y, p, s = _ventanas(*DISPARIDAD_TVP)

    assert ME.evaluar_equidad(y, p, s, config_eq).estado == estado


def test_probabilidades_igualadas_es_la_mayor_de_las_dos_diferencias(
    config, tmp_path
):
    config_eq = _con(
        config, tmp_path, umbrales={PROB_IGUALADAS: 0.10}, descriptivas=[TVP, TFP]
    )
    y, p, s = _ventanas(*DISPARIDAD_TVP)
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    igualadas = _resultado(veredicto, PROB_IGUALADAS, "Sleeping")
    assert igualadas.valor_observado == max(
        _resultado(veredicto, TVP, "Sleeping").valor_observado,
        _resultado(veredicto, TFP, "Sleeping").valor_observado,
    )
    assert {t.tasa for t in igualadas.tasas} == {"tvp", "tfp"}


def test_cada_metrica_del_catalogo_se_calcula_y_se_nombra():
    assert set(ME.TASAS_DE_METRICA) == set(METRICAS_EQUIDAD)
    assert set(R.NOMBRES_METRICA) == set(METRICAS_EQUIDAD)


# --- Soporte mínimo y veredicto -----------------------------------------------


def test_una_categoria_sin_soporte_queda_fuera_de_la_comparacion(config, tmp_path):
    config_eq = _con(config, tmp_path, soporte=3)
    y, p, s = _ventanas(("dia", "Sleeping", "Sleeping", 3), ("noche", "Sleeping", "Relax", 2))

    tvp = _resultado(ME.evaluar_equidad(y, p, s, config_eq), TVP, "Sleeping")
    assert [t.en_comparacion for t in tvp.tasas] == [True, False]
    assert not tvp.evaluable
    assert "menos de dos categorías" in tvp.motivo


def test_sin_ninguna_combinacion_evaluable_el_veredicto_no_es_aprueba(
    config, tmp_path
):
    config_eq = _con(config, tmp_path, soporte=100)
    y, p, s = _ventanas(("dia", "Sleeping", "Sleeping", 5), ("noche", "Sleeping", "Sleeping", 5))
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    assert veredicto.estado == "no_evaluable"
    assert not veredicto.aprueba
    assert veredicto.cobertura == (0, 2)
    assert len(veredicto.no_evaluables()) == 2


def test_un_veredicto_sin_resultados_no_aprueba():
    assert ME.emitir_veredicto([]).estado == "no_evaluable"


def test_el_cociente_sin_predicciones_de_la_actividad_no_es_evaluable(config_eq):
    y, p, s = _ventanas(("dia", "Sleeping", "Relax", 2), ("noche", "Sleeping", "Relax", 2))

    cociente = _resultado(ME.evaluar_equidad(y, p, s, config_eq), COCIENTE, "Sleeping")
    assert not cociente.evaluable
    assert "predicciones" in cociente.motivo


def test_los_resultados_son_inmutables(config_eq):
    """No debe existir forma de reescribir un umbral o un veredicto después
    de calculados."""
    veredicto = ME.evaluar_equidad(*_ventanas(*DISPARIDAD_TVP), config_eq)

    with pytest.raises(dataclasses.FrozenInstanceError):
        veredicto.estado = "aprueba"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        veredicto.resultados[0].umbral = 1.0  # type: ignore[misc]


# --- Entradas -----------------------------------------------------------------


def test_rechaza_entradas_desalineadas(config_eq):
    y, p, s = _ventanas(("dia", "A", "A", 3), ("noche", "A", "A", 3))

    with pytest.raises(EntradasDesalineadas, match="longitud"):
        ME.evaluar_equidad(y, p.iloc[:-1], s, config_eq)
    with pytest.raises(EntradasDesalineadas, match="índice"):
        ME.evaluar_equidad(y, p.set_axis(range(10, 16)), s, config_eq)


def test_una_categoria_no_declarada_es_un_error(config_eq):
    y, p, s = _ventanas(("dia", "A", "A", 3), ("tarde", "A", "A", 3))

    with pytest.raises(CategoriaNoDeclarada, match="tarde"):
        ME.evaluar_equidad(y, p, s, config_eq)
    with pytest.raises(CategoriaNoDeclarada, match="tarde"):
        D.calcular_desempeno(y, p, s, config_eq)


# --- Desempeño desagregado ----------------------------------------------------


def test_desempeno_una_fila_por_categoria_declarada():
    subgrupo = dataclasses.replace(FRANJA, categorias=("dia", "noche", "madrugada"))
    y, p, s = _ventanas(
        ("dia", "Sleeping", "Sleeping", 3),
        ("dia", "Relax", "Sleeping", 1),
        ("noche", "Relax", "Relax", 2),
    )
    filas = D.calcular_desempeno_desagregado(y, p, s, subgrupo)

    assert [(f.categoria, f.n) for f in filas] == [
        ("dia", 4),
        ("noche", 2),
        ("madrugada", 0),
    ]
    assert filas[0].accuracy == pytest.approx(0.75)
    assert filas[0].n_actividades == 2
    assert filas[2].accuracy is None


# --- Artefactos ---------------------------------------------------------------


def test_los_artefactos_son_deterministas(config_eq):
    y, p, s = _ventanas(*DISPARIDAD_TVP)

    corridas = []
    for _ in range(2):
        csv = D.guardar_desempeno(D.calcular_desempeno(y, p, s, config_eq), config_eq)
        js = ME.guardar_metricas(ME.evaluar_equidad(y, p, s, config_eq), config_eq)
        corridas.append((csv.read_bytes(), js.read_bytes()))

    assert corridas[0] == corridas[1]
    assert b"\r\n" not in corridas[0][0]
    metricas = json.loads(corridas[0][1])
    assert metricas["estado"] == "no_aprueba"
    tasa = metricas["resultados"][0]["tasas"][0]
    assert {"numerador", "denominador", "en_comparacion"} <= tasa.keys()


def test_el_reporte_rellena_toda_la_plantilla(config_eq):
    y, p, s = _ventanas(*DISPARIDAD_TVP)
    desempeno = D.calcular_desempeno(y, p, s, config_eq)
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    ruta = R.generar_reporte_equidad(desempeno, veredicto, "prueba-001", config_eq)
    texto = ruta.read_text(encoding="utf-8")

    assert "{{" not in texto
    assert "prueba-001" in texto
    assert "**NO APRUEBA**" in texto
    assert "Subgrupo de prueba." in texto
    for limitacion in config_eq.equidad.limitaciones:
        assert limitacion in texto
    assert ruta.read_bytes() == R.generar_reporte_equidad(
        desempeno, veredicto, "prueba-001", config_eq
    ).read_bytes()


def test_el_reporte_de_un_veredicto_no_evaluable_lo_dice(config, tmp_path):
    config_eq = _con(config, tmp_path, soporte=100)
    y, p, s = _ventanas(*DISPARIDAD_TVP)
    veredicto = ME.evaluar_equidad(y, p, s, config_eq)

    texto = R.generar_reporte_equidad(
        D.calcular_desempeno(y, p, s, config_eq), veredicto, "prueba-002", config_eq
    ).read_text(encoding="utf-8")

    assert "**NO EVALUABLE**" in texto
    assert "no es un aprobado" in texto
