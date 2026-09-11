"""Desempeño del modelo desagregado por subgrupo (R4.1).

No emite veredicto: calcula y tabula métricas de desempeño estándar por cada
categoría de cada subgrupo declarado en `config.equidad.subgrupos`. El
veredicto lo emite `metricas_equidad`, contra umbrales pre-declarados.

Precisión, exhaustividad y F1 se promedian en macro sobre las actividades que
aparecen en las etiquetas reales de la categoría. Una actividad que no ocurre
en una franja no tiene exhaustividad que medir allí; contarla como cero
castigaría a la categoría por la composición de los datos (D45).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from src.comun.utilidades import asegurar_directorio
from src.equidad.entradas import categorias_de, validar_entradas

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion, Subgrupo

# Subdirectorio de `config.rutas.artefactos` con la evidencia de equidad.
DIRECTORIO = "equidad"
_ARCHIVO = "desempeno_desagregado.csv"


@dataclass(frozen=True)
class DesempenoSubgrupo:
    """Métricas de desempeño de una categoría de un subgrupo.

    Si la categoría está declarada pero no tiene ventanas en la prueba
    (`n == 0`), las métricas son None: no hay nada que medir, y un cero diría
    que se midió y salió mal.
    """

    subgrupo: str
    categoria: str
    n: int
    n_actividades: int
    accuracy: float | None
    precision_macro: float | None
    recall_macro: float | None
    f1_macro: float | None


def calcular_desempeno_desagregado(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    subgrupo: "Subgrupo",
) -> list[DesempenoSubgrupo]:
    """Una fila por cada categoría de `subgrupo`, en el orden declarado.

    Raises:
        EntradasDesalineadas: si etiquetas, predicciones y sensibles no
            describen las mismas ventanas.
        CategoriaNoDeclarada: si los datos traen una categoría no declarada.
    """
    validar_entradas(y_verdadero, y_predicho, sensibles, subgrupo)
    reales = y_verdadero.astype(str).to_numpy()
    predichas = y_predicho.astype(str).to_numpy()
    columna = sensibles[subgrupo.columna].astype(str)

    filas = []
    for categoria in categorias_de(subgrupo, columna):
        en_categoria = (columna == categoria).to_numpy()
        n = int(en_categoria.sum())
        if n == 0:
            filas.append(
                DesempenoSubgrupo(
                    subgrupo.nombre, categoria, 0, 0, None, None, None, None
                )
            )
            continue
        r, p = reales[en_categoria], predichas[en_categoria]
        actividades = sorted(set(r))
        precision, recall, f1, _ = precision_recall_fscore_support(
            r, p, labels=actividades, average="macro", zero_division=0.0
        )
        filas.append(
            DesempenoSubgrupo(
                subgrupo=subgrupo.nombre,
                categoria=categoria,
                n=n,
                n_actividades=len(actividades),
                accuracy=float(accuracy_score(r, p)),
                precision_macro=float(precision),
                recall_macro=float(recall),
                f1_macro=float(f1),
            )
        )
    return filas


def calcular_desempeno(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    config: "Configuracion",
) -> list[DesempenoSubgrupo]:
    """Desempeño desagregado de todos los subgrupos de `config.equidad`."""
    filas = []
    for subgrupo in config.equidad.subgrupos:
        filas += calcular_desempeno_desagregado(
            y_verdadero, y_predicho, sensibles, subgrupo
        )
    return filas


def guardar_desempeno(
    filas: list[DesempenoSubgrupo], config: "Configuracion"
) -> Path:
    """Escribe la tabla en `artefactos/equidad/desempeno_desagregado.csv`.

    Seis decimales fijos, UTF-8 y saltos de línea LF: dos corridas
    equivalentes producen el mismo archivo y el manifiesto puede hashearlo.
    """
    destino = Path(config.rutas.artefactos) / DIRECTORIO / _ARCHIVO
    asegurar_directorio(destino.parent)
    columnas = [campo.name for campo in dataclasses.fields(DesempenoSubgrupo)]
    tabla = pd.DataFrame([dataclasses.asdict(f) for f in filas], columns=columnas)
    tabla.to_csv(
        destino,
        index=False,
        float_format="%.6f",
        encoding="utf-8",
        lineterminator="\n",
    )
    return destino
