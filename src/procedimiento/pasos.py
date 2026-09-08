"""Los 6 pasos del marco, cada uno como función pura y auditable.

Cada paso:
    - recibe el `ContextoEjecucion` y devuelve un `ContextoEjecucion` nuevo
      (o el mismo enriquecido); no muta estado global,
    - registra su inicio/fin y los hashes de sus entradas y salidas,
    - escribe sus artefactos bajo `config.rutas.artefactos`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.comun.datos import ParticionSupervisada
    from src.comun.modelado import ModeloSellado
    from src.equidad.metricas_equidad import VeredictoEquidad


@dataclass(frozen=True)
class ContextoEjecucion:
    """Estado que fluye entre pasos. Inmutable: cada paso crea una copia
    actualizada con `dataclasses.replace`."""

    config: "Configuracion"
    id_ejecucion: str
    marca_inicio: str
    particion: "ParticionSupervisada | None" = None
    modelo: "ModeloSellado | None" = None
    hash_datos: str | None = None
    veredicto_equidad: "VeredictoEquidad | None" = None
    artefactos: dict[str, Path] = field(default_factory=dict)
    eventos: list[dict[str, Any]] = field(default_factory=list)


def paso_1_preparar_datos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 1 — Preparación de datos.

    Carga el crudo de CASAS, valida el esquema, construye características,
    particiona train/test de forma determinista y sella el hash de los datos.

    TODO: orquestar `src.comun.datos.{cargar_crudo, validar_esquema,
        construir_caracteristicas, particionar, hash_dataframe}`.
    """
    raise NotImplementedError


def paso_2_entrenar_modelo(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 2 — Entrenamiento del modelo.

    Entrena el clasificador con los hiperparámetros de `config.modelo` y lo
    sella (versión + hashes + serialización).

    TODO: delegar en `src.comun.modelado.entrenar`.
    """
    raise NotImplementedError


def paso_3_explicabilidad(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 3 — Explicabilidad (Principio 1).

    Construye el explainer SHAP, calcula atribución global sobre una muestra
    y atribución local para cada fila del set de prueba, y genera el reporte.

    TODO: delegar en `src.explicabilidad.*`; guardar rutas de artefactos en
        el contexto para enlazarlas desde la bitácora (paso 5).
    """
    raise NotImplementedError


def paso_4_equidad(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 4 — Equidad (Principio 2).

    Calcula desempeño desagregado y métricas de equidad por subgrupo, las
    contrasta con los umbrales PRE-DECLARADOS y emite el veredicto.

    TODO: delegar en `src.equidad.*`; almacenar `VeredictoEquidad` en el
        contexto. NO abortar el pipeline si falla: el fallo es evidencia.
    """
    raise NotImplementedError


def paso_5_trazabilidad(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 5 — Trazabilidad (Principio 3).

    Ejecuta la inferencia sobre el set de prueba registrando cada resultado
    en la bitácora JSONL (con referencia a su explicación local del paso 3),
    y luego verifica integridad y cobertura del registro.

    TODO: usar `src.trazabilidad.registro.RegistroEstructurado` y
        `src.trazabilidad.verificacion.*`.
    """
    raise NotImplementedError


def paso_6_evidencia(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 6 — Generación de evidencia auditable.

    Consolida model card, datasheet, reporte de cumplimiento y bitácora de
    ejecución, y emite el manifiesto con los hashes de todas las entradas y
    salidas y la instantánea del entorno.

    TODO: delegar en `src.procedimiento.evidencia.*`.
    """
    raise NotImplementedError


PASOS = (
    paso_1_preparar_datos,
    paso_2_entrenar_modelo,
    paso_3_explicabilidad,
    paso_4_equidad,
    paso_5_trazabilidad,
    paso_6_evidencia,
)

_ = replace  # usado por los TODO de cada paso
