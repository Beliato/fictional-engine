"""Pruebas de explicabilidad (SHAP local y global).

Esqueletos: se completan cuando `src.explicabilidad` esté implementado.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="TODO: implementar src.explicabilidad")


def test_explicacion_local_determinista(datos_sinteticos, config):
    """Dos ejecuciones con la misma semilla dan las mismas contribuciones."""
    # TODO.
    ...


def test_explicacion_local_genera_artefacto_referenciable(datos_sinteticos, config):
    """`ExplicacionLocal.ruta_artefacto` existe y contiene JSON válido."""
    # TODO.
    ...


def test_importancia_global_suma_coherente_con_local(datos_sinteticos, config):
    # TODO: media de |SHAP| local ~= importancia global reportada.
    ...
