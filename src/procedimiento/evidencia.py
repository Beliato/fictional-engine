"""Generación de la evidencia auditable (paso 6).

Produce artefactos legibles por un auditor y un manifiesto que permite
reproducir y verificar la ejecución bit a bit.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.procedimiento.pasos import ContextoEjecucion


def generar_model_card(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/model_card.md` con los datos de la ejecución.

    TODO: sustituir marcadores de la plantilla (modelo, datos, métricas,
        limitaciones, veredicto de equidad) y escribir en
        `config.rutas.model_card`.
    """
    raise NotImplementedError


def generar_datasheet(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/datasheet.md` (procedencia y composición de CASAS).

    TODO: implementar.
    """
    raise NotImplementedError


def generar_reporte_cumplimiento(ctx: "ContextoEjecucion") -> Path:
    """Genera el reporte de cumplimiento consolidado (3 principios + mapeo
    normativo ENIA-CR / AI Act EU / NIST AI RMF) desde
    `plantillas/reporte_cumplimiento.md`.

    TODO: agregar los reportes por principio y el veredicto global.
    """
    raise NotImplementedError


def generar_bitacora_ejecucion(ctx: "ContextoEjecucion") -> Path:
    """Escribe la bitácora de ejecución (qué paso corrió, cuándo, con qué
    entradas/salidas y hashes) como Markdown + JSON.

    TODO: serializar `ctx.eventos`.
    """
    raise NotImplementedError


def generar_manifiesto(ctx: "ContextoEjecucion") -> Path:
    """Emite `config.rutas.manifiesto`: JSON determinista con

        - id y marcas temporales de la ejecución,
        - instantánea del entorno (`src.comun.semillas.instantanea_entorno`),
        - `config.yaml` crudo usado,
        - hash de datos crudos, características, modelo,
        - hash de cada artefacto generado,
        - veredicto de equidad y estado de verificación de la bitácora.

    Es la pieza que hace la ejecución "auditable" y reproducible.

    TODO: recopilar todo lo anterior y escribir con
        `src.comun.utilidades.escribir_json`.
    """
    raise NotImplementedError
