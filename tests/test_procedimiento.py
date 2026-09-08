"""Pruebas del orquestador y los 6 pasos.

Esqueletos: se completan cuando `src.procedimiento` esté implementado.
"""

from __future__ import annotations

import pytest

from src.procedimiento.pasos import PASOS, PRECONDICIONES


def test_hay_exactamente_seis_pasos():
    """El procedimiento tiene 6 pasos, en el orden de la Tabla 9."""
    assert len(PASOS) == 6
    assert [p.__name__ for p in PASOS] == [
        "paso_1_caracterizacion_sistema",
        "paso_2_documentacion_datos",
        "paso_3_declaracion_criterios",
        "paso_4_ejecucion_pruebas",
        "paso_5_generacion_artefactos",
        "paso_6_verificacion_auditabilidad",
    ]


def test_preparacion_y_modelo_no_son_pasos_del_marco():
    """El modelo es sujeto de prueba, no objeto de optimización (Tabla 10).

    Preparar los datos y sellar el modelo son precondiciones: si alguna
    apareciera en `PASOS`, el marco estaría auditando su propio insumo.
    """
    assert [p.__name__ for p in PRECONDICIONES] == [
        "precondicion_preparar_datos",
        "precondicion_sellar_modelo",
    ]
    assert not set(PRECONDICIONES) & set(PASOS)


def test_cada_paso_declara_su_producto_y_funcion_nist():
    """Cada paso documenta su producto (Tabla 9) y su función del NIST AI RMF.

    La trazabilidad hacia el documento no es decorativa: el criterio de éxito
    del piloto es haber ejecutado el procedimiento de la Tabla 9.
    """
    for paso in PASOS:
        doc = paso.__doc__ or ""
        assert "Producto:" in doc, f"{paso.__name__} no declara su producto"
        assert "Función NIST AI RMF:" in doc, f"{paso.__name__} no declara función"
        assert "Requerimientos:" in doc, f"{paso.__name__} no declara requerimientos"


@pytest.mark.integracion
@pytest.mark.lento
@pytest.mark.skip(reason="TODO: implementar el pipeline completo")
def test_pipeline_completo_es_reproducible(tmp_path):
    """Dos ejecuciones con el mismo config producen manifiestos con los
    mismos hashes de artefactos."""
    # TODO.
    ...
