"""Fixtures compartidas de la batería de pruebas."""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def ruta_config() -> Path:
    """Ruta al `config.yaml` real del repositorio."""
    return RAIZ / "config.yaml"


@pytest.fixture
def config(ruta_config):
    """Configuración cargada desde el `config.yaml` del repo."""
    from src.comun.configuracion import cargar_configuracion

    return cargar_configuracion(ruta_config)


@pytest.fixture
def datos_sinteticos():
    """DataFrame pequeño y determinista que imita el esquema de CASAS.

    Útil para probar pasos sin descargar el dataset real.

    TODO: construir con `numpy.random.default_rng(0)` un DataFrame con
        columnas de sensores PIR, marca temporal y actividad.
    """
    pytest.skip("TODO: construir datos sintéticos con el esquema de CASAS")
