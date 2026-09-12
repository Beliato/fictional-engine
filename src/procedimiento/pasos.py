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
    hash_filas,
    particionar,
    validar_esquema,
)
from src.comun.modelado import entrenar, predecir_con_confianza
from src.comun.utilidades import ahora_utc_iso, hash_archivo
from src.equidad.desempeno_desagregado import calcular_desempeno, guardar_desempeno
from src.equidad.metricas_equidad import evaluar_equidad, guardar_metricas
from src.explicabilidad.atribucion_global import calcular_importancia_global
from src.explicabilidad.atribucion_local import (
    construir_explainer,
    explicar_lote,
    referencia_de,
)
from src.equidad.reporte import generar_reporte_equidad
from src.explicabilidad.reporte import (
    generar_reporte_explicabilidad,
    seleccionar_ejemplos,
)
from src.procedimiento.evidencia import (
    generar_bitacora_ejecucion,
    generar_datasheet,
    generar_ficha_caracterizacion,
    generar_manifiesto,
    generar_model_card,
    generar_protocolo_evaluacion,
    generar_reporte_cumplimiento,
)
from src.procedimiento.requerimientos import verificar_cobertura_requerimientos
from src.trazabilidad.registro import RegistroEstructurado
from src.trazabilidad.verificacion import verificar_cobertura, verificar_registro

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
    # Resultados del paso 4, que los pasos 5 y 6 consolidan.
    ids_prueba: tuple[str, ...] = ()
    predicciones: "pd.Series | None" = None
    explicaciones: list[Any] = field(default_factory=list)
    explicacion_global: Any = None
    desempeno_equidad: list[Any] = field(default_factory=list)
    informe_bitacora: Any = None
    informe_cobertura: Any = None
    # Resultados del paso 6.
    hash_protocolo_verificado: bool | None = None
    cobertura_requerimientos: list[Any] = field(default_factory=list)
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

    Carga el crudo declarado en la configuración, valida el esquema,
    construye características,
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

    Se sella el hash del archivo `config.yaml`, no de la configuración ya
    cargada: un auditor lo reproduce con `sha256sum config.yaml` sin ejecutar
    nada del marco.

    Raises:
        EvidenciaIncompleta: si falta algún dato que el protocolo declara.
    """
    ctx = replace(ctx, hash_protocolo=hash_archivo(ctx.config.ruta_archivo))
    return _registrar_artefacto(
        ctx,
        "paso_3_declaracion_criterios",
        "protocolo_evaluacion",
        generar_protocolo_evaluacion(ctx),
    )


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

    El identificador de cada inferencia es `ven-NNNNN`, la posición de la
    ventana en el conjunto de evaluación ordenado temporalmente. La bitácora
    guarda el hash de la fila de entrada, nunca los eventos (D47).

    Raises:
        PrecondicionIncumplida: si faltan datos o modelo.
        BitacoraExistente: si la bitácora ya tiene registros de otra corrida.
    """
    config = ctx.config
    if ctx.particion is None or ctx.modelo is None:
        raise PrecondicionIncumplida(
            "el paso 4 necesita los datos preparados y el modelo sellado; "
            "las precondiciones deben correr antes"
        )
    particion, modelo = ctx.particion, ctx.modelo
    X, y = particion.X_prueba, particion.y_prueba
    ids = [f"ven-{i:05d}" for i in range(len(X))]
    predicciones, confianza = predecir_con_confianza(modelo, X)

    # --- Explicabilidad (R3.1, R3.2) ---
    explicaciones = explicar_lote(
        construir_explainer(modelo, config), modelo, X, ids, config
    )
    global_ = calcular_importancia_global(explicaciones, config)

    # --- Equidad (R4.1, R4.2) ---
    sensibles = particion.sensibles_prueba
    desempeno = calcular_desempeno(y, predicciones, sensibles, config)
    veredicto = evaluar_equidad(y, predicciones, sensibles, config)
    ruta_desempeno = guardar_desempeno(desempeno, config)
    ruta_metricas = guardar_metricas(veredicto, config)

    # --- Trazabilidad (R5.1) ---
    ruta_bitacora = Path(config.rutas.registro_inferencias)
    _exigir_bitacora_nueva(ruta_bitacora)
    RegistroEstructurado(ruta_bitacora, config).registrar_lote(
        {
            "id_evento": id_evento,
            "referencia_entrada": referencia,
            "salida_modelo": str(prediccion),
            "confianza": float(probabilidad),
            "referencia_explicacion": referencia_de(explicacion, config),
        }
        for id_evento, referencia, prediccion, probabilidad, explicacion in zip(
            ids, hash_filas(X), predicciones, confianza, explicaciones
        )
    )
    informe = verificar_registro(ruta_bitacora, config)
    cobertura = verificar_cobertura(ruta_bitacora, set(ids), config)

    evaluadas, posibles = veredicto.cobertura
    ctx = replace(
        ctx,
        ids_prueba=tuple(ids),
        predicciones=predicciones,
        explicaciones=explicaciones,
        explicacion_global=global_,
        desempeno_equidad=desempeno,
        veredicto_equidad=veredicto,
        informe_bitacora=informe,
        informe_cobertura=cobertura,
        artefactos={
            **ctx.artefactos,
            "explicaciones_locales": Path(explicaciones[0].ruta_artefacto),
            "importancia_global": global_.ruta_tabla,
            "figura_importancia_global": global_.ruta_figura_resumen,
            "desempeno_desagregado": ruta_desempeno,
            "metricas_equidad": ruta_metricas,
            "bitacora": ruta_bitacora,
        },
    )
    return registrar_evento(
        ctx,
        "paso_4_ejecucion_pruebas",
        inferencias=len(ids),
        explicaciones=len(explicaciones),
        veredicto_equidad=veredicto.estado,
        cobertura_equidad=f"{evaluadas}/{posibles}",
        bitacora_valida=informe.valido,
        cobertura_bitacora=cobertura.valido,
        problemas=[*informe.problemas, *cobertura.problemas][:5],
    )


def _exigir_bitacora_nueva(ruta: Path) -> None:
    """La bitácora es append-only (D5): no se puede continuar otra corrida.

    Raises:
        BitacoraExistente: si el archivo ya tiene registros. Mezclar dos
            ejecuciones produciría ids duplicados y una evidencia que no
            corresponde a ninguna de las dos.
    """
    if ruta.exists() and ruta.stat().st_size > 0:
        raise BitacoraExistente(
            f"la bitácora {ruta} ya contiene registros de otra ejecución; "
            "archívela o bórrela antes de volver a ejecutar el paso 4"
        )


def paso_5_generacion_artefactos(ctx: ContextoEjecucion) -> ContextoEjecucion:
    """Paso 5 — Generación de artefactos auditables.

    Actividad (Tabla 9): elaboración del reporte de explicabilidad, el reporte
    de equidad y el model card a partir de los resultados obtenidos.
    Producto: artefactos documentales.
    Función NIST AI RMF: GOBERNAR.
    Requerimientos: R5.2, y documentación de R3.1, R3.2, R3.3, R4.1 y R4.2.

    El reporte de cumplimiento no se emite aquí sino en el paso 6: declara la
    cobertura de los nueve requerimientos, que solo puede comprobarse cuando
    ya existen todos los artefactos.

    Raises:
        PrecondicionIncumplida: si el paso 4 no dejó resultados.
    """
    if ctx.veredicto_equidad is None or ctx.explicacion_global is None:
        raise PrecondicionIncumplida(
            "el paso 5 documenta los resultados del paso 4, que todavía no "
            "se ejecutó"
        )
    config = ctx.config
    y_real = dict(zip(ctx.ids_prueba, map(str, ctx.particion.y_prueba)))
    aciertos, errores = seleccionar_ejemplos(ctx.explicaciones, y_real, config)

    ctx = _registrar_artefacto(
        ctx,
        "paso_5_generacion_artefactos",
        "reporte_explicabilidad",
        generar_reporte_explicabilidad(
            ctx.explicacion_global, aciertos, errores, y_real, ctx.id_ejecucion, config
        ),
    )
    ctx = _registrar_artefacto(
        ctx,
        "paso_5_generacion_artefactos",
        "reporte_equidad",
        generar_reporte_equidad(
            ctx.desempeno_equidad, ctx.veredicto_equidad, ctx.id_ejecucion, config
        ),
    )
    return _registrar_artefacto(
        ctx, "paso_5_generacion_artefactos", "model_card", generar_model_card(ctx)
    )


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

    El orden importa: primero se comprueba, después se documenta lo
    comprobado y al final se sella. El manifiesto hashea los artefactos ya
    escritos, así que cualquier cosa emitida después quedaría fuera del sello.

    Raises:
        PrecondicionIncumplida: si el paso 4 no dejó bitácora que verificar.
    """
    config = ctx.config
    if not ctx.ids_prueba or "bitacora" not in ctx.artefactos:
        raise PrecondicionIncumplida(
            "el paso 6 verifica la bitácora del paso 4, que todavía no se "
            "ejecutó"
        )
    ruta_bitacora = ctx.artefactos["bitacora"]
    ctx = replace(
        ctx,
        hash_protocolo_verificado=(
            hash_archivo(config.ruta_archivo) == ctx.hash_protocolo
        ),
        informe_bitacora=verificar_registro(ruta_bitacora, config),
        informe_cobertura=verificar_cobertura(
            ruta_bitacora, set(ctx.ids_prueba), config
        ),
    )
    ctx = registrar_evento(
        ctx,
        "paso_6_verificacion_auditabilidad",
        protocolo_sin_alterar=ctx.hash_protocolo_verificado,
        bitacora_valida=ctx.informe_bitacora.valido,
        cobertura_valida=ctx.informe_cobertura.valido,
    )
    ctx = _registrar_artefacto(
        ctx,
        "paso_6_verificacion_auditabilidad",
        "bitacora_ejecucion",
        generar_bitacora_ejecucion(ctx),
    )
    ctx = replace(
        ctx, cobertura_requerimientos=verificar_cobertura_requerimientos(ctx.artefactos)
    )
    ctx = _registrar_artefacto(
        ctx,
        "paso_6_verificacion_auditabilidad",
        "reporte_cumplimiento",
        generar_reporte_cumplimiento(ctx),
    )
    cubiertos = sum(1 for fila in ctx.cobertura_requerimientos if fila.cubierto)
    ctx = registrar_evento(
        ctx,
        "paso_6_verificacion_auditabilidad",
        requerimientos_cubiertos=f"{cubiertos}/{len(ctx.cobertura_requerimientos)}",
    )
    return _registrar_artefacto(
        ctx,
        "paso_6_verificacion_auditabilidad",
        "manifiesto",
        generar_manifiesto(ctx),
    )


class PrecondicionIncumplida(RuntimeError):
    """Un paso se invocó sin que su precondición hubiera corrido."""


class BitacoraExistente(RuntimeError):
    """La bitácora ya tiene registros de otra ejecución."""


PASOS = (
    paso_1_caracterizacion_sistema,
    paso_2_documentacion_datos,
    paso_3_declaracion_criterios,
    paso_4_ejecucion_pruebas,
    paso_5_generacion_artefactos,
    paso_6_verificacion_auditabilidad,
)
