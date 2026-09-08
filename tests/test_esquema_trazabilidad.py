"""Pruebas del esquema de trazabilidad (módulo ya implementado)."""

from __future__ import annotations

import json

import pytest

from src.trazabilidad.esquema import (
    VERSION_ESQUEMA,
    RegistroInferencia,
    RegistroInvalido,
)


def _registro_valido(**overrides) -> RegistroInferencia:
    base = dict(
        id_evento="evt-0001",
        marca_temporal="2026-09-07T12:00:00.000Z",
        referencia_entrada="sha256:" + "a" * 64,
        salida_modelo="cocinar",
        confianza=0.92,
        version_modelo="0.1.0",
        version_marco="0.1.0",
        referencia_explicacion="artefactos/explicaciones/local/evt-0001.json",
        responsable="Ada Lovelace — Responsable de cumplimiento",
    )
    base.update(overrides)
    return RegistroInferencia(**base)


def test_roundtrip_jsonl():
    reg = _registro_valido()
    linea = reg.a_linea_jsonl()
    datos = json.loads(linea)
    assert RegistroInferencia.desde_diccionario(datos) == reg


def test_jsonl_tiene_claves_ordenadas_y_version_esquema():
    datos = json.loads(_registro_valido().a_linea_jsonl())
    assert list(datos) == sorted(datos)
    assert datos["version_esquema"] == VERSION_ESQUEMA


def test_desde_diccionario_rechaza_campos_faltantes():
    with pytest.raises(RegistroInvalido):
        RegistroInferencia.desde_diccionario({"id_evento": "x"})


def test_desde_diccionario_rechaza_campos_desconocidos():
    datos = json.loads(_registro_valido().a_linea_jsonl())
    datos["campo_raro"] = 1
    with pytest.raises(RegistroInvalido):
        RegistroInferencia.desde_diccionario(datos)


def test_registro_es_inmutable():
    reg = _registro_valido()
    with pytest.raises(Exception):
        reg.confianza = 0.1  # type: ignore[misc]
