"""Pruebas de carga y validación de `config.yaml`."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from src.comun.configuracion import (
    ConfiguracionInvalida,
    cargar_configuracion,
    verificar_coherencia_semillas,
)

RAIZ = Path(__file__).resolve().parents[1]


def _config_valida() -> dict:
    """El YAML real del repo, como dict mutable para derivar casos inválidos."""
    return yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))


def _escribir(tmp_path: Path, crudo: dict) -> Path:
    ruta = tmp_path / "config.yaml"
    ruta.write_text(yaml.safe_dump(crudo, allow_unicode=True), encoding="utf-8")
    return ruta


# --- Carga del config real ---------------------------------------------------


def test_carga_config_real_del_repo(ruta_config):
    """`cargar_configuracion(config.yaml)` devuelve una `Configuracion`."""
    config = cargar_configuracion(ruta_config)

    assert config.version_marco == "0.1.0"
    assert config.semilla == 42
    assert config.n_jobs == 1
    assert config.modelo.tipo == "RandomForestClassifier"
    assert config.trazabilidad.formato == "jsonl"


def test_rutas_se_resuelven_contra_la_raiz_del_repo(ruta_config):
    """Las rutas quedan absolutas y colgando de la raíz, no del cwd."""
    config = cargar_configuracion(ruta_config)

    assert config.rutas.manifiesto.is_absolute()
    assert config.rutas.manifiesto == RAIZ / "artefactos" / "manifiesto.json"
    assert config.datos.archivo_crudo == RAIZ / "datos" / "crudos" / "casas.csv"


def test_carga_no_depende_del_directorio_de_trabajo(ruta_config, tmp_path, monkeypatch):
    """Invocar desde otro cwd produce exactamente la misma configuración."""
    desde_raiz = cargar_configuracion(ruta_config)
    monkeypatch.chdir(tmp_path)
    desde_otro_lado = cargar_configuracion(ruta_config)

    assert desde_otro_lado == desde_raiz


def test_la_configuracion_es_inmutable(config):
    """`frozen=True`: nadie puede reescribir un umbral en tiempo de ejecución."""
    with pytest.raises(Exception):
        config.semilla = 7  # type: ignore[misc]


def test_articulacion_normativa_cubre_los_tres_principios(config):
    """Cada principio declara su correspondencia ENIA / AI Act / NIST."""
    assert set(config.articulacion_normativa) == {
        "explicabilidad",
        "equidad",
        "trazabilidad",
    }
    for principio, mapeo in config.articulacion_normativa.items():
        assert {"enia_cr", "ai_act_eu", "nist_ai_rmf"} <= mapeo.keys(), principio


# --- Ausencia de defaults silenciosos ----------------------------------------


def test_falla_si_falta_una_clave_obligatoria(tmp_path):
    """Un YAML incompleto lanza `ConfiguracionInvalida`, no usa defaults."""
    crudo = _config_valida()
    del crudo["semilla"]

    with pytest.raises(ConfiguracionInvalida, match="semilla"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_falla_si_falta_una_clave_anidada(tmp_path):
    """La exigencia llega hasta los bloques internos."""
    crudo = _config_valida()
    del crudo["equidad"]["umbrales"]

    with pytest.raises(ConfiguracionInvalida, match="equidad"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_falla_ante_una_clave_desconocida(tmp_path):
    """Un umbral mal escrito no debe desaparecer en silencio."""
    crudo = _config_valida()
    crudo["equidad"]["umbrales_"] = {}

    with pytest.raises(ConfiguracionInvalida, match="umbrales_"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_falla_si_el_archivo_no_existe(tmp_path):
    with pytest.raises(FileNotFoundError):
        cargar_configuracion(tmp_path / "no_existe.yaml")


def test_falla_ante_yaml_mal_formado(tmp_path):
    ruta = tmp_path / "config.yaml"
    ruta.write_text("semilla: [42\n", encoding="utf-8")

    with pytest.raises(ConfiguracionInvalida, match="YAML"):
        cargar_configuracion(ruta)


# --- Validación de valores ---------------------------------------------------


@pytest.mark.parametrize("valor", [0.0, 1.0, -0.1, 1.5])
def test_test_size_fuera_de_rango(tmp_path, valor):
    """`test_size` debe estar en (0, 1), extremos excluidos."""
    crudo = _config_valida()
    crudo["datos"]["particion"]["test_size"] = valor

    with pytest.raises(ConfiguracionInvalida, match="test_size"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_umbrales_equidad_presentes_y_no_negativos(config):
    """Todos los umbrales esperados existen y son >= 0."""
    assert config.equidad.umbrales
    for nombre, valor in config.equidad.umbrales.items():
        assert valor >= 0, nombre
        if nombre.endswith("_min"):
            assert 0 < valor <= 1, nombre
        else:
            assert valor <= 1, nombre


@pytest.mark.parametrize(
    ("clave", "valor"),
    [
        ("demographic_parity_difference", -0.01),
        ("demographic_parity_difference", 1.5),
        ("selection_rate_ratio_min", 0.0),
        ("selection_rate_ratio_min", 1.2),
    ],
)
def test_umbral_fuera_de_rango(tmp_path, clave, valor):
    """Las diferencias van en [0, 1]; los cocientes `_min`, en (0, 1]."""
    crudo = _config_valida()
    crudo["equidad"]["umbrales"][clave] = valor

    with pytest.raises(ConfiguracionInvalida, match=clave):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_falla_sin_subgrupos(tmp_path):
    """Sin subgrupos no hay evaluación desagregada (R4.1)."""
    crudo = _config_valida()
    crudo["equidad"]["subgrupos"] = []

    with pytest.raises(ConfiguracionInvalida, match="subgrupo"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_falla_con_subgrupos_de_nombre_duplicado(tmp_path):
    """Dos subgrupos homónimos harían ilegible el reporte de equidad."""
    crudo = _config_valida()
    primero = crudo["equidad"]["subgrupos"][0]
    crudo["equidad"]["subgrupos"].append(dict(primero))

    with pytest.raises(ConfiguracionInvalida, match="duplicado"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_rechaza_rutas_absolutas(tmp_path):
    """Una ruta absoluta ataría la configuración a una máquina concreta."""
    crudo = _config_valida()
    crudo["rutas"]["artefactos"] = str(tmp_path / "artefactos")

    with pytest.raises(ConfiguracionInvalida, match="relativa"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_booleano_no_pasa_por_numero(tmp_path):
    """`n_jobs: true` no debe colarse como 1: bool es subclase de int."""
    crudo = _config_valida()
    crudo["determinismo"]["n_jobs"] = True

    with pytest.raises(ConfiguracionInvalida, match="n_jobs"):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_columnas_sensor_pir_puede_venir_vacia(ruta_config):
    """Solo se puede completar tras inspeccionar CASAS; exigirla es prematuro.

    Quien consuma los datos debe exigirla no vacía. El cargador, no.
    """
    config = cargar_configuracion(ruta_config)

    assert config.datos.columnas_sensor_pir == ()


# --- Coherencia de semillas --------------------------------------------------


def test_semilla_coincide_con_random_state_del_modelo(config):
    """`verificar_coherencia_semillas` no lanza para el config del repo."""
    verificar_coherencia_semillas(config)


def test_detecta_random_state_divergente(tmp_path):
    """Una semilla divergente no rompe nada: solo mata la reproducibilidad."""
    crudo = _config_valida()
    crudo["modelo"]["hiperparametros"]["random_state"] = 7

    config = cargar_configuracion(_escribir(tmp_path, crudo))
    with pytest.raises(ConfiguracionInvalida, match="random_state"):
        verificar_coherencia_semillas(config)


def test_detecta_pythonhashseed_divergente(tmp_path):
    crudo = _config_valida()
    crudo["determinismo"]["pythonhashseed"] = 7

    config = cargar_configuracion(_escribir(tmp_path, crudo))
    with pytest.raises(ConfiguracionInvalida, match="pythonhashseed"):
        verificar_coherencia_semillas(config)


# --- Mensajes de error -------------------------------------------------------


def test_el_error_nombra_la_clave_con_notacion_de_punto(tmp_path):
    """Quien lea el error tiene que poder abrir el YAML e ir directo."""
    crudo = _config_valida()
    crudo["explicabilidad"]["muestras_globales"] = 0

    with pytest.raises(
        ConfiguracionInvalida, match=r"explicabilidad\.muestras_globales"
    ):
        cargar_configuracion(_escribir(tmp_path, crudo))


def test_yaml_que_no_es_un_mapa(tmp_path):
    ruta = tmp_path / "config.yaml"
    ruta.write_text(textwrap.dedent("- uno\n- dos\n"), encoding="utf-8")

    with pytest.raises(ConfiguracionInvalida, match="bloque de claves"):
        cargar_configuracion(ruta)
