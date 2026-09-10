"""Pruebas de carga, características y partición del dataset CASAS.

Ninguna depende del crudo real: pesa 61 MB, está fuera de git y su licencia
prohíbe redistribuirlo. Se usa el generador `crudo_sintetico`, que reproduce
el formato de Aruba incluidos los spans `begin`/`end`.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from src.comun import datos as D
from src.comun.datos import EsquemaDatosInvalido
from src.comun.lectores import FormatoNoReconocido


@pytest.fixture
def config_con_crudo(config, tmp_path, crudo_sintetico):
    """Config del repo apuntando a un crudo sintético en `tmp_path`."""

    def construir(texto: str | None = None, **cambios_datos):
        ruta = tmp_path / "crudo.txt"
        ruta.write_text(
            texto if texto is not None else crudo_sintetico(), encoding="utf-8"
        )
        datos = dataclasses.replace(
            config.datos, archivo_crudo=ruta, **cambios_datos
        )
        return dataclasses.replace(config, datos=datos)

    return construir


# --- Carga -------------------------------------------------------------------


def test_carga_los_eventos_y_ordena_por_tiempo(config_con_crudo):
    c = config_con_crudo()
    df = D.cargar_crudo(c)

    assert len(df) > 0
    assert list(df.columns) == ["marca_temporal", "sensor", "valor", "actividad"]
    assert df["marca_temporal"].is_monotonic_increasing


def test_propaga_la_actividad_entre_begin_y_end(config_con_crudo):
    """Los eventos intermedios no llevan etiqueta: heredan la abierta."""
    texto = (
        "2010-11-04 00:00:00.000000 M003 ON Sleeping begin\n"
        "2010-11-04 00:00:10.000000 M004 ON\n"
        "2010-11-04 00:00:20.000000 M005 OFF Sleeping end\n"
        "2010-11-04 00:00:30.000000 M006 ON\n"
    )
    df = D.cargar_crudo(config_con_crudo(texto))

    assert list(df["actividad"]) == ["Sleeping", "Sleeping", "Sleeping", "Otro"]


def test_los_eventos_fuera_de_todo_span_son_otro(config_con_crudo):
    texto = (
        "2010-11-04 00:00:00.000000 M003 ON\n"
        "2010-11-04 00:00:10.000000 M004 ON\n"
    )
    df = D.cargar_crudo(config_con_crudo(texto))

    assert set(df["actividad"]) == {"Otro"}


def test_cuenta_las_lineas_descartadas_en_vez_de_ocultarlas(config_con_crudo):
    """Aruba trae líneas donde la actividad se coló en la columna de sensor."""
    texto = (
        "2010-11-04 00:00:00.000000 M003 ON\n"
        "2010-11-04 00:00:05.000000 LEAVEHOME ON\n"
        "2010-11-04 00:00:10.000000 c 1\n"
        "2010-11-04 00:00:15.000000 M004 ON\n"
    )
    df = D.cargar_crudo(config_con_crudo(texto))

    assert len(df) == 2
    assert df.attrs["lineas_descartadas"] == 2


def test_falla_si_no_existe_el_crudo(config, tmp_path):
    c = dataclasses.replace(
        config,
        datos=dataclasses.replace(config.datos, archivo_crudo=tmp_path / "no.txt"),
    )
    with pytest.raises(FileNotFoundError):
        D.cargar_crudo(c)


def test_falla_si_ningun_evento_usa_un_sensor_declarado(config_con_crudo):
    """El lector no puede devolver una tabla vacía y seguir de largo."""
    texto = "2010-11-04 00:00:00.000000 ZZZ ON\n"
    with pytest.raises(FormatoNoReconocido, match="ningún evento"):
        D.cargar_crudo(config_con_crudo(texto))


# --- Validación --------------------------------------------------------------


def test_validar_acepta_un_crudo_correcto(config_con_crudo):
    c = config_con_crudo()
    D.validar_esquema(D.cargar_crudo(c), c)


def test_validar_rechaza_eventos_desordenados(config_con_crudo):
    c = config_con_crudo()
    df = D.cargar_crudo(c).iloc[::-1]

    with pytest.raises(EsquemaDatosInvalido, match="ordenados"):
        D.validar_esquema(df, c)


def test_validar_exige_los_sensores_pir_declarados(config_con_crudo):
    """Un PIR declarado y ausente delata un crudo que no es el esperado."""
    texto = "2010-11-04 00:00:00.000000 M003 ON\n" * 3
    c = config_con_crudo(texto)

    with pytest.raises(EsquemaDatosInvalido, match="ausentes"):
        D.validar_esquema(D.cargar_crudo(c), c)


def test_la_temperatura_no_necesita_zona(config_con_crudo):
    """Los sensores T miden una condición ambiental, no localizan a nadie."""
    c = config_con_crudo()
    df = D.cargar_crudo(c)

    assert "T001" in set(df["sensor"])
    D.validar_esquema(df, c)  # no debe lanzar


# --- Características ---------------------------------------------------------


def test_las_caracteristicas_se_nombran_por_zona_no_por_sensor(config_con_crudo):
    """El R3.3 exige que un cuidador pueda leerlas; "M018" no se lee."""
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)

    conteos = [col for col in X.columns if col.startswith("conteo_")]
    assert conteos == [f"conteo_{z}" for z in c.datos.zonas_distintas]
    assert "conteo_Kitchen" in conteos
    assert not any(col.startswith("conteo_M0") for col in X.columns)


def test_cada_ventana_agrupa_n_eventos(config_con_crudo):
    c = config_con_crudo()
    df = D.cargar_crudo(c)
    X = D.construir_caracteristicas(df, c)

    assert len(X) == len(df) // c.datos.ventana.n_eventos


def test_descarta_la_ventana_final_incompleta(config_con_crudo):
    """Una ventana corta tendría conteos sistemáticamente menores."""
    c = config_con_crudo()
    n = c.datos.ventana.n_eventos
    df = D.cargar_crudo(c).iloc[: n * 3 + 7]
    X = D.construir_caracteristicas(df, c)

    assert len(X) == 3


def test_las_caracteristicas_no_tienen_nulos(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)

    assert int(X.isna().sum().sum()) == 0


def test_excluye_las_actividades_declaradas(config_con_crudo):
    c = config_con_crudo()
    excluida = c.datos.actividades.etiqueta_sin_actividad
    c = dataclasses.replace(
        c,
        datos=dataclasses.replace(
            c.datos,
            actividades=dataclasses.replace(
                c.datos.actividades, excluidas=(excluida,)
            ),
        ),
    )
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)

    assert excluida not in set(X[c.datos.columna_objetivo])


def test_deriva_las_columnas_sensibles(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)

    assert set(X["franja_horaria"]) <= {"madrugada", "mañana", "tarde", "noche"}
    assert set(X["tipo_dia"]) <= {"laborable", "fin_de_semana"}


@pytest.mark.parametrize(
    ("hora", "esperada"),
    [(0, "madrugada"), (5, "madrugada"), (6, "mañana"), (11, "mañana"),
     (12, "tarde"), (17, "tarde"), (18, "noche"), (23, "noche")],
)
def test_franja_horaria_cubre_las_24_horas(config, hora, esperada):
    assert D.franja_horaria(hora, config.datos.franjas_horarias) == esperada


def test_las_franjas_salen_de_la_configuracion(config):
    """Cambiar los cortes es configurar, no editar código."""
    import dataclasses

    from src.comun.configuracion import FranjaHoraria

    turnos = (
        FranjaHoraria(desde=0, nombre="turno_noche"),
        FranjaHoraria(desde=8, nombre="turno_dia"),
    )
    assert D.franja_horaria(3, turnos) == "turno_noche"
    assert D.franja_horaria(20, turnos) == "turno_dia"
    assert dataclasses.is_dataclass(config.datos.franjas_horarias[0])


def test_las_sensibles_no_son_caracteristicas_del_modelo(config_con_crudo):
    """Entrenar sobre la columna del subgrupo haría trivial la disparidad."""
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    columnas = D.columnas_caracteristicas(X, c)

    for subgrupo in c.equidad.subgrupos:
        assert subgrupo.columna not in columnas
    assert c.datos.columna_objetivo not in columnas
    assert "fecha" not in columnas


# --- Partición ---------------------------------------------------------------


def test_la_particion_es_temporal_sin_dias_compartidos(config_con_crudo):
    """Ningún día cae a ambos lados: es lo que evita la fuga temporal."""
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    p = D.particionar(X, c)

    dias_train = set(X.loc[X.index[: len(p.X_entrenamiento)], "fecha"])
    dias_test = set(X.loc[X.index[len(p.X_entrenamiento) :], "fecha"])
    assert not dias_train & dias_test


def test_la_particion_respeta_el_orden_temporal(config_con_crudo):
    """Prueba son los últimos días, no unos cualesquiera."""
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    p = D.particionar(X, c)

    corte = len(p.X_entrenamiento)
    assert max(X["fecha"][:corte]) <= min(X["fecha"][corte:])


def test_la_particion_es_determinista(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)

    a, b = D.particionar(X, c), D.particionar(X, c)
    assert a.X_entrenamiento.equals(b.X_entrenamiento)
    assert a.y_prueba.equals(b.y_prueba)


def test_la_particion_separa_las_sensibles(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    p = D.particionar(X, c)

    esperadas = [s.columna for s in c.equidad.subgrupos]
    assert list(p.sensibles_prueba.columns) == esperadas
    assert len(p.sensibles_prueba) == len(p.X_prueba)
    assert len(p.sensibles_entrenamiento) == len(p.X_entrenamiento)


def test_falla_si_hay_menos_de_dos_dias(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    un_dia = X[X["fecha"] == X["fecha"].min()]

    with pytest.raises(EsquemaDatosInvalido, match="2 días"):
        D.particionar(un_dia, c)


def test_rechaza_una_estrategia_no_implementada(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    c = dataclasses.replace(
        c,
        datos=dataclasses.replace(
            c.datos,
            particion=dataclasses.replace(
                c.datos.particion, estrategia="aleatoria_estratificada"
            ),
        ),
    )
    with pytest.raises(NotImplementedError, match="temporal_por_dia"):
        D.particionar(X, c)


# --- Hash --------------------------------------------------------------------


def test_el_hash_es_estable_entre_llamadas(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)

    assert D.hash_dataframe(X) == D.hash_dataframe(X)


def test_el_hash_cambia_si_cambia_un_valor(config_con_crudo):
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    Y = X.copy()
    Y.loc[0, "conteo_Kitchen"] = int(Y.loc[0, "conteo_Kitchen"]) + 1

    assert D.hash_dataframe(X) != D.hash_dataframe(Y)


def test_el_hash_distingue_nombres_de_columna(config_con_crudo):
    """Los mismos valores bajo otro nombre no son el mismo dato."""
    c = config_con_crudo()
    X = D.construir_caracteristicas(D.cargar_crudo(c), c)
    Y = X.rename(columns={"conteo_Kitchen": "conteo_Cocina"})

    assert D.hash_dataframe(X) != D.hash_dataframe(Y)
