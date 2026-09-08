"""Pruebas de equidad: métricas desagregadas y veredicto vs umbrales.

Esqueletos: se completan cuando `src.equidad` esté implementado.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="TODO: implementar src.equidad")


def test_desempeno_desagregado_una_fila_por_categoria(datos_sinteticos, config):
    # TODO.
    ...


def test_metricas_equidad_contra_umbrales_predeclarados(datos_sinteticos, config):
    # TODO: verificar que el umbral usado es exactamente config.equidad.umbrales.
    ...


def test_veredicto_falla_si_cualquier_metrica_incumple(config):
    # TODO: construir resultados con una métrica fuera de umbral -> aprueba == False.
    ...


def test_veredicto_no_puede_ajustar_umbral_en_runtime():
    """No debe existir API para modificar un umbral tras cargar la config."""
    # TODO: asegurar que ConfigEquidad es frozen y no hay setters.
    ...
