"""Validación de las entradas comunes del análisis de equidad.

El desempeño desagregado y las métricas de equidad reciben lo mismo
—etiquetas reales, predicciones y columnas sensibles— y fallan igual ante lo
mismo. Un desalineo o una categoría no declarada no pueden traducirse en una
tabla con huecos: el reporte diría menos de lo que se midió sin decir por qué.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from src.comun.configuracion import Subgrupo


def validar_entradas(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    subgrupo: "Subgrupo",
) -> None:
    """Exige que las tres entradas describan las mismas ventanas, en el mismo
    orden, y que traigan la columna del subgrupo.

    Raises:
        EntradasDesalineadas: si no es así.
    """
    longitudes = (len(y_verdadero), len(y_predicho), len(sensibles))
    if len(set(longitudes)) != 1:
        raise EntradasDesalineadas(
            "etiquetas, predicciones y columnas sensibles deben tener la misma "
            f"longitud; se recibió {longitudes}"
        )
    if not (
        y_verdadero.index.equals(y_predicho.index)
        and y_verdadero.index.equals(sensibles.index)
    ):
        raise EntradasDesalineadas(
            "etiquetas, predicciones y columnas sensibles deben compartir el "
            "índice: con índices distintos, cada predicción se compararía con "
            "la etiqueta de otra ventana"
        )
    if subgrupo.columna not in sensibles.columns:
        raise EntradasDesalineadas(
            f"falta la columna {subgrupo.columna!r} del subgrupo "
            f"{subgrupo.nombre!r} entre las columnas sensibles"
        )


def categorias_de(subgrupo: "Subgrupo", valores: "pd.Series") -> tuple[str, ...]:
    """Categorías a comparar para `subgrupo`, dados sus `valores` como texto.

    Son las declaradas, en su orden. Si no se declaró ninguna, las presentes
    en los datos, ordenadas.

    Raises:
        CategoriaNoDeclarada: si los datos traen una categoría que la
            configuración no declara. Descartarla en silencio sacaría del
            análisis justo a quienes nadie previó.
    """
    presentes = sorted(set(valores))
    if not subgrupo.categorias:
        return tuple(presentes)
    sobrantes = sorted(set(presentes) - set(subgrupo.categorias))
    if sobrantes:
        raise CategoriaNoDeclarada(
            f"el subgrupo {subgrupo.nombre!r} trae categorías no declaradas en "
            f"equidad.subgrupos: {sobrantes}"
        )
    return subgrupo.categorias


class EntradasDesalineadas(ValueError):
    """Etiquetas, predicciones y columnas sensibles no describen lo mismo."""


class CategoriaNoDeclarada(ValueError):
    """Los datos traen una categoría de subgrupo que la configuración no declara."""
