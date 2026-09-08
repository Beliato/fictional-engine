"""Carga, validación y partición determinista del dataset CASAS.

El dataset CASAS son eventos de sensores de monitoreo domiciliario en formato
tabular. Este módulo no descarga datos: espera el archivo crudo en la ruta
declarada en `config.yaml` (`datos.archivo_crudo`) y documenta su procedencia
en el datasheet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from src.comun.configuracion import Configuracion


@dataclass(frozen=True)
class ParticionSupervisada:
    """Resultado de la partición train/test, con las columnas sensibles
    conservadas por separado para el análisis de equidad."""

    X_entrenamiento: "pd.DataFrame"
    X_prueba: "pd.DataFrame"
    y_entrenamiento: "pd.Series"
    y_prueba: "pd.Series"
    sensibles_entrenamiento: "pd.DataFrame"
    sensibles_prueba: "pd.DataFrame"


def cargar_crudo(config: "Configuracion") -> "pd.DataFrame":
    """Carga el CSV crudo de CASAS sin transformarlo.

    Args:
        config: configuración del marco.

    Returns:
        DataFrame con los eventos tal cual vienen del archivo.

    Raises:
        FileNotFoundError: si no existe `config.datos.archivo_crudo`.

    TODO: leer con `pandas.read_csv`, dtypes explícitos, sin inferencia
        silenciosa; registrar nº de filas y hash del archivo.
    """
    raise NotImplementedError


def validar_esquema(df: "pd.DataFrame", config: "Configuracion") -> None:
    """Valida que el DataFrame crudo tiene el esquema esperado.

    Comprobaciones: presencia de `columna_objetivo` y de las
    `columnas_sensor_pir`, ausencia de nulos en columnas críticas, tipos
    coherentes, rango temporal plausible.

    Raises:
        EsquemaDatosInvalido: si alguna comprobación falla.

    TODO: implementar las comprobaciones anteriores.
    """
    raise NotImplementedError


def construir_caracteristicas(
    df: "pd.DataFrame", config: "Configuracion"
) -> "pd.DataFrame":
    """Deriva las características de modelado a partir de los eventos crudos.

    Incluye la derivación de columnas usadas como subgrupos de equidad
    (p. ej. `franja_horaria` a partir de la marca temporal).

    Returns:
        DataFrame de características listo para particionar. Se persiste en
        `datos/intermedios/` para inspección.

    TODO: definir el conjunto de características; documentarlo en el datasheet.
    """
    raise NotImplementedError


def particionar(
    df: "pd.DataFrame", config: "Configuracion"
) -> ParticionSupervisada:
    """Realiza la partición train/test de forma determinista.

    Usa `config.semilla`, `config.datos.particion.test_size` y
    `estratificar`. Separa las columnas sensibles (las referenciadas por
    `config.equidad.subgrupos`) para el análisis desagregado.

    TODO: usar `sklearn.model_selection.train_test_split` con `random_state`
        = `config.semilla`.
    """
    raise NotImplementedError


def hash_dataframe(df: "pd.DataFrame") -> str:
    """Devuelve un hash estable (SHA-256) del contenido de un DataFrame.

    Se usa para sellar la versión de los datos en el manifiesto de evidencia.

    TODO: serializar de forma canónica (orden de filas/columnas fijo) antes
        de hashear.
    """
    raise NotImplementedError


class EsquemaDatosInvalido(ValueError):
    """El dataset crudo no cumple el esquema esperado."""
