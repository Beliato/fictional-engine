"""Pruebas del control de aleatoriedad y de la instantánea del entorno."""

from __future__ import annotations

import random

import numpy as np
import pytest

from src.comun.semillas import (
    PAQUETES,
    EntornoNoDeterminista,
    fijar_semilla_global,
    instantanea_entorno,
    verificar_pythonhashseed,
)


def test_fijar_semilla_hace_repetible_la_aleatoriedad():
    fijar_semilla_global(42)
    primera = (random.random(), np.random.rand(3).tolist())
    fijar_semilla_global(42)

    assert primera == (random.random(), np.random.rand(3).tolist())


def test_pythonhashseed_coincide_con_el_declarado(config):
    """La batería corre con PYTHONHASHSEED fijado, como el pipeline."""
    verificar_pythonhashseed(config.pythonhashseed)


def test_pythonhashseed_ausente_o_distinto_falla(monkeypatch):
    monkeypatch.delenv("PYTHONHASHSEED", raising=False)
    with pytest.raises(EntornoNoDeterminista, match="no está fijado"):
        verificar_pythonhashseed(42)

    monkeypatch.setenv("PYTHONHASHSEED", "7")
    with pytest.raises(EntornoNoDeterminista, match="reproducible"):
        verificar_pythonhashseed(42)


def test_la_instantanea_declara_versiones_y_estado_de_git():
    entorno = instantanea_entorno()

    assert {"python", "plataforma", "pythonhashseed"} <= entorno.keys()
    assert set(PAQUETES) <= entorno.keys()
    assert all(entorno[p] != "(ausente)" for p in PAQUETES), entorno
    # El commit puede no estar disponible fuera de un repositorio, pero la
    # clave existe siempre: el manifiesto declara la ausencia.
    assert entorno["git_commit"]
    assert entorno["git_arbol_limpio"] in {"sí", "no", "(no disponible)"}
