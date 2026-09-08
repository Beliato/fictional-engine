"""Pruebas del escritor/verificador de la bitácora.

Esqueletos: se completan cuando `src.trazabilidad.registro` y
`src.trazabilidad.verificacion` estén implementados.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="TODO: implementar src.trazabilidad.registro/verificacion"
)


def test_registro_es_append_only(tmp_path, config):
    """Registrar dos veces produce dos líneas; no se reescribe la primera."""
    # TODO.
    ...


def test_registrar_rechaza_confianza_fuera_de_rango(tmp_path, config):
    # TODO: confianza = 1.5 -> ValueError.
    ...


def test_verificar_detecta_id_evento_duplicado(tmp_path, config):
    # TODO.
    ...


def test_verificar_detecta_responsable_placeholder(tmp_path, config):
    """Un `responsable` que contiene 'TODO' invalida la bitácora."""
    # TODO.
    ...


def test_verificar_cobertura_reporta_inferencias_faltantes(tmp_path, config):
    # TODO.
    ...
