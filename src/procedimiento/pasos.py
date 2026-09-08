"""Los 6 pasos del procedimiento de aplicación del marco (Tabla 9).

El procedimiento sigue las funciones del NIST AI RMF (NIST, 2023): la
caracterización inicial corresponde a MAPEAR, la ejecución de las pruebas
técnicas a MEDIR, y la consolidación documental a GOBERNAR y GESTIONAR.

Precondiciones vs. pasos
------------------------
La preparación de datos y el sellado del modelo NO son pasos del marco de
cumplimiento: son precondiciones. El marco recibe el sistema de IA como
entrada, y el modelo actúa como *sujeto de prueba, no como objeto de
optimización*. Por eso viven en `PRECONDICIONES` y no en `PASOS`.

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
    # Hash del `config.yaml` sellado en el paso 3. Es lo que permite demostrar
    # que los umbrales de equidad no se tocaron después de ver resultados.
    hash_protocolo: str | None = None
    veredicto_equidad: "VeredictoEquidad | None" = None
    artefactos: dict[str, Path] = field(default_factory=dict)
    eventos: list[dict[str, Any]] = field(default_factory=list)


# =============================================================================
# Precondiciones — no son pasos del marco (ver docstring del módulo)
# =============================================================================


def precondicion_preparar_datos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Carga y prepara el conjunto de datos que el sistema evaluado consume.

    Carga el crudo de CASAS, valida el esquema, construye características,
    particiona train/test de forma determinista y sella el hash de los datos.

    TODO: orquestar `src.comun.datos.{cargar_crudo, validar_esquema,
        construir_caracteristicas, particionar, hash_dataframe}`.
    """
    raise NotImplementedError


def precondicion_sellar_modelo(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Obtiene el modelo de referencia y lo sella para la auditoría.

    El modelo es el sujeto de prueba. Si ya viene dado, este paso lo carga y
    lo sella; si el caso de estudio exige producirlo, lo ajusta con los
    hiperparámetros y la semilla declarados en `config.modelo`. En ambos casos
    el producto es un `ModeloSellado` (estimador + versión + hash de
    parámetros + hash de datos + ruta serializada), y su desempeño NO se
    optimiza en función de los resultados de las pruebas posteriores.

    TODO: delegar en `src.comun.modelado.{cargar_sellado, entrenar}`.
    """
    raise NotImplementedError


PRECONDICIONES = (
    precondicion_preparar_datos,
    precondicion_sellar_modelo,
)


# =============================================================================
# Los 6 pasos del procedimiento (Tabla 9)
# =============================================================================


def paso_1_caracterizacion_sistema(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 1 — Caracterización del sistema.

    Actividad (Tabla 9): descripción del sistema, su finalidad, su población
    destinataria y la configuración de sensores empleada.
    Producto: ficha de caracterización.
    Función NIST AI RMF: MAPEAR.
    Requerimientos: insumo de R5.2 (propósito y condiciones de uso).

    TODO: rellenar `plantillas/ficha_caracterizacion.md` desde `config` y el
        `ModeloSellado`; delegar en
        `src.procedimiento.evidencia.generar_ficha_caracterizacion`.
    """
    raise NotImplementedError


def paso_2_documentacion_datos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 2 — Documentación del conjunto de datos.

    Actividad (Tabla 9): registro de procedencia, composición,
    representatividad de subgrupos y sesgos potenciales.
    Producto: datasheet del conjunto de datos.
    Función NIST AI RMF: MAPEAR.
    Requerimientos: R4.3.

    TODO: delegar en `src.procedimiento.evidencia.generar_datasheet`.
    """
    raise NotImplementedError


def paso_3_declaracion_criterios(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 3 — Declaración de criterios de evaluación.

    Actividad (Tabla 9): definición de los subgrupos de comparación, las
    métricas de equidad y los umbrales de referencia, ANTES de ejecutar las
    pruebas del paso 4.
    Producto: protocolo de evaluación declarado.
    Función NIST AI RMF: MAPEAR.
    Requerimientos: R4.2 (umbrales declarados previamente).

    Control metodológico: este paso sella el hash de `config.yaml` en
    `ctx.hash_protocolo`. El paso 6 lo vuelve a comprobar; si difiere, los
    criterios se alteraron después de ver resultados y la evidencia queda
    marcada como no válida.

    TODO: delegar en
        `src.procedimiento.evidencia.generar_protocolo_evaluacion`.
    """
    raise NotImplementedError


def paso_4_ejecucion_pruebas(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 4 — Ejecución de las pruebas técnicas.

    Actividad (Tabla 9): aplicación de los módulos de explicabilidad, equidad
    y verificación de registro sobre el modelo evaluado.
    Producto: resultados de las pruebas y bitácora.
    Función NIST AI RMF: MEDIR.
    Requerimientos: R3.1, R3.2, R3.3, R4.1, R4.2, R5.1.

    Sub-pruebas:
        - Explicabilidad: atribución local por inferencia (R3.1), agregación
          global sobre el conjunto de evaluación (R3.2) y traducción de las
          atribuciones dominantes a enunciados comprensibles (R3.3).
        - Equidad: desempeño desagregado por subgrupo (R4.1) y métricas de
          disparidad contra los umbrales sellados en el paso 3 (R4.2).
        - Trazabilidad: registro estructurado de cada inferencia en la
          bitácora JSONL, con referencia a su explicación local (R5.1), y
          verificación de integridad y cobertura del propio registro.

    Un veredicto de equidad negativo NO aborta el pipeline: es evidencia.

    TODO: delegar en `src.explicabilidad.*`, `src.equidad.*` y
        `src.trazabilidad.{registro, verificacion}`; guardar rutas de
        artefactos y `VeredictoEquidad` en el contexto.
    """
    raise NotImplementedError


def paso_5_generacion_artefactos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 5 — Generación de artefactos auditables.

    Actividad (Tabla 9): elaboración del reporte de explicabilidad, el reporte
    de equidad y el model card a partir de los resultados obtenidos.
    Producto: artefactos documentales.
    Función NIST AI RMF: GOBERNAR.
    Requerimientos: R5.2, y documentación de R3.1, R3.2, R3.3, R4.1 y R4.2.

    TODO: delegar en `src.explicabilidad.reporte`, `src.equidad.reporte` y
        `src.procedimiento.evidencia.{generar_model_card,
        generar_reporte_cumplimiento}`.
    """
    raise NotImplementedError


def paso_6_verificacion_auditabilidad(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 6 — Verificación de auditabilidad.

    Actividad (Tabla 9): comprobación de que los artefactos y la bitácora
    permiten reconstruir y atribuir las decisiones del sistema.
    Producto: expediente de evidencia verificable.
    Función NIST AI RMF: GESTIONAR.
    Requerimientos: R5.3.

    Comprobaciones:
        - cada inferencia de la bitácora se puede reconstruir ex post y
          atribuir a un responsable identificable (R5.3),
        - `ctx.hash_protocolo` sigue coincidiendo con el `config.yaml` usado
          (los criterios del paso 3 no se alteraron),
        - los nueve requerimientos de la matriz de mapeo tienen su artefacto
          asociado presente y con hash registrado.

    Cierra con la bitácora de ejecución y el manifiesto de hashes, que son lo
    que hace la corrida reproducible y comparable.

    TODO: delegar en `src.trazabilidad.verificacion` y
        `src.procedimiento.evidencia.{generar_bitacora_ejecucion,
        generar_manifiesto}`.
    """
    raise NotImplementedError


PASOS = (
    paso_1_caracterizacion_sistema,
    paso_2_documentacion_datos,
    paso_3_declaracion_criterios,
    paso_4_ejecucion_pruebas,
    paso_5_generacion_artefactos,
    paso_6_verificacion_auditabilidad,
)

_ = replace  # usado por los TODO de cada paso
