"""Generación de los artefactos documentales del expediente de evidencia.

Produce artefactos legibles por un auditor y un manifiesto que permite
reproducir y verificar la ejecución bit a bit. Cada generador se invoca desde
el paso del procedimiento (Tabla 9) que lo tiene como producto:

    paso 1 -> generar_ficha_caracterizacion
    paso 2 -> generar_datasheet
    paso 3 -> generar_protocolo_evaluacion
    paso 5 -> generar_model_card, generar_reporte_cumplimiento
    paso 6 -> generar_bitacora_ejecucion, generar_manifiesto
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.procedimiento.pasos import ContextoEjecucion


def generar_ficha_caracterizacion(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/ficha_caracterizacion.md` (producto del paso 1).

    Describe el sistema evaluado, su finalidad, su población destinataria y
    la configuración de sensores empleada. Es el insumo de caracterización
    que la función MAPEAR del NIST AI RMF exige antes de medir nada.

    TODO: sustituir marcadores desde `config` y `ctx.modelo`; escribir en
        `config.rutas.ficha_caracterizacion`.
    """
    raise NotImplementedError


def generar_protocolo_evaluacion(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/protocolo_evaluacion.md` (producto del paso 3).

    Deja constancia de los subgrupos de comparación, las métricas de equidad
    y los umbrales de referencia declarados ANTES de ejecutar las pruebas,
    junto con el hash del `config.yaml` que los contiene.

    Ese hash es el control metodológico: sin él, la afirmación de que los
    umbrales no se ajustaron a los resultados no es verificable por un
    auditor externo.

    TODO: sustituir marcadores desde `config.equidad`; calcular el hash del
        config y devolverlo en `ctx.hash_protocolo`; escribir en
        `config.rutas.protocolo_evaluacion`.
    """
    raise NotImplementedError


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
