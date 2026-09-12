"""Pruebas del contrato multi-hogar: lector CSV, ventanas y partición.

Cuando el dataset cubre varias viviendas, el contrato gana la columna
`hogar`. No es una característica: es clave de agrupación —las ventanas nunca
cruzan hogares y la partición es temporal dentro de cada uno— y columna
sensible, porque cada vivienda es una persona distinta.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.comun import datos as D
from src.comun.configuracion import cargar_configuracion
from src.comun.lectores import (
    COLUMNA_HOGAR,
    ContratoIncumplido,
    FormatoNoReconocido,
    leer_eventos,
)

RAIZ = Path(__file__).resolve().parents[1]
SENSORES = ("Bathroom", "Bedroom", "Kitchen", "LivingRoom", "OutsideDoor")


def _casa(dias: int = 5, eventos_por_dia: int = 40) -> str:
    """Genera el CSV de una vivienda, con spans de actividad y una puerta."""
    lineas = []
    for d in range(dias):
        fecha = f"2012-07-{d + 1:02d}"
        for i in range(eventos_por_dia):
            hora = f"{i // 4 % 24:02d}:{i * 7 % 60:02d}:{i % 60:02d}.000000"
            sensor = SENSORES[i % len(SENSORES)]
            if i % 20 == 0:
                lineas.append(f"{fecha},{hora},{sensor},ON,Sleep=\"begin\"")
            elif i % 20 == 10:
                lineas.append(f"{fecha},{hora},{sensor},OFF,Sleep=\"end\"")
            elif i % 13 == 0:
                lineas.append(f"{fecha},{hora},OutsideDoor,OPEN")
            else:
                lineas.append(f"{fecha},{hora},{sensor},ON")
    return "\n".join(lineas) + "\n"


def _config(
    tmp_path,
    hogares: tuple[str, ...] = ("casa_a", "casa_b"),
    ajustes_actividades: dict | None = None,
):
    """Config derivada de la del repo que apunta a un directorio de hogares."""
    crudos = tmp_path / "datos" / "crudos" / "hogares"
    crudos.mkdir(parents=True)
    for i, hogar in enumerate(hogares):
        (crudos / f"{hogar}.csv").write_text(
            _casa(dias=5 + i), encoding="utf-8"
        )

    crudo = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    crudo["datos"]["archivo_crudo"] = "datos/crudos/hogares"
    crudo["datos"]["formato"] = "casas_csv"
    crudo["datos"]["columnas_sensor_pir"] = list(SENSORES)
    crudo["datos"]["sensores_puerta"] = ["OutsideDoor_Puerta"]
    crudo["datos"]["sensores_temperatura"] = []
    crudo["datos"]["zonas"] = {
        **{s: s for s in SENSORES},
        "OutsideDoor_Puerta": "OutsideDoor",
    }
    crudo["datos"]["actividades"]["excluidas"] = []
    crudo["datos"]["actividades"].update(ajustes_actividades or {})
    crudo["datos"]["ventana"]["n_eventos"] = 10
    crudo["equidad"]["subgrupos"].append(
        {
            "nombre": "hogar",
            "columna": "hogar",
            "categorias": sorted(hogares),
            "justificacion": "Cada vivienda es una persona distinta.",
        }
    )
    ruta = tmp_path / "config.yaml"
    ruta.write_text(
        yaml.safe_dump(crudo, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return cargar_configuracion(ruta)


@pytest.fixture
def config_hogares(tmp_path):
    return _config(tmp_path)


# --- Lector -------------------------------------------------------------------


def test_lee_un_directorio_y_marca_el_hogar_de_cada_evento(config_hogares):
    eventos = leer_eventos(config_hogares)

    assert list(eventos.columns)[-1] == COLUMNA_HOGAR
    assert set(eventos[COLUMNA_HOGAR].unique()) == {"casa_a", "casa_b"}
    # Cada hogar viene en un bloque contiguo y ordenado: la ventana y la
    # partición dependen de eso.
    bloques = (eventos[COLUMNA_HOGAR] != eventos[COLUMNA_HOGAR].shift()).sum()
    assert bloques == 2


def test_desdobla_el_sensor_que_tambien_es_puerta(config_hogares):
    """`OutsideDoor` reporta ON/OFF y OPEN/CLOSE; el marco separa por nombre."""
    eventos = leer_eventos(config_hogares)

    puerta = eventos[eventos.sensor == "OutsideDoor_Puerta"]
    assert not puerta.empty
    assert set(puerta.valor.str.upper()) <= {"OPEN", "CLOSE"}
    movimiento = eventos[eventos.sensor == "OutsideDoor"]
    assert set(movimiento.valor.str.upper()) <= {"ON", "OFF"}


def test_hereda_la_actividad_abierta_hasta_el_cierre(config_hogares):
    eventos = leer_eventos(config_hogares)
    etiquetas = eventos["actividad"].tolist()

    assert "Sleep" in etiquetas
    assert config_hogares.datos.actividades.etiqueta_sin_actividad in etiquetas


def test_un_directorio_sin_csv_es_un_error(config_hogares, tmp_path):
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    config = dataclasses.replace(
        config_hogares,
        datos=dataclasses.replace(config_hogares.datos, archivo_crudo=vacio),
    )

    with pytest.raises(FileNotFoundError, match="csv"):
        leer_eventos(config)


def test_el_contrato_exige_los_hogares_en_bloques(config_hogares):
    """Intercalar dos hogares rompería la ventana y la partición."""
    from src.comun.lectores import _verificar_contrato, obtener_lector

    eventos = leer_eventos(config_hogares)
    intercalados = eventos.sort_values("marca_temporal", kind="stable")

    with pytest.raises(ContratoIncumplido, match="bloques"):
        _verificar_contrato(intercalados, obtener_lector(config_hogares))


# --- Ventanas y partición -----------------------------------------------------


def test_las_ventanas_no_cruzan_hogares(config_hogares):
    eventos = leer_eventos(config_hogares)
    caracteristicas = D.construir_caracteristicas(eventos, config_hogares)

    assert COLUMNA_HOGAR in caracteristicas.columns
    assert set(caracteristicas[COLUMNA_HOGAR].unique()) == {"casa_a", "casa_b"}
    # Cada ventana consume n eventos de un solo hogar: el total por hogar no
    # puede superar lo que daría su propio recuento.
    por_hogar = eventos.groupby(COLUMNA_HOGAR).size() // config_hogares.datos.ventana.n_eventos
    conteo = caracteristicas.groupby(COLUMNA_HOGAR).size()
    assert (conteo <= por_hogar).all()


def test_cada_hogar_aparece_en_entrenamiento_y_en_prueba(config_hogares):
    """La partición es temporal dentro de cada vivienda: si una quedara solo
    en prueba, su desempeño no sería comparable con el de las demás."""
    eventos = leer_eventos(config_hogares)
    particion = D.particionar(
        D.construir_caracteristicas(eventos, config_hogares), config_hogares
    )

    for lado in (particion.sensibles_entrenamiento, particion.sensibles_prueba):
        assert set(lado[COLUMNA_HOGAR].unique()) == {"casa_a", "casa_b"}


def test_el_hogar_nunca_es_caracteristica_del_modelo(config_hogares):
    """Si el modelo pudiera distinguir viviendas, el análisis desagregado
    dejaría de poder descartar que aprendió a tratarlas distinto."""
    eventos = leer_eventos(config_hogares)
    caracteristicas = D.construir_caracteristicas(eventos, config_hogares)

    columnas = D.columnas_caracteristicas(caracteristicas, config_hogares)
    assert COLUMNA_HOGAR not in columnas
    particion = D.particionar(caracteristicas, config_hogares)
    assert COLUMNA_HOGAR not in particion.X_entrenamiento.columns
    assert COLUMNA_HOGAR in particion.sensibles_entrenamiento.columns


def test_un_hogar_con_un_solo_dia_no_se_puede_partir(tmp_path):
    config = _config(tmp_path)
    eventos = leer_eventos(config)
    caracteristicas = D.construir_caracteristicas(eventos, config)
    un_dia = caracteristicas[
        (caracteristicas[COLUMNA_HOGAR] == "casa_a")
        & (caracteristicas["fecha"] == caracteristicas["fecha"].min())
    ]
    mezcla = pd.concat(
        [un_dia, caracteristicas[caracteristicas[COLUMNA_HOGAR] == "casa_b"]]
    )

    with pytest.raises(D.EsquemaDatosInvalido, match="casa_a"):
        D.particionar(mezcla, config)


def test_el_formato_csv_rechaza_un_crudo_de_otro_formato(tmp_path, crudo_sintetico):
    """Apuntar el lector CSV al crudo separado por espacios debe fallar en la
    costura, no tres pasos más adelante."""
    config = _config(tmp_path)
    ajeno = tmp_path / "datos" / "crudos" / "hogares" / "ajeno.csv"
    for otro in ajeno.parent.glob("*.csv"):
        otro.unlink()
    ajeno.write_text(crudo_sintetico(dias=3), encoding="utf-8")

    with pytest.raises((FormatoNoReconocido, ContratoIncumplido)):
        leer_eventos(config)


# --- Mapeo de actividades y protocolo del piloto ------------------------------


def test_el_mapeo_agrupa_variantes_antes_de_excluir(tmp_path):
    """`excluidas` se declara sobre las clases que el modelo verá, no sobre
    las etiquetas originales."""
    config = _config(tmp_path, ajustes_actividades={"mapeo": {"Sleep": "Descanso"}})
    caracteristicas = D.construir_caracteristicas(leer_eventos(config), config)
    clases = set(caracteristicas[config.datos.columna_objetivo])

    assert "Descanso" in clases and "Sleep" not in clases

    config = _config(
        tmp_path / "excluyendo",
        ajustes_actividades={"mapeo": {"Sleep": "Descanso"}, "excluidas": ["Descanso"]},
    )
    caracteristicas = D.construir_caracteristicas(leer_eventos(config), config)
    clases = set(caracteristicas[config.datos.columna_objetivo])

    assert "Descanso" not in clases and "Sleep" not in clases


def test_el_protocolo_del_piloto_multihogar():
    """Protocolo declarado para el piloto de nueve viviendas. Cambiarlo obliga
    a tocar también esta prueba: deja un segundo rastro en git."""
    config = cargar_configuracion(RAIZ / "config.hogares.yaml")

    assert config.datos.formato == "casas_csv"
    assert [s.nombre for s in config.equidad.subgrupos][0] == "hogar"
    assert len(config.equidad.subgrupos[0].categorias) == 9
    assert config.equidad.soporte_minimo == 30
    assert set(config.equidad.umbrales) == {
        "true_positive_rate_difference",
        "false_positive_rate_difference",
    }
    # El expediente de este piloto no puede pisar el de Aruba (D49).
    assert config.rutas.artefactos.name == "hogares"
    assert config.datos.actividades.mapeo
