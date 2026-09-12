"""Atribución global (R3.2): qué características impulsan al modelo en conjunto.

La Tabla 6 la define como la "agregación de las atribuciones locales sobre el
conjunto de evaluación; ordenamiento de variables por contribución media
absoluta". Se implementa literalmente: la importancia global es la media de
|contribución| sobre **todas** las explicaciones locales ya calculadas. No hay
un segundo cálculo SHAP, así que local y global son coherentes por
construcción y el costo de la atribución no se paga dos veces.

Figuras
-------
Siguen el método de visualización del proyecto: una sola serie en un solo
color y sin leyenda (el título dice qué se grafica), barras de 24 px como
máximo con el extremo de dato redondeado y cuadrado en la base, grilla y ejes
en línea fina recesiva, y texto en tinta, nunca en el color de la serie. La
tabla de valores acompaña a cada figura en el reporte como su equivalente
accesible.

Tamaño, DPI y metadatos fijos, y la API orientada a objetos de matplotlib en
lugar de `pyplot`, que tiene estado global: dos corridas equivalentes
producen PNG idénticos byte a byte, y el manifiesto los puede hashear.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from matplotlib.path import Path as Trazo
from matplotlib.ticker import FuncFormatter

from src.comun.utilidades import asegurar_directorio, escribir_json
from src.explicabilidad.lenguaje import (
    etiqueta_caracteristica,
    formatear_decimal,
    formatear_miles,
)

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.explicabilidad.atribucion_local import ExplicacionLocal

# Paleta de referencia del método de visualización, modo claro. Es
# presentación, no un parámetro de evaluación: cambiarla no altera ningún
# resultado, solo su aspecto.
_SUPERFICIE = "#fcfcfb"
_SERIE = "#2a78d6"
_TINTA = "#0b0b0b"
_TINTA_SECUNDARIA = "#52514e"
_TINTA_TENUE = "#898781"
_GRILLA = "#e1e0d9"
_EJE = "#c3c2b7"

_DPI = 150
_ANCHO = 8.0  # pulgadas
_BANDA = 0.28  # pulgadas por barra: 42 px a 150 DPI
_FRACCION_BARRA = 0.5  # la barra ocupa media banda: 21 px, dentro del tope de 24
_RADIO_PX = 4  # extremo de dato redondeado
# Sin versión de software en el PNG: los bytes no cambian con un parche de
# matplotlib que no altera el dibujo.
_METADATOS_PNG = {"Software": None}


@dataclass(frozen=True)
class ExplicacionGlobal:
    """Importancia global: media de |contribución| por característica."""

    importancia_media_abs: dict[str, float]  # ordenada de mayor a menor
    n_explicaciones: int
    ruta_tabla: Path
    ruta_figura_resumen: Path
    rutas_dependencias: dict[str, Path]

    def top(self, k: int) -> list[str]:
        """Las `k` características de mayor importancia, en orden."""
        return list(self.importancia_media_abs)[:k]


def muestrear_para_graficos(
    explicaciones: "list[ExplicacionLocal]", config: "Configuracion"
) -> "list[ExplicacionLocal]":
    """Submuestra determinista para los gráficos de dependencia.

    Toma hasta `config.explicabilidad.muestras_graficos` explicaciones con la
    semilla del marco y conserva su orden original. Solo afecta a lo que se
    dibuja: la importancia global usa todas.
    """
    n = min(config.explicabilidad.muestras_graficos, len(explicaciones))
    if n == len(explicaciones):
        return list(explicaciones)
    rng = np.random.default_rng(config.semilla)
    indices = np.sort(rng.choice(len(explicaciones), size=n, replace=False))
    return [explicaciones[i] for i in indices]


def calcular_importancia_global(
    explicaciones: "list[ExplicacionLocal]", config: "Configuracion"
) -> ExplicacionGlobal:
    """Agrega las explicaciones locales y escribe tabla y figuras.

    Artefactos, bajo `config.rutas.artefactos/explicaciones/global/`:
        - `importancia_global.json`: la tabla, en orden de importancia.
        - `importancia_global.png`: barras horizontales ordenadas.
        - `dependencia_<caracteristica>.png`: una por cada característica
          destacada (`config.explicabilidad.caracteristicas_destacadas`).

    Raises:
        ValueError: si no hay explicaciones o no explican las mismas
            características.
    """
    if not explicaciones:
        raise ValueError("no hay explicaciones locales que agregar")
    columnas = list(explicaciones[0].contribuciones)
    for explicacion in explicaciones:
        if list(explicacion.contribuciones) != columnas:
            raise ValueError(
                f"la explicación {explicacion.id_evento!r} no atribuye las "
                "mismas características que las demás"
            )

    matriz = np.array(
        [[e.contribuciones[c] for c in columnas] for e in explicaciones]
    )
    medias = np.abs(matriz).mean(axis=0)
    ordenadas = sorted(
        zip(columnas, map(float, medias)), key=lambda kv: (-kv[1], kv[0])
    )
    importancia = dict(ordenadas)

    destino = asegurar_directorio(
        Path(config.rutas.artefactos) / "explicaciones" / "global"
    )
    ruta_tabla = destino / "importancia_global.json"
    escribir_json(
        ruta_tabla,
        {
            "n_explicaciones": len(explicaciones),
            "medida": (
                "media de |contribución SHAP| a la probabilidad de la clase "
                "predicha"
            ),
            "importancia": [
                {"caracteristica": c, "importancia_media_abs": v}
                for c, v in ordenadas
            ],
        },
    )

    k = config.explicabilidad.caracteristicas_destacadas
    ruta_resumen = destino / "importancia_global.png"
    nombres_zona = config.datos.nombres_zona
    _dibujar_importancia(
        importancia, len(explicaciones), k, ruta_resumen, nombres_zona
    )

    muestra = muestrear_para_graficos(explicaciones, config)
    rutas_dependencias: dict[str, Path] = {}
    for caracteristica in list(importancia)[:k]:
        ruta = destino / f"dependencia_{caracteristica}.png"
        _dibujar_dependencia(caracteristica, muestra, ruta, nombres_zona)
        rutas_dependencias[caracteristica] = ruta

    return ExplicacionGlobal(
        importancia_media_abs=importancia,
        n_explicaciones=len(explicaciones),
        ruta_tabla=ruta_tabla,
        ruta_figura_resumen=ruta_resumen,
        rutas_dependencias=rutas_dependencias,
    )


# --- Dibujo ------------------------------------------------------------------


def _pt(px: float) -> float:
    """Píxeles a puntos tipográficos, que es la unidad de matplotlib."""
    return px * 72 / _DPI


def _barra(ancho: float, y_centro: float, alto: float, rx: float, ry: float):
    """Barra horizontal con el extremo de dato redondeado y la base cuadrada.

    `rx` y `ry` son el radio de 4 px expresado en unidades de datos de cada
    eje, que tienen escalas distintas.
    """
    if ancho <= 0:
        return None
    y0, y1 = y_centro - alto / 2, y_centro + alto / 2
    rx, ry = min(rx, ancho), min(ry, alto / 2)
    vertices = [
        (0, y0),
        (ancho - rx, y0),
        (ancho, y0),
        (ancho, y0 + ry),
        (ancho, y1 - ry),
        (ancho, y1),
        (ancho - rx, y1),
        (0, y1),
        (0, y0),
    ]
    codigos = [
        Trazo.MOVETO,
        Trazo.LINETO,
        Trazo.CURVE3,
        Trazo.CURVE3,
        Trazo.LINETO,
        Trazo.CURVE3,
        Trazo.CURVE3,
        Trazo.LINETO,
        Trazo.CLOSEPOLY,
    ]
    return PathPatch(
        Trazo(vertices, codigos), facecolor=_SERIE, edgecolor="none", linewidth=0
    )


def _figura(alto: float) -> Figure:
    figura = Figure(figsize=(_ANCHO, alto), dpi=_DPI, facecolor=_SUPERFICIE)
    FigureCanvasAgg(figura)
    return figura


def _titulos(figura: Figure, alto: float, titulo: str, subtitulo: str) -> None:
    izquierda = 0.2 / _ANCHO
    figura.text(
        izquierda, 1 - 0.22 / alto, titulo,
        color=_TINTA, fontsize=12, fontweight="bold", ha="left", va="top",
    )
    figura.text(
        izquierda, 1 - 0.48 / alto, subtitulo,
        color=_TINTA_SECUNDARIA, fontsize=8.5, ha="left", va="top",
    )


def _estilo_ejes(ejes, grilla: str) -> None:
    ejes.set_facecolor(_SUPERFICIE)
    for lado in ("top", "right"):
        ejes.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ejes.spines[lado].set_color(_EJE)
        ejes.spines[lado].set_linewidth(_pt(1))
    ejes.grid(True, axis=grilla, color=_GRILLA, linewidth=_pt(1), linestyle="solid")
    ejes.set_axisbelow(True)
    ejes.tick_params(colors=_TINTA_TENUE, labelsize=8, length=0)


def _dibujar_importancia(
    importancia: dict[str, float],
    n: int,
    destacadas: int,
    ruta: Path,
    nombres_zona: "dict[str, str] | None" = None,
) -> None:
    nombres = list(importancia)
    valores = np.array(list(importancia.values()))
    n_barras = len(nombres)

    margen_izq, margen_der, margen_abajo, margen_arriba = 2.3, 0.55, 0.55, 0.8
    alto = margen_arriba + margen_abajo + n_barras * _BANDA
    figura = _figura(alto)
    ancho_ejes = _ANCHO - margen_izq - margen_der
    alto_ejes = alto - margen_arriba - margen_abajo
    ejes = figura.add_axes(
        [margen_izq / _ANCHO, margen_abajo / alto, ancho_ejes / _ANCHO, alto_ejes / alto]
    )
    _estilo_ejes(ejes, grilla="x")
    ejes.spines["bottom"].set_visible(False)

    x_max = float(valores.max()) * 1.2 if valores.max() > 0 else 1.0
    ejes.set_xlim(0, x_max)
    ejes.set_ylim(-0.5, n_barras - 0.5)
    # Radio de 4 px y separación de etiquetas en unidades de cada eje.
    rx = _RADIO_PX * x_max / (ancho_ejes * _DPI)
    ry = _RADIO_PX * n_barras / (alto_ejes * _DPI)
    separacion = 6 * x_max / (ancho_ejes * _DPI)

    for i, valor in enumerate(valores):
        y = n_barras - 1 - i  # la más importante arriba
        barra = _barra(float(valor), y, _FRACCION_BARRA, rx, ry)
        if barra is not None:
            ejes.add_patch(barra)
        # Etiqueta directa selectiva: solo las destacadas, al final de la barra.
        if i < destacadas:
            ejes.text(
                float(valor) + separacion, y, formatear_decimal(float(valor)),
                color=_TINTA_SECUNDARIA, fontsize=8, ha="left", va="center",
            )

    ejes.set_yticks(range(n_barras))
    ejes.set_yticklabels(
        [
            etiqueta_caracteristica(nombres[n_barras - 1 - y], nombres_zona)
            for y in range(n_barras)
        ]
    )
    ejes.tick_params(axis="y", colors=_TINTA_SECUNDARIA, labelsize=8.5)
    ejes.xaxis.set_major_formatter(FuncFormatter(lambda v, _: formatear_decimal(v, 2)))
    ejes.set_xlabel("Contribución media absoluta", color=_TINTA_TENUE, fontsize=8)

    _titulos(
        figura, alto,
        "Importancia global de las características",
        "Media de |contribución SHAP| a la probabilidad de la clase predicha · "
        f"{formatear_miles(n)} inferencias",
    )
    figura.savefig(ruta, dpi=_DPI, facecolor=_SUPERFICIE, metadata=_METADATOS_PNG)


def _dibujar_dependencia(
    caracteristica: str,
    muestra: "list[ExplicacionLocal]",
    ruta: Path,
    nombres_zona: "dict[str, str] | None" = None,
) -> None:
    x = np.array([e.valores[caracteristica] for e in muestra])
    y = np.array([e.contribuciones[caracteristica] for e in muestra])
    etiqueta = etiqueta_caracteristica(caracteristica, nombres_zona)

    alto = 4.6
    figura = _figura(alto)
    ejes = figura.add_axes([0.1, 0.12, 0.86, 0.68])
    _estilo_ejes(ejes, grilla="both")
    ejes.axhline(0, color=_EJE, linewidth=_pt(1), zorder=1)
    # Relleno de 8 px con anillo de 2 px del color de la superficie, para que
    # los puntos superpuestos sigan distinguiéndose. matplotlib centra el borde
    # sobre el contorno, así que el marcador nominal mide 10 px para que el
    # relleno visible no baje de 8. La transparencia deja ver dónde se
    # concentran los puntos cuando se superponen.
    ejes.scatter(
        x, y, s=_pt(10) ** 2, c=_SERIE, alpha=0.6,
        edgecolors=_SUPERFICIE, linewidths=_pt(2), zorder=2,
    )
    ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _: formatear_decimal(v, 2)))
    ejes.xaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
    )
    ejes.set_xlabel(etiqueta, color=_TINTA_TENUE, fontsize=8)
    ejes.set_ylabel("Contribución", color=_TINTA_TENUE, fontsize=8)

    _titulos(
        figura, alto,
        f"Cómo influye «{etiqueta}» en la decisión",
        "Cada punto es una inferencia · contribución a la probabilidad de la "
        f"clase predicha · muestra determinista de {formatear_miles(len(muestra))}",
    )
    figura.savefig(ruta, dpi=_DPI, facecolor=_SUPERFICIE, metadata=_METADATOS_PNG)
