"""Carga y validación de la configuración central (`config.yaml`).

Principio: sin estado oculto. Toda la parametrización vive en `config.yaml`.
El cargador convierte ese YAML en dataclasses inmutables y falla de forma
explícita si falta una clave obligatoria o si un valor es incoherente.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


# --- Estructura tipada de la configuración -----------------------------------
# Las dataclasses son `frozen=True` para impedir mutaciones en tiempo de
# ejecución (el estado de configuración no debe cambiar tras la carga).


@dataclass(frozen=True)
class ParticionDatos:
    test_size: float
    estratificar: bool


@dataclass(frozen=True)
class ConfigDatos:
    fuente: str
    archivo_crudo: Path
    columna_objetivo: str
    columnas_sensor_pir: tuple[str, ...]
    particion: ParticionDatos


@dataclass(frozen=True)
class ConfigModelo:
    tipo: str
    version: str
    hiperparametros: dict[str, Any]


@dataclass(frozen=True)
class ConfigExplicabilidad:
    explainer: str
    muestras_globales: int
    guardar_local_por_inferencia: bool


@dataclass(frozen=True)
class Subgrupo:
    nombre: str
    columna: str
    categorias: tuple[str, ...]


@dataclass(frozen=True)
class ConfigEquidad:
    subgrupos: tuple[Subgrupo, ...]
    umbrales: dict[str, float]


@dataclass(frozen=True)
class ConfigTrazabilidad:
    version_esquema: str
    formato: str
    responsable_por_defecto: str


@dataclass(frozen=True)
class Rutas:
    datos_crudos: Path
    datos_intermedios: Path
    artefactos: Path
    plantillas: Path
    registro_inferencias: Path
    manifiesto: Path
    model_card: Path
    reporte_cumplimiento: Path


@dataclass(frozen=True)
class Configuracion:
    """Configuración completa y validada del marco."""

    version_marco: str
    semilla: int
    pythonhashseed: int
    n_jobs: int
    rutas: Rutas
    datos: ConfigDatos
    modelo: ConfigModelo
    explicabilidad: ConfigExplicabilidad
    equidad: ConfigEquidad
    trazabilidad: ConfigTrazabilidad
    articulacion_normativa: dict[str, dict[str, str]]
    # Copia cruda del YAML, útil para volcarla en el manifiesto de evidencia.
    crudo: dict[str, Any]


# --- API pública ------------------------------------------------------------


def cargar_configuracion(ruta: str | Path = "config.yaml") -> Configuracion:
    """Lee y valida `config.yaml`, devolviendo una `Configuracion` inmutable.

    Args:
        ruta: ubicación del archivo YAML de configuración.

    Returns:
        La configuración validada.

    Raises:
        FileNotFoundError: si `ruta` no existe.
        ConfiguracionInvalida: si falta una clave obligatoria o un valor es
            incoherente (p. ej. `test_size` fuera de (0, 1), umbral negativo,
            subgrupo sin columna).

    TODO:
        - Cargar el YAML con `yaml.safe_load`.
        - Mapear cada bloque a su dataclass.
        - Validar: rangos numéricos, rutas relativas, coherencia semilla vs
          `random_state` de los hiperparámetros, existencia de todos los
          umbrales esperados por `equidad`.
        - Resolver las rutas relativas respecto a la raíz del repo.
    """
    raise NotImplementedError("TODO: implementar carga y validación de config.yaml")


def verificar_coherencia_semillas(config: Configuracion) -> None:
    """Comprueba que la semilla global coincide con todos los `random_state`
    declarados en la configuración (modelo, partición, etc.).

    Raises:
        ConfiguracionInvalida: si hay una discrepancia.

    TODO: recorrer `config.modelo.hiperparametros` y demás lugares con
        `random_state` / `random_seed` y exigir igualdad con `config.semilla`.
    """
    raise NotImplementedError


class ConfiguracionInvalida(ValueError):
    """La configuración existe pero es incompleta o incoherente."""
