"""Pruebas de carga y validación de `config.yaml`.

Esqueletos: se completan cuando `src.comun.configuracion` esté implementado.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="TODO: implementar src.comun.configuracion")


def test_carga_config_real_del_repo(ruta_config):
    """`cargar_configuracion(config.yaml)` devuelve una `Configuracion`."""
    # TODO: assert sobre version_marco, semilla == 42, rutas resueltas.


def test_falla_si_falta_una_clave_obligatoria(tmp_path):
    """Un YAML incompleto lanza `ConfiguracionInvalida`, no usa defaults."""
    # TODO: escribir un yaml parcial en tmp_path y esperar la excepción.


def test_umbrales_equidad_presentes_y_no_negativos(config):
    """Todos los umbrales esperados existen y son >= 0."""
    # TODO.


def test_semilla_coincide_con_random_state_del_modelo(config):
    """`verificar_coherencia_semillas` no lanza para el config del repo."""
    # TODO.
