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

from src.comun.datos import (
    cargar_crudo,
    construir_caracteristicas,
    hash_dataframe,
    particionar,
    validar_esquema,
)
from src.comun.modelado import entrenar
from src.comun.utilidades import ahora_utc_iso, hash_archivo
from src.procedimiento.evidencia import (
    generar_datasheet,
    generar_ficha_caracterizacion,
)

if TYPE_CHECKING:
    import pandas as pd

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
    # Cuadro de características completo, antes de partir: el datasheet
    # describe el dataset entero, no el conjunto de entrenamiento.
    caracteristicas: "pd.DataFrame | None" = None
    n_eventos_crudos: int | None = None
    hash_datos_crudos: str | None = None
    # Hash del cuadro de características (datos ya procesados).
    hash_datos: str | None = None
    # Hash del `config.yaml` sellado en el paso 3. Es lo que permite demostrar
    # que los umbrales de equidad no se tocaron después de ver resultados.
    hash_protocolo: str | None = None
    veredicto_equidad: "VeredictoEquidad | None" = None
    artefactos: dict[str, Path] = field(default_factory=dict)
    eventos: list[dict[str, Any]] = field(default_factory=list)


def nuevo_contexto(
    config: "Configuracion", id_ejecucion: str
) -> ContextoEjecucion:
    """Contexto inicial de una ejecución, con su marca de inicio en UTC."""
    return ContextoEjecucion(
        config=config, id_ejecucion=id_ejecucion, marca_inicio=ahora_utc_iso()
    )


def registrar_evento(
    ctx: ContextoEjecucion, paso: str, **detalle: Any
) -> ContextoEjecucion:
    """Añade un evento a la bitácora de ejecución del contexto.

    Es lo que después permite decir qué paso corrió, cuándo y con qué
    entradas y salidas. Se registra al terminar el paso: un evento anotado
    antes de hacer el trabajo afirmaría algo que todavía no ocurrió.
    """
    evento = {"paso": paso, "marca_temporal": ahora_utc_iso(), **detalle}
    return replace(ctx, eventos=[*ctx.eventos, evento])


def _registrar_artefacto(
    ctx: ContextoEjecucion, paso: str, nombre: str, ruta: Path
) -> ContextoEjecucion:
    """Guarda la ruta del artefacto producido y su hash en la bitácora."""
    ctx = replace(ctx, artefactos={**ctx.artefactos, nombre: ruta})
    return registrar_evento(
        ctx, paso, artefacto=nombre, ruta=str(ruta), hash=hash_archivo(ruta)
    )


# =============================================================================
# Precondiciones — no son pasos del marco (ver docstring del módulo)
# =============================================================================


def precondicion_preparar_datos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Carga y prepara el conjunto de datos que el sistema evaluado consume.

    Carga el crudo de CASAS, valida el esquema, construye características,
    particiona train/test de forma determinista y sella el hash de los datos.

    Sella dos hashes distintos: el del crudo tal como se leyó y el del cuadro
    de características. El datasheet declara ambos, así que un auditor puede
    comprobar por separado que los datos de origen y la preparación son los
    mismos que produjeron los resultados.

    Raises:
        EsquemaDatosInvalido: si el crudo no cumple el esquema declarado.
        FormatoNoReconocido: si `datos.formato` no tiene lector.
    """
    config = ctx.config
    eventos = cargar_crudo(config)
    validar_esquema(eventos, config)
    caracteristicas = construir_caracteristicas(eventos, config)
    particion = particionar(caracteristicas, config)

    ctx = replace(
        ctx,
        caracteristicas=caracteristicas,
        particion=particion,
        n_eventos_crudos=len(eventos),
        hash_datos_crudos=hash_dataframe(eventos),
        hash_datos=hash_dataframe(caracteristicas),
    )
    return registrar_evento(
        ctx,
        "precondicion_preparar_datos",
        eventos_crudos=len(eventos),
        ventanas=len(caracteristicas),
        ventanas_entrenamiento=len(particion.X_entrenamiento),
        ventanas_prueba=len(particion.X_prueba),
        hash_datos_crudos=ctx.hash_datos_crudos,
        hash_datos=ctx.hash_datos,
    )


def precondicion_sellar_modelo(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Obtiene el modelo de referencia y lo sella para la auditoría.

    El modelo es el sujeto de prueba. Si ya viene dado, este paso lo carga y
    lo sella; si el caso de estudio exige producirlo, lo ajusta con los
    hiperparámetros y la semilla declarados en `config.modelo`. En ambos casos
    el producto es un `ModeloSellado` (estimador + versión + hash de
    parámetros + hash de datos + ruta serializada), y su desempeño NO se
    optimiza en función de los resultados de las pruebas posteriores.

    Raises:
        PrecondicionIncumplida: si los datos no se prepararon antes.
    """
    if ctx.particion is None:
        raise PrecondicionIncumplida(
            "no hay partición: `precondicion_preparar_datos` debe correr antes "
            "de sellar el modelo"
        )
    modelo = entrenar(
        ctx.particion.X_entrenamiento, ctx.particion.y_entrenamiento, ctx.config
    )
    ctx = replace(ctx, modelo=modelo)
    return registrar_evento(
        ctx,
        "precondicion_sellar_modelo",
        tipo=ctx.config.modelo.tipo,
        version=modelo.version,
        hash_parametros=modelo.hash_parametros,
        hash_datos_entrenamiento=modelo.hash_datos_entrenamiento,
        ruta_serializado=str(modelo.ruta_serializado),
    )


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

    El texto descriptivo proviene del bloque `sistema` de `config.yaml`: el
    marco no sabe qué sistema audita, solo exige que esté declarado (D46).

    Raises:
        EvidenciaIncompleta: si el modelo todavía no está sellado.
    """
    return _registrar_artefacto(
        ctx,
        "paso_1_caracterizacion_sistema",
        "ficha_caracterizacion",
        generar_ficha_caracterizacion(ctx),
    )


def paso_2_documentacion_datos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 2 — Documentación del conjunto de datos.

    Actividad (Tabla 9): registro de procedencia, composición,
    representatividad de subgrupos y sesgos potenciales.
    Producto: datasheet del conjunto de datos.
    Función NIST AI RMF: MAPEAR.
    Requerimientos: R4.3.

    La composición (número de instancias, clases, distribución, hashes) sale
    de los datos ya preparados; la procedencia y las condiciones de uso, del
    bloque `datos.documentacion` de `config.yaml`.

    Raises:
        EvidenciaIncompleta: si los datos todavía no se prepararon.
    """
    return _registrar_artefacto(
        ctx,
        "paso_2_documentacion_datos",
        "datasheet",
        generar_datasheet(ctx),
    )


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


class PrecondicionIncumplida(RuntimeError):
    """Un paso se invocó sin que su precondición hubiera corrido."""


PASOS = (
    paso_1_caracterizacion_sistema,
    paso_2_documentacion_datos,
    paso_3_declaracion_criterios,
    paso_4_ejecucion_pruebas,
    paso_5_generacion_artefactos,
    paso_6_verificacion_auditabilidad,
)
