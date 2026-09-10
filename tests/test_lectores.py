"""Pruebas del contrato de ingesta.

Estas pruebas son las que sostienen la afirmación de que el marco se aplica a
cualquier dataset de sensores pasivos: verifican que la costura existe, que
está declarada y que se hace cumplir.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from src.comun import lectores as L
from src.comun.lectores import (
    COLUMNAS_EVENTOS,
    ContratoIncumplido,
    FormatoNoReconocido,
    LectorEventos,
    LectorEventosCASAS,
    leer_eventos,
    obtener_lector,
)


@pytest.fixture
def config_con_crudo(config, tmp_path, crudo_sintetico):
    def construir(texto: str | None = None, **cambios):
        ruta = tmp_path / "crudo.txt"
        ruta.write_text(
            texto if texto is not None else crudo_sintetico(), encoding="utf-8"
        )
        datos = dataclasses.replace(config.datos, archivo_crudo=ruta, **cambios)
        return dataclasses.replace(config, datos=datos)

    return construir


# --- Selección del lector ----------------------------------------------------


def test_el_formato_declarado_selecciona_el_lector(config):
    lector = obtener_lector(config)

    assert isinstance(lector, LectorEventosCASAS)
    assert lector.nombre == config.datos.formato


def test_un_formato_no_registrado_falla_con_las_opciones(config):
    c = dataclasses.replace(
        config, datos=dataclasses.replace(config.datos, formato="parquet_magico")
    )
    with pytest.raises(FormatoNoReconocido) as exc:
        obtener_lector(c)

    assert "parquet_magico" in str(exc.value)
    assert "casas_eventos" in str(exc.value)


def test_todo_lector_registrado_se_declara_bajo_su_propio_nombre(config):
    """La clave del registro y el atributo del lector no pueden divergir."""
    for nombre, clase in L.LECTORES.items():
        assert issubclass(clase, LectorEventos)
        assert clase.nombre == nombre
        assert clase.formato, f"{nombre} no describe su formato"


# --- El contrato se hace cumplir ---------------------------------------------


class _LectorRoto(LectorEventos):
    """Adaptador de prueba que devuelve lo que se le indique."""

    nombre = "roto"
    formato = "solo para pruebas"

    def __init__(self, salida):
        self._salida = salida

    def leer(self, config):
        return self._salida


def _config_con_lector(config, salida, monkeypatch):
    monkeypatch.setitem(L.LECTORES, "roto", lambda: _LectorRoto(salida))
    return dataclasses.replace(
        config, datos=dataclasses.replace(config.datos, formato="roto")
    )


def test_rechaza_algo_que_no_es_dataframe(config, monkeypatch):
    c = _config_con_lector(config, [1, 2, 3], monkeypatch)

    with pytest.raises(ContratoIncumplido, match="DataFrame"):
        leer_eventos(c)


def test_rechaza_columnas_distintas(config, monkeypatch):
    """Un adaptador con otras columnas rompería todo aguas abajo."""
    salida = pd.DataFrame({"cuando": [], "que": []})
    c = _config_con_lector(config, salida, monkeypatch)

    with pytest.raises(ContratoIncumplido, match="columnas"):
        leer_eventos(c)


def test_rechaza_una_tabla_vacia(config, monkeypatch):
    salida = pd.DataFrame({c: [] for c in COLUMNAS_EVENTOS})
    c = _config_con_lector(config, salida, monkeypatch)

    with pytest.raises(ContratoIncumplido, match="ningún evento"):
        leer_eventos(c)


def test_rechaza_marca_temporal_que_no_es_fecha(config, monkeypatch):
    salida = pd.DataFrame(
        {
            "marca_temporal": ["ayer", "hoy"],
            "sensor": ["M001", "M002"],
            "valor": ["ON", "OFF"],
            "actividad": ["Otro", "Otro"],
        }
    )
    c = _config_con_lector(config, salida, monkeypatch)

    with pytest.raises(ContratoIncumplido, match="datetime64"):
        leer_eventos(c)


def test_rechaza_eventos_desordenados(config, monkeypatch):
    """La ventana y la partición temporal dependen del orden."""
    salida = pd.DataFrame(
        {
            "marca_temporal": pd.to_datetime(
                ["2010-11-04 10:00", "2010-11-04 09:00"]
            ),
            "sensor": ["M001", "M002"],
            "valor": ["ON", "OFF"],
            "actividad": ["Otro", "Otro"],
        }
    )
    c = _config_con_lector(config, salida, monkeypatch)

    with pytest.raises(ContratoIncumplido, match="ordenados"):
        leer_eventos(c)


def test_rechaza_nulos_en_columnas_obligatorias(config, monkeypatch):
    salida = pd.DataFrame(
        {
            "marca_temporal": pd.to_datetime(["2010-11-04 09:00"]),
            "sensor": [None],
            "valor": ["ON"],
            "actividad": ["Otro"],
        }
    )
    c = _config_con_lector(config, salida, monkeypatch)

    with pytest.raises(ContratoIncumplido, match="sensor"):
        leer_eventos(c)


def test_el_error_nombra_al_adaptador_culpable(config, monkeypatch):
    """Quien lea el fallo tiene que saber qué lector arreglar."""
    c = _config_con_lector(config, pd.DataFrame({"x": [1]}), monkeypatch)

    with pytest.raises(ContratoIncumplido, match="_LectorRoto"):
        leer_eventos(c)


# --- Un dataset ajeno se integra sin tocar el marco --------------------------


class _LectorCSVAjeno(LectorEventos):
    """Un formato inventado: CSV con encabezado y etiqueta por fila.

    Representa un dataset PIR de otro proveedor. Si el marco es realmente
    agnóstico, integrarlo debe requerir solo esta clase.
    """

    nombre = "csv_ajeno"
    formato = "CSV con columnas ts,dispositivo,estado,etiqueta"

    def leer(self, config):
        crudo = pd.read_csv(config.datos.archivo_crudo)
        return pd.DataFrame(
            {
                "marca_temporal": pd.to_datetime(crudo["ts"]),
                "sensor": crudo["dispositivo"].astype(str),
                "valor": crudo["estado"].astype(str),
                "actividad": crudo["etiqueta"].astype(str),
            }
        )


def test_un_dataset_ajeno_recorre_el_pipeline_sin_tocar_el_marco(
    config, tmp_path, monkeypatch
):
    """La prueba de fuego del §5.6: otro formato, mismo marco.

    No se modifica `datos.py`, `modelado.py` ni el procedimiento: solo se
    registra un lector y se cambia una clave del `config.yaml`.
    """
    from src.comun import datos as D

    filas = []
    for dia in range(1, 9):
        for i in range(40):
            filas.append(
                {
                    "ts": f"2011-01-{dia:02d} {i % 24:02d}:{i:02d}:00",
                    "dispositivo": f"M{(i % 31) + 1:03d}",
                    "estado": "ON",
                    "etiqueta": "Relax" if i % 2 else "Sleeping",
                }
            )
        for t in range(1, 6):
            filas.append(
                {
                    "ts": f"2011-01-{dia:02d} 23:5{t}:00",
                    "dispositivo": f"T00{t}",
                    "estado": f"{20 + t / 2:.1f}",
                    "etiqueta": "Relax",
                }
            )
    ruta = tmp_path / "ajeno.csv"
    pd.DataFrame(filas).sort_values("ts").to_csv(ruta, index=False)

    monkeypatch.setitem(L.LECTORES, _LectorCSVAjeno.nombre, _LectorCSVAjeno)
    c = dataclasses.replace(
        config,
        datos=dataclasses.replace(
            config.datos, archivo_crudo=ruta, formato=_LectorCSVAjeno.nombre
        ),
    )

    eventos = D.cargar_crudo(c)
    D.validar_esquema(eventos, c)
    X = D.construir_caracteristicas(eventos, c)
    particion = D.particionar(X, c)

    assert list(eventos.columns) == list(COLUMNAS_EVENTOS)
    assert len(particion.X_entrenamiento) > 0
    assert len(particion.X_prueba) > 0
    # Las características siguen nombrándose por zona: la interpretabilidad
    # que exige el R3.3 no depende del formato de origen.
    assert "conteo_Kitchen" in particion.X_entrenamiento.columns
    assert list(particion.sensibles_prueba.columns) == [
        s.columna for s in c.equidad.subgrupos
    ]


# --- Lector de CASAS ---------------------------------------------------------


def test_casas_falla_si_el_archivo_no_corresponde_al_formato(config_con_crudo):
    """Un archivo de otro formato no debe producir una tabla vacía."""
    c = config_con_crudo("ts,dispositivo,estado\n2011-01-01,M001,ON\n")

    with pytest.raises(FormatoNoReconocido, match="formato"):
        leer_eventos(c)


def test_casas_reporta_las_lineas_descartadas(config_con_crudo):
    c = config_con_crudo(
        "2010-11-04 00:00:00.000000 M003 ON\n"
        "2010-11-04 00:00:05.000000 LEAVEHOME ON\n"
        "2010-11-04 00:00:15.000000 M004 ON\n"
    )
    eventos = leer_eventos(c)

    assert eventos.attrs["lineas_descartadas"] == 1
