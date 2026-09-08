"""Pruebas del orquestador y los 6 pasos.

Esqueletos: se completan cuando `src.procedimiento` esté implementado.
"""

from __future__ import annotations

import pytest

from src.procedimiento.pasos import PASOS


def test_hay_exactamente_seis_pasos():
    """El marco tiene 6 pasos, en orden fijo."""
    assert len(PASOS) == 6
    assert [p.__name__ for p in PASOS] == [
        "paso_1_preparar_datos",
        "paso_2_entrenar_modelo",
        "paso_3_explicabilidad",
        "paso_4_equidad",
        "paso_5_trazabilidad",
        "paso_6_evidencia",
    ]


@pytest.mark.integracion
@pytest.mark.lento
@pytest.mark.skip(reason="TODO: implementar el pipeline completo")
def test_pipeline_completo_es_reproducible(tmp_path):
    """Dos ejecuciones con el mismo config producen manifiestos con los
    mismos hashes de artefactos."""
    # TODO.
    ...
