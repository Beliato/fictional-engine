"""Consolidación del reporte de equidad (Principio 2)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.equidad.desempeno_desagregado import DesempenoSubgrupo
    from src.equidad.metricas_equidad import VeredictoEquidad


def generar_reporte_equidad(
    desempeno: "list[DesempenoSubgrupo]",
    veredicto: "VeredictoEquidad",
    config: "Configuracion",
) -> Path:
    """Genera el reporte de equidad en Markdown desde
    `plantillas/reporte_equidad.md`.

    Incluye: subgrupos evaluados, umbrales PRE-DECLARADOS (citando que fueron
    fijados antes de ejecutar), tabla de desempeño desagregado, tabla de
    métricas de equidad observadas vs umbral, y el veredicto final con las
    métricas incumplidas si las hay.

    Returns:
        Ruta del reporte escrito bajo `config.rutas.artefactos`.

    TODO: rellenar la plantilla y escribir el archivo.
    """
    raise NotImplementedError
