"""Pruebas del orquestador y los 6 pasos."""

from __future__ import annotations

import dataclasses

import pytest

from src.procedimiento.evidencia import EvidenciaIncompleta
from src.procedimiento.pasos import (
    PASOS,
    PRECONDICIONES,
    PrecondicionIncumplida,
    nuevo_contexto,
    paso_1_caracterizacion_sistema,
    paso_2_documentacion_datos,
    precondicion_preparar_datos,
    precondicion_sellar_modelo,
)


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


# --- Precondiciones y pasos 1 y 2 ---------------------------------------------


@pytest.fixture
def config_piloto(config, tmp_path, crudo_sintetico):
    """Config con crudo sintético y artefactos en `tmp_path`.

    Bosque chico: lo que se prueba es el procedimiento, no el desempeño.
    """
    crudo = tmp_path / "crudo.txt"
    crudo.write_text(crudo_sintetico(dias=12, eventos_por_dia=150), encoding="utf-8")
    artefactos = tmp_path / "artefactos"
    rutas = dataclasses.replace(
        config.rutas,
        artefactos=artefactos,
        ficha_caracterizacion=artefactos / "ficha_caracterizacion.md",
        datasheet=artefactos / "datasheet.md",
    )
    datos = dataclasses.replace(config.datos, archivo_crudo=crudo)
    modelo = dataclasses.replace(
        config.modelo,
        hiperparametros={**config.modelo.hiperparametros, "n_estimators": 8},
    )
    return dataclasses.replace(config, rutas=rutas, datos=datos, modelo=modelo)


@pytest.fixture
def ctx_preparado(config_piloto):
    ctx = nuevo_contexto(config_piloto, "prueba-001")
    return precondicion_sellar_modelo(precondicion_preparar_datos(ctx))


def test_las_precondiciones_sellan_datos_y_modelo(ctx_preparado):
    """Dejan en el contexto lo que los artefactos tendrán que declarar."""
    ctx = ctx_preparado

    assert ctx.particion is not None and ctx.modelo is not None
    assert ctx.n_eventos_crudos > 0
    assert len(ctx.caracteristicas) > 0
    # Dos hashes distintos: origen y preparación se auditan por separado.
    assert len(ctx.hash_datos_crudos) == 64 and len(ctx.hash_datos) == 64
    assert ctx.hash_datos_crudos != ctx.hash_datos
    assert [e["paso"] for e in ctx.eventos] == [
        "precondicion_preparar_datos",
        "precondicion_sellar_modelo",
    ]


def test_sellar_el_modelo_exige_los_datos_preparados(config_piloto):
    """Sin partición no hay con qué entrenar: es un error de ejecución."""
    with pytest.raises(PrecondicionIncumplida, match="partición"):
        precondicion_sellar_modelo(nuevo_contexto(config_piloto, "prueba-001"))


def test_paso_1_genera_la_ficha_de_caracterizacion(ctx_preparado):
    ctx = paso_1_caracterizacion_sistema(ctx_preparado)
    ruta = ctx.artefactos["ficha_caracterizacion"]
    texto = ruta.read_text(encoding="utf-8")

    assert "{{" not in texto
    assert ctx.config.sistema.finalidad in texto
    assert ctx.config.trazabilidad.responsable_por_defecto in texto
    assert ctx.marca_inicio in texto
    assert ctx.eventos[-1]["paso"] == "paso_1_caracterizacion_sistema"
    assert len(ctx.eventos[-1]["hash"]) == 64


def test_paso_1_exige_el_modelo_sellado(config_piloto):
    """La ficha declara la versión del modelo evaluado; sin modelo, no hay
    sistema que caracterizar."""
    ctx = precondicion_preparar_datos(nuevo_contexto(config_piloto, "prueba-001"))

    with pytest.raises(EvidenciaIncompleta, match="modelo sellado"):
        paso_1_caracterizacion_sistema(ctx)


def test_paso_2_genera_el_datasheet_con_la_composicion_real(ctx_preparado):
    ctx = paso_2_documentacion_datos(ctx_preparado)
    texto = ctx.artefactos["datasheet"].read_text(encoding="utf-8")

    assert "{{" not in texto
    assert ctx.hash_datos_crudos in texto and ctx.hash_datos in texto
    assert "| Actividad | Ventanas | % |" in texto
    assert ctx.config.datos.documentacion.licencia in texto
    # La clase de los eventos sin anotar tiene que aparecer en la tabla.
    assert ctx.config.datos.actividades.etiqueta_sin_actividad in texto


def test_paso_2_exige_los_datos_preparados(config_piloto):
    ctx = nuevo_contexto(config_piloto, "prueba-001")

    with pytest.raises(EvidenciaIncompleta, match="características"):
        paso_2_documentacion_datos(ctx)


def test_los_artefactos_de_los_pasos_1_y_2_son_deterministas(ctx_preparado):
    """Con el mismo contexto, dos corridas producen los mismos bytes: el
    manifiesto compara hashes entre ejecuciones."""
    primera = [
        paso.__wrapped__(ctx_preparado)  # type: ignore[attr-defined]
        if hasattr(paso, "__wrapped__")
        else paso(ctx_preparado)
        for paso in (paso_1_caracterizacion_sistema, paso_2_documentacion_datos)
    ]
    bytes_primera = [
        list(ctx.artefactos.values())[-1].read_bytes() for ctx in primera
    ]
    segunda = [
        paso(ctx_preparado)
        for paso in (paso_1_caracterizacion_sistema, paso_2_documentacion_datos)
    ]
    bytes_segunda = [list(ctx.artefactos.values())[-1].read_bytes() for ctx in segunda]

    assert bytes_primera == bytes_segunda
    assert all(b"\r\n" not in contenido for contenido in bytes_primera)


@pytest.mark.integracion
@pytest.mark.lento
@pytest.mark.skip(reason="TODO: implementar el pipeline completo")
def test_pipeline_completo_es_reproducible(tmp_path):
    """Dos ejecuciones con el mismo config producen manifiestos con los
    mismos hashes de artefactos."""
    # TODO.
    ...
