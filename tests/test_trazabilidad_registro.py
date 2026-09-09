"""Pruebas del escritor/verificador de la bitácora."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from src.trazabilidad.esquema import RegistroInvalido
from src.trazabilidad.registro import RegistroEstructurado, leer_registros
from src.trazabilidad.verificacion import (
    verificar_cobertura,
    verificar_registro,
)


@pytest.fixture
def config_sin_explicaciones(config):
    """Config con la comprobación de artefactos de explicación desactivada.

    La mayoría de las pruebas verifica la bitácora en sí, no la existencia de
    los artefactos SHAP que todavía no genera nadie.
    """
    explicabilidad = dataclasses.replace(
        config.explicabilidad, guardar_local_por_inferencia=False
    )
    return dataclasses.replace(config, explicabilidad=explicabilidad)


@pytest.fixture
def responsable():
    """Un responsable real: el de `config.yaml` es todavía un placeholder."""
    return "Miguel Méndez — Investigador responsable"


@pytest.fixture
def bitacora(tmp_path) -> Path:
    return tmp_path / "bitacora" / "inferencias.jsonl"


def _campos(n: int, responsable: str) -> dict:
    return {
        "id_evento": f"evt-{n:03d}",
        "referencia_entrada": f"{n:064x}",
        "salida_modelo": "preparar_comida",
        "confianza": 0.9,
        "referencia_explicacion": f"artefactos/explicaciones/evt-{n:03d}.json",
        "responsable": responsable,
    }


# --- Escritura ---------------------------------------------------------------


def test_registro_es_append_only(bitacora, config, responsable):
    """Registrar dos veces produce dos líneas; no se reescribe la primera."""
    registro = RegistroEstructurado(bitacora, config)
    primero = registro.registrar(**_campos(1, responsable))
    segundo = registro.registrar(**_campos(2, responsable))

    lineas = bitacora.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    assert json.loads(lineas[0])["id_evento"] == primero.id_evento
    assert json.loads(lineas[1])["id_evento"] == segundo.id_evento


def test_un_escritor_nuevo_no_trunca_la_bitacora(bitacora, config, responsable):
    """Reabrir para una segunda corrida no puede borrar la evidencia previa."""
    RegistroEstructurado(bitacora, config).registrar(**_campos(1, responsable))
    RegistroEstructurado(bitacora, config).registrar(**_campos(2, responsable))

    assert len(bitacora.read_text(encoding="utf-8").splitlines()) == 2


def test_crea_el_directorio_padre(tmp_path, config):
    ruta = tmp_path / "no" / "existe" / "aun" / "inferencias.jsonl"
    RegistroEstructurado(ruta, config)

    assert ruta.parent.is_dir()


def test_rellena_los_campos_automaticos(bitacora, config, responsable):
    """Versiones y marca temporal salen de la config, no de quien llama."""
    escrito = RegistroEstructurado(bitacora, config).registrar(
        **_campos(1, responsable)
    )

    assert escrito.version_modelo == config.modelo.version
    assert escrito.version_marco == config.version_marco
    assert escrito.version_esquema == config.trazabilidad.version_esquema
    assert escrito.marca_temporal.endswith("Z")


def test_responsable_por_defecto_sale_de_la_config(bitacora, config):
    escrito = RegistroEstructurado(bitacora, config).registrar(
        id_evento="evt-001",
        referencia_entrada="a" * 64,
        salida_modelo="dormir",
        confianza=0.5,
        referencia_explicacion="artefactos/explicaciones/evt-001.json",
    )

    assert escrito.responsable == config.trazabilidad.responsable_por_defecto


def test_falla_si_la_version_de_esquema_no_coincide(bitacora, config):
    """Escribir bajo una versión y auditar bajo otra no evidencia nada."""
    trazabilidad = dataclasses.replace(
        config.trazabilidad, version_esquema="9.9.9"
    )
    incoherente = dataclasses.replace(config, trazabilidad=trazabilidad)

    with pytest.raises(ValueError, match="versión de esquema"):
        RegistroEstructurado(bitacora, incoherente)


@pytest.mark.parametrize("valor", [1.5, -0.1])
def test_registrar_rechaza_confianza_fuera_de_rango(
    bitacora, config, responsable, valor
):
    registro = RegistroEstructurado(bitacora, config)
    campos = _campos(1, responsable) | {"confianza": valor}

    with pytest.raises(ValueError, match="confianza"):
        registro.registrar(**campos)


def test_registrar_rechaza_confianza_booleana(bitacora, config, responsable):
    """`True` pasaría por 1.0 sin un rechazo explícito."""
    registro = RegistroEstructurado(bitacora, config)
    campos = _campos(1, responsable) | {"confianza": True}

    with pytest.raises(ValueError, match="confianza"):
        registro.registrar(**campos)


@pytest.mark.parametrize(
    "campo", ["id_evento", "referencia_entrada", "salida_modelo", "responsable"]
)
def test_registrar_rechaza_campos_vacios(bitacora, config, responsable, campo):
    registro = RegistroEstructurado(bitacora, config)
    campos = _campos(1, responsable) | {campo: "   "}

    with pytest.raises(ValueError, match=campo):
        registro.registrar(**campos)


def test_un_registro_invalido_no_se_escribe(bitacora, config, responsable):
    """El rechazo ocurre antes de tocar el archivo."""
    registro = RegistroEstructurado(bitacora, config)
    with pytest.raises(ValueError):
        registro.registrar(**(_campos(1, responsable) | {"confianza": 2.0}))

    assert not bitacora.exists() or bitacora.read_text(encoding="utf-8") == ""


# --- Lotes -------------------------------------------------------------------


def test_registrar_lote_conserva_el_orden(bitacora, config, responsable):
    escritos = RegistroEstructurado(bitacora, config).registrar_lote(
        [_campos(n, responsable) for n in range(1, 6)]
    )

    ids_en_archivo = [
        json.loads(l)["id_evento"]
        for l in bitacora.read_text(encoding="utf-8").splitlines()
    ]
    assert ids_en_archivo == [r.id_evento for r in escritos]
    assert ids_en_archivo == [f"evt-{n:03d}" for n in range(1, 6)]


def test_lote_invalido_no_escribe_nada(bitacora, config, responsable):
    """En una bitácora append-only no se puede retirar una línea ya escrita.

    Por eso el lote se valida entero antes de escribir la primera.
    """
    lote = [_campos(n, responsable) for n in range(1, 4)]
    lote[2]["confianza"] = 7.0

    registro = RegistroEstructurado(bitacora, config)
    with pytest.raises(ValueError, match="confianza"):
        registro.registrar_lote(lote)

    assert not bitacora.exists() or bitacora.read_text(encoding="utf-8") == ""


def test_lote_vacio_no_crea_archivo(bitacora, config):
    assert RegistroEstructurado(bitacora, config).registrar_lote([]) == []
    assert not bitacora.exists()


# --- Lectura -----------------------------------------------------------------


def test_leer_registros_recupera_lo_escrito(bitacora, config, responsable):
    escritos = RegistroEstructurado(bitacora, config).registrar_lote(
        [_campos(n, responsable) for n in range(1, 4)]
    )

    assert list(leer_registros(bitacora)) == escritos


def test_leer_registros_falla_de_inmediato_si_no_existe(tmp_path):
    """No al consumir el primer elemento: al llamar."""
    with pytest.raises(FileNotFoundError):
        leer_registros(tmp_path / "no_existe.jsonl")


def test_leer_registros_señala_la_linea_mal_formada(bitacora, config, responsable):
    RegistroEstructurado(bitacora, config).registrar(**_campos(1, responsable))
    with bitacora.open("a", encoding="utf-8") as f:
        f.write("{esto no es json}\n")

    with pytest.raises(RegistroInvalido, match=":2:"):
        list(leer_registros(bitacora))


def test_leer_registros_ignora_lineas_en_blanco(bitacora, config, responsable):
    RegistroEstructurado(bitacora, config).registrar(**_campos(1, responsable))
    with bitacora.open("a", encoding="utf-8") as f:
        f.write("\n\n")

    assert len(list(leer_registros(bitacora))) == 1


# --- Verificación de integridad ----------------------------------------------


def test_verificar_acepta_una_bitacora_correcta(
    bitacora, config_sin_explicaciones, responsable
):
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar_lote(
        [_campos(n, responsable) for n in range(1, 4)]
    )

    informe = verificar_registro(bitacora, config_sin_explicaciones)
    assert informe.valido, informe.problemas
    assert informe.n_registros == 3


def test_verificar_detecta_id_evento_duplicado(
    bitacora, config_sin_explicaciones, responsable
):
    escritor = RegistroEstructurado(bitacora, config_sin_explicaciones)
    escritor.registrar(**_campos(1, responsable))
    escritor.registrar(**_campos(1, responsable))

    informe = verificar_registro(bitacora, config_sin_explicaciones)
    assert not informe.valido
    assert any("duplicado" in p for p in informe.problemas)


def test_verificar_detecta_responsable_placeholder(
    bitacora, config_sin_explicaciones
):
    """Un `responsable` que contiene 'TODO' invalida la bitácora."""
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar(
        id_evento="evt-001",
        referencia_entrada="a" * 64,
        salida_modelo="dormir",
        confianza=0.5,
        referencia_explicacion="artefactos/explicaciones/evt-001.json",
    )

    informe = verificar_registro(bitacora, config_sin_explicaciones)
    assert not informe.valido
    assert any("plantilla" in p for p in informe.problemas)


def test_verificar_detecta_version_de_modelo_ajena(
    bitacora, config_sin_explicaciones, responsable
):
    """Registros de otra versión del modelo contaminan la evidencia."""
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar(
        **_campos(1, responsable)
    )
    otra = dataclasses.replace(
        config_sin_explicaciones,
        modelo=dataclasses.replace(config_sin_explicaciones.modelo, version="9.9.9"),
    )

    informe = verificar_registro(bitacora, otra)
    assert not informe.valido
    assert any("version_modelo" in p for p in informe.problemas)


def test_verificar_detecta_marcas_fuera_de_orden(
    bitacora, config_sin_explicaciones, responsable
):
    escritor = RegistroEstructurado(bitacora, config_sin_explicaciones)
    escritor.registrar_lote([_campos(n, responsable) for n in (1, 2)])

    lineas = bitacora.read_text(encoding="utf-8").splitlines()
    primera = json.loads(lineas[0])
    segunda = json.loads(lineas[1])
    segunda["marca_temporal"] = "2020-01-01T00:00:00.000Z"
    assert primera["marca_temporal"] > segunda["marca_temporal"]
    bitacora.write_text(
        json.dumps(primera, sort_keys=True)
        + "\n"
        + json.dumps(segunda, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    informe = verificar_registro(bitacora, config_sin_explicaciones)
    assert not informe.valido
    assert any("fuera de orden" in p for p in informe.problemas)


def test_verificar_detecta_marca_temporal_no_utc(
    bitacora, config_sin_explicaciones, responsable
):
    """Una bitácora en hora local es inauditable al cambiar de zona."""
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar(
        **_campos(1, responsable)
    )
    datos = json.loads(bitacora.read_text(encoding="utf-8").splitlines()[0])
    datos["marca_temporal"] = "2026-09-08T10:00:00.000-06:00"
    bitacora.write_text(json.dumps(datos, sort_keys=True) + "\n", encoding="utf-8")

    informe = verificar_registro(bitacora, config_sin_explicaciones)
    assert not informe.valido
    assert any("UTC" in p for p in informe.problemas)


def test_verificar_reporta_bitacora_vacia(bitacora, config_sin_explicaciones):
    """Cero inferencias registradas no evidencian el comportamiento de nada."""
    bitacora.parent.mkdir(parents=True, exist_ok=True)
    bitacora.write_text("", encoding="utf-8")

    informe = verificar_registro(bitacora, config_sin_explicaciones)
    assert not informe.valido
    assert any("vacía" in p for p in informe.problemas)


def test_verificar_reporta_bitacora_inexistente(bitacora, config_sin_explicaciones):
    informe = verificar_registro(bitacora, config_sin_explicaciones)

    assert not informe.valido
    assert informe.n_registros == 0
    assert any("no existe" in p for p in informe.problemas)


def test_verificar_exige_el_artefacto_de_explicacion(bitacora, config, responsable):
    """Con `guardar_local_por_inferencia`, la referencia debe resolver."""
    RegistroEstructurado(bitacora, config).registrar(**_campos(1, responsable))

    informe = verificar_registro(bitacora, config)
    assert not informe.valido
    assert any("referencia_explicacion" in p for p in informe.problemas)


def test_el_resumen_lista_los_problemas(bitacora, config_sin_explicaciones):
    informe = verificar_registro(bitacora, config_sin_explicaciones)
    resumen = informe.resumen()

    assert "NO VÁLIDA" in resumen
    assert "no existe" in resumen


# --- Verificación de cobertura -----------------------------------------------


def test_verificar_cobertura_acepta_correspondencia_exacta(
    bitacora, config_sin_explicaciones, responsable
):
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar_lote(
        [_campos(n, responsable) for n in range(1, 4)]
    )
    esperados = {f"evt-{n:03d}" for n in range(1, 4)}

    informe = verificar_cobertura(bitacora, esperados, config_sin_explicaciones)
    assert informe.valido, informe.problemas


def test_verificar_cobertura_reporta_inferencias_faltantes(
    bitacora, config_sin_explicaciones, responsable
):
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar_lote(
        [_campos(n, responsable) for n in range(1, 3)]
    )
    esperados = {f"evt-{n:03d}" for n in range(1, 6)}

    informe = verificar_cobertura(bitacora, esperados, config_sin_explicaciones)
    assert not informe.valido
    assert any("faltan 3" in p for p in informe.problemas)


def test_verificar_cobertura_reporta_sobrantes(
    bitacora, config_sin_explicaciones, responsable
):
    RegistroEstructurado(bitacora, config_sin_explicaciones).registrar_lote(
        [_campos(n, responsable) for n in range(1, 4)]
    )

    informe = verificar_cobertura(
        bitacora, {"evt-001"}, config_sin_explicaciones
    )
    assert not informe.valido
    assert any("no esperados" in p for p in informe.problemas)


def test_verificar_cobertura_detecta_duplicados(
    bitacora, config_sin_explicaciones, responsable
):
    """Un id repetido no es faltante ni sobrante, pero rompe el 1:1."""
    escritor = RegistroEstructurado(bitacora, config_sin_explicaciones)
    escritor.registrar(**_campos(1, responsable))
    escritor.registrar(**_campos(1, responsable))

    informe = verificar_cobertura(
        bitacora, {"evt-001"}, config_sin_explicaciones
    )
    assert not informe.valido
    assert any("duplicados" in p for p in informe.problemas)
