"""Consolidación del reporte de explicabilidad (Principio 1)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.explicabilidad.atribucion_global import ExplicacionGlobal
    from src.explicabilidad.atribucion_local import ExplicacionLocal


def generar_reporte_explicabilidad(
    global_: "ExplicacionGlobal",
    ejemplos_locales: "list[ExplicacionLocal]",
    config: "Configuracion",
) -> Path:
    """Genera el reporte de explicabilidad en Markdown a partir de la
    plantilla `plantillas/reporte_explicabilidad.md`.

    Incluye: método SHAP usado, importancia global, figuras, y un puñado de
    ejemplos locales representativos (correctos e incorrectos).

    Returns:
        Ruta del reporte escrito bajo `config.rutas.artefactos`.

    TODO: rellenar la plantilla y escribir el archivo.
    """
    raise NotImplementedError
