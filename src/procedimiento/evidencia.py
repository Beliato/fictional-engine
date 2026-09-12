"""Generación de los artefactos documentales del expediente de evidencia.

Produce artefactos legibles por un auditor y un manifiesto que permite
reproducir y verificar la ejecución bit a bit. Cada generador se invoca desde
el paso del procedimiento (Tabla 9) que lo tiene como producto:

    paso 1 -> generar_ficha_caracterizacion
    paso 2 -> generar_datasheet
    paso 3 -> generar_protocolo_evaluacion
    paso 5 -> generar_model_card
    paso 6 -> generar_bitacora_ejecucion, generar_reporte_cumplimiento,
              generar_manifiesto

El reporte de cumplimiento se emite en el paso 6 y no en el 5 porque declara
la cobertura de los nueve requerimientos, que solo se puede comprobar cuando
ya existen todos los artefactos.

Reparto de responsabilidades: lo que el marco puede derivar de los datos o de
la configuración lo calcula aquí; lo que afirma algo sobre el sistema o el
dataset se declara en `config.yaml` y se copia sin interpretar. Así el mismo
código documenta otro sistema sin tocar una línea (D46).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.comun.utilidades import (
    ahora_utc_iso,
    asegurar_directorio,
    rellenar_plantilla,
)
from src.equidad.reporte import lista_limitaciones, tabla_protocolo
from src.explicabilidad.lenguaje import formatear_decimal, formatear_miles

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion
    from src.procedimiento.pasos import ContextoEjecucion


def _plantilla(ctx: "ContextoEjecucion", nombre: str) -> str:
    return (Path(ctx.config.rutas.plantillas) / nombre).read_text(encoding="utf-8")


def _escribir(destino: Path, texto: str) -> Path:
    asegurar_directorio(destino.parent)
    with destino.open("w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return destino


def _exigir(valor: Any, que: str) -> Any:
    """Exige un dato que debió producir una precondición o un paso anterior."""
    if valor is None:
        raise EvidenciaIncompleta(
            f"falta {que} en el contexto de ejecución; el paso que lo produce "
            "no ha corrido"
        )
    return valor


def _enumerar(nombres: "tuple[str, ...]") -> str:
    return f"{len(nombres)} ({', '.join(nombres)})" if nombres else "ninguno"


def generar_ficha_caracterizacion(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/ficha_caracterizacion.md` (producto del paso 1).

    Describe el sistema evaluado, su finalidad, su población destinataria y
    la configuración de sensores empleada. Es el insumo de caracterización
    que la función MAPEAR del NIST AI RMF exige antes de medir nada.

    Raises:
        EvidenciaIncompleta: si el modelo todavía no está sellado.
        PlantillaIncompleta: si la plantilla declara un marcador sin valor.
    """
    config = ctx.config
    sistema = config.sistema
    modelo = _exigir(ctx.modelo, "el modelo sellado")
    datos = config.datos
    complementarios = (*datos.sensores_puerta, *datos.sensores_temperatura)

    valores = {
        "id_ejecucion": ctx.id_ejecucion,
        "nombre_sistema": sistema.nombre,
        "version_modelo": (
            f"{config.modelo.tipo} v{modelo.version} "
            f"(hash de parámetros {modelo.hash_parametros[:12]})"
        ),
        "version_marco": config.version_marco,
        "responsable": config.trazabilidad.responsable_por_defecto,
        "marca_temporal": ctx.marca_inicio,
        "finalidad": sistema.finalidad,
        "poblacion_destinataria": sistema.poblacion_destinataria,
        "configuracion_sensores": sistema.contexto_sensores,
        "columnas_sensor_pir": _enumerar(datos.columnas_sensor_pir),
        "sensores_complementarios": _enumerar(complementarios),
        "ventana_agregacion": (
            f"ventanas disjuntas de {formatear_miles(datos.ventana.n_eventos)} "
            "eventos consecutivos; franjas horarias: "
            + ", ".join(
                f"{f.nombre} (desde {f.desde} h)" for f in datos.franjas_horarias
            )
        ),
        "tarea_aprendizaje": sistema.tarea_aprendizaje,
        "contexto_despliegue": sistema.contexto_despliegue,
        "personas_afectadas": sistema.personas_afectadas,
        "delimitacion": sistema.delimitacion,
    }
    return _escribir(
        Path(config.rutas.ficha_caracterizacion),
        rellenar_plantilla(_plantilla(ctx, "ficha_caracterizacion.md"), valores),
    )


def generar_datasheet(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/datasheet.md` (producto del paso 2, R4.3).

    Documenta procedencia, composición y representatividad del conjunto de
    datos. La composición se calcula sobre el cuadro de características
    completo, antes de partir: el datasheet describe el dataset, no el
    conjunto de entrenamiento.

    Raises:
        EvidenciaIncompleta: si los datos todavía no se prepararon.
        PlantillaIncompleta: si la plantilla declara un marcador sin valor.
    """
    config = ctx.config
    documentacion = config.datos.documentacion
    caracteristicas = _exigir(ctx.caracteristicas, "el cuadro de características")
    objetivo = config.datos.columna_objetivo
    conteo = caracteristicas[objetivo].value_counts().sort_index()
    total = int(conteo.sum())
    fechas = caracteristicas["fecha"]

    valores = {
        "id_ejecucion": ctx.id_ejecucion,
        "fuente": config.datos.fuente,
        "motivacion": documentacion.motivacion,
        "creador": documentacion.creador,
        "n_instancias_crudo": formatear_miles(
            _exigir(ctx.n_eventos_crudos, "el conteo de eventos crudos")
        ),
        "n_instancias_procesado": formatear_miles(len(caracteristicas)),
        "columnas_sensor_pir": _enumerar(config.datos.columnas_sensor_pir),
        "columna_objetivo": objetivo,
        "clases": ", ".join(str(c) for c in conteo.index),
        "distribucion_clases": _tabla_distribucion(conteo, total),
        "datos_personales": documentacion.datos_personales,
        "ventana_temporal": f"{min(fechas)} a {max(fechas)}",
        "consentimiento": documentacion.consentimiento,
        "mecanismo_recoleccion": documentacion.mecanismo_recoleccion,
        "transformaciones": _transformaciones(config),
        "derivacion_subgrupos": _derivacion_subgrupos(config),
        "hash_datos_crudos": _exigir(
            ctx.hash_datos_crudos, "el hash de los datos crudos"
        ),
        "hash_datos_procesados": _exigir(
            ctx.hash_datos, "el hash de los datos procesados"
        ),
        "uso_en_proyecto": documentacion.uso_en_proyecto,
        "usos_no_recomendados": documentacion.usos_no_recomendados,
        "licencia": documentacion.licencia,
        "instrucciones_descarga": documentacion.instrucciones_descarga,
    }
    return _escribir(
        Path(config.rutas.datasheet),
        rellenar_plantilla(_plantilla(ctx, "datasheet.md"), valores),
    )


def _tabla_distribucion(conteo: Any, total: int) -> str:
    """Distribución de clases como tabla, con el porcentaje de cada una.

    La representatividad que pide el R4.3 se lee aquí: una clase con pocas
    ventanas no se puede auditar por equidad, y el reporte lo dirá.
    """
    filas = ["| Actividad | Ventanas | % |", "|---|---:|---:|"]
    for clase, n in conteo.items():
        filas.append(
            f"| {clase} | {formatear_miles(int(n))} | "
            f"{formatear_decimal(100 * int(n) / total, 1)} |"
        )
    filas.append(f"| **Total** | **{formatear_miles(total)}** | **100,0** |")
    return "\n".join(filas)


def _transformaciones(config: "Configuracion") -> str:
    """Describe la preparación de datos a partir de la configuración."""
    datos = config.datos
    zonas = datos.zonas_distintas
    excluidas = ", ".join(datos.actividades.excluidas) or "ninguna"
    return "\n".join(
        [
            f"- Los eventos se agrupan en ventanas disjuntas de "
            f"{formatear_miles(datos.ventana.n_eventos)} eventos consecutivos; "
            "cada ventana es una fila.",
            f"- Las activaciones se cuentan por zona del hogar ({len(zonas)} "
            f"zonas: {', '.join(zonas)}), no por sensor, para que las "
            "explicaciones nombren lugares y no identificadores (R3.3).",
            "- Se añaden temperatura por sensor, eventos de puerta, hora del "
            "día, día de la semana y duración de la ventana.",
            "- Los eventos que quedan fuera de todo intervalo anotado forman la "
            f"clase «{datos.actividades.etiqueta_sin_actividad}» en vez de "
            "descartarse: son comportamiento real del hogar.",
            f"- Actividades excluidas por falta de casos: {excluidas}.",
            f"- Partición `{datos.particion.estrategia}` con test_size "
            f"{formatear_decimal(datos.particion.test_size, 2)}: los últimos "
            "días del período van a prueba.",
        ]
    )


def _derivacion_subgrupos(config: "Configuracion") -> str:
    """Cómo se derivan los subgrupos de equidad, y por qué se comparan."""
    lineas = []
    for subgrupo in config.equidad.subgrupos:
        categorias = (
            ", ".join(subgrupo.categorias)
            if subgrupo.categorias
            else "las categorías presentes en los datos"
        )
        lineas.append(
            f"- **{subgrupo.nombre}** (columna `{subgrupo.columna}`; "
            f"categorías: {categorias}). {subgrupo.justificacion}"
        )
    lineas.append(
        "- Cortes horarios: "
        + "; ".join(
            f"{f.nombre} desde {f.desde} h" for f in config.datos.franjas_horarias
        )
        + "."
    )
    return "\n".join(lineas)


def generar_protocolo_evaluacion(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/protocolo_evaluacion.md` (producto del paso 3).

    Deja constancia de los subgrupos de comparación, las métricas de equidad
    y los umbrales de referencia declarados ANTES de ejecutar las pruebas,
    junto con el hash del `config.yaml` que los contiene.

    Ese hash es el control metodológico: sin él, la afirmación de que los
    umbrales no se ajustaron a los resultados no es verificable por un
    auditor externo.

    El hash lo sella el paso 3 antes de llamar aquí; este generador solo lo
    declara. Las métricas y sus umbrales se toman de la misma función que
    usa el reporte de equidad, para que el expediente no pueda afirmar dos
    protocolos distintos para la misma corrida.

    Raises:
        EvidenciaIncompleta: si el protocolo todavía no se selló.
        PlantillaIncompleta: si la plantilla declara un marcador sin valor.
    """
    from src.comun.semillas import instantanea_entorno

    config = ctx.config
    entorno = instantanea_entorno()
    valores = {
        "id_ejecucion": ctx.id_ejecucion,
        "marca_temporal": ctx.marca_inicio,
        "hash_protocolo": _exigir(ctx.hash_protocolo, "el hash del protocolo"),
        "commit_git": entorno["git_commit"]
        + ("" if entorno["git_arbol_limpio"] == "sí" else " (árbol con cambios sin confirmar)"),
        "tabla_subgrupos": _tabla_subgrupos(config),
        "justificacion_subgrupos": _derivacion_subgrupos(config),
        "tabla_umbrales": tabla_protocolo(config),
        "justificacion_umbrales": config.equidad.justificacion_umbrales,
        "limitaciones": lista_limitaciones(config),
        "metricas_desempeno": _metricas_desempeno(config),
    }
    return _escribir(
        Path(config.rutas.protocolo_evaluacion),
        rellenar_plantilla(_plantilla(ctx, "protocolo_evaluacion.md"), valores),
    )


def _tabla_subgrupos(config: "Configuracion") -> str:
    filas = ["| Subgrupo | Columna | Categorías |", "|---|---|---|"]
    for subgrupo in config.equidad.subgrupos:
        categorias = (
            ", ".join(subgrupo.categorias)
            if subgrupo.categorias
            else "las presentes en los datos"
        )
        filas.append(
            f"| {subgrupo.nombre} | `{subgrupo.columna}` | {categorias} |"
        )
    filas.append("")
    filas.append(
        "- **Soporte mínimo:** "
        f"{formatear_miles(config.equidad.soporte_minimo)} casos en el "
        "denominador de cada tasa; cada actividad se evalúa contra el resto."
    )
    return "\n".join(filas)


def _metricas_desempeno(config: "Configuracion") -> str:
    """Métricas de desempeño desagregado declaradas para el R4.1."""
    return "\n".join(
        [
            "Por cada categoría de cada subgrupo: número de ventanas, "
            "actividades presentes, exactitud, y precisión, exhaustividad y "
            "F1 promediadas en macro sobre las actividades que aparecen en "
            "las etiquetas reales de esa categoría.",
            "",
            "No se optimizan: se miden. El modelo es sujeto de prueba, no "
            "objeto de optimización (Tabla 10).",
        ]
    )


def generar_model_card(ctx: "ContextoEjecucion") -> Path:
    """Rellena `plantillas/model_card.md` (producto del paso 5).

    Documenta el modelo de forma estandarizada: propósito, datos, desempeño
    global y desagregado, equidad, explicabilidad, trazabilidad y
    limitaciones (R5.2), en un formato legible por destinatarios no técnicos
    (R3.3).

    Raises:
        EvidenciaIncompleta: si falta algún resultado del paso 4.
    """
    from src.comun.semillas import instantanea_entorno
    from src.equidad.reporte import (
        ESTADOS,
        lista_limitaciones,
        tabla_desempeno,
        tabla_resultados,
    )
    from src.explicabilidad.lenguaje import etiqueta_caracteristica

    config = ctx.config
    modelo = _exigir(ctx.modelo, "el modelo sellado")
    veredicto = _exigir(ctx.veredicto_equidad, "el veredicto de equidad")
    global_ = _exigir(ctx.explicacion_global, "la importancia global")
    informe = _exigir(ctx.informe_bitacora, "la verificación de la bitácora")
    evaluadas, posibles = veredicto.cobertura
    articulacion = config.articulacion_normativa

    valores = {
        "modelo_tipo": config.modelo.tipo,
        "modelo_version": modelo.version,
        "fecha_sellado": ctx.marca_inicio,
        "hiperparametros": ", ".join(
            f"`{clave}={valor}`"
            for clave, valor in sorted(config.modelo.hiperparametros.items())
        ),
        "semilla": str(config.semilla),
        "hash_parametros": modelo.hash_parametros,
        "hash_datos_entrenamiento": modelo.hash_datos_entrenamiento,
        "version_marco": config.version_marco,
        "responsable": config.trazabilidad.responsable_por_defecto,
        "usuarios_previstos": config.sistema.poblacion_destinataria,
        "usos_fuera_alcance": config.datos.documentacion.usos_no_recomendados,
        "datos_fuente": config.datos.fuente,
        "particion": (
            f"`{config.datos.particion.estrategia}`, test_size "
            f"{formatear_decimal(config.datos.particion.test_size, 2)}"
        ),
        "tabla_desempeno_global": _tabla_desempeno_global(ctx),
        "tabla_desempeno_desagregado": tabla_desempeno(ctx.desempeno_equidad),
        "tabla_metricas_equidad": tabla_resultados(
            veredicto.metricas_incumplidas(),
            "_Ninguna combinación evaluable excede su umbral._",
        ),
        "veredicto_equidad": (
            f"{ESTADOS[veredicto.estado]} — {evaluadas} de {posibles} "
            "combinaciones evaluadas"
        ),
        "explainer": (
            f"{config.explicabilidad.explainer}, perturbación "
            f"`{config.explicabilidad.perturbacion}`"
        ),
        "importancia_global_top": ", ".join(
            f"{etiqueta_caracteristica(nombre, config.datos.nombres_zona)} "
            f"({formatear_decimal(global_.importancia_media_abs[nombre], 3)})"
            for nombre in global_.top(3)
        ),
        "rutas_figuras_explicabilidad": ", ".join(
            f"`{_relativa(ruta, config)}`"
            for ruta in (global_.ruta_figura_resumen, *global_.rutas_dependencias.values())
        ),
        "ruta_bitacora": f"`{_relativa(ctx.artefactos['bitacora'], config)}`",
        "n_inferencias": formatear_miles(informe.n_registros),
        "estado_verificacion_bitacora": "VÁLIDA" if informe.valido else "NO VÁLIDA",
        "limitaciones": lista_limitaciones(config),
        "ruta_manifiesto": f"`{_relativa(config.rutas.manifiesto, config)}`",
        "instantanea_entorno": _tabla_entorno(instantanea_entorno()),
    }
    for principio, prefijos in (
        ("explicabilidad", "explicabilidad"),
        ("equidad", "equidad"),
        ("trazabilidad", "trazabilidad"),
    ):
        mapeo = articulacion[principio]
        valores[f"enia_{prefijos}"] = mapeo["enia_cr"]
        valores[f"aiact_{prefijos}"] = mapeo["ai_act_eu"]
        valores[f"nist_{prefijos}"] = mapeo["nist_ai_rmf"]

    return _escribir(
        Path(config.rutas.model_card),
        rellenar_plantilla(_plantilla(ctx, "model_card.md"), valores),
    )


def _relativa(ruta: Path, config: "Configuracion") -> str:
    """Ruta vista desde la raíz del repositorio, en POSIX."""
    import os

    return Path(
        os.path.relpath(Path(ruta), Path(config.rutas.artefactos).parent)
    ).as_posix()


def _tabla_entorno(entorno: dict) -> str:
    filas = ["| Componente | Valor |", "|---|---|"]
    filas += [f"| {clave} | `{valor}` |" for clave, valor in entorno.items()]
    return "\n".join(filas)


def _tabla_desempeno_global(ctx: "ContextoEjecucion") -> str:
    """Desempeño del modelo sobre todo el conjunto de evaluación.

    Se mide, no se persigue: el modelo es sujeto de prueba (Tabla 10).
    """
    from sklearn.metrics import accuracy_score, f1_score

    particion = _exigir(ctx.particion, "la partición")
    predicciones = _exigir(ctx.predicciones, "las predicciones")
    reales = particion.y_prueba.astype(str)
    predichas = predicciones.astype(str)
    return "\n".join(
        [
            "| Métrica | Valor |",
            "|---|---:|",
            f"| Ventanas de evaluación | {formatear_miles(len(reales))} |",
            f"| Exactitud | {formatear_decimal(accuracy_score(reales, predichas))} |",
            "| F1 macro | "
            f"{formatear_decimal(f1_score(reales, predichas, average='macro', zero_division=0.0))} |",
        ]
    )


def generar_reporte_cumplimiento(ctx: "ContextoEjecucion") -> Path:
    """Genera el reporte de cumplimiento consolidado (producto del paso 6).

    Reúne el estado de los tres principios, la cobertura de los nueve
    requerimientos y la articulación normativa. El veredicto global distingue
    dos cosas que no son lo mismo: que falte evidencia y que la evidencia
    muestre un incumplimiento.

    Raises:
        EvidenciaIncompleta: si falta algún resultado de los pasos anteriores.
    """
    from src.comun.semillas import instantanea_entorno
    from src.equidad.reporte import ESTADOS, tabla_protocolo, tabla_resultados
    from src.procedimiento.requerimientos import alcance_declarado

    config = ctx.config
    modelo = _exigir(ctx.modelo, "el modelo sellado")
    veredicto = _exigir(ctx.veredicto_equidad, "el veredicto de equidad")
    informe = _exigir(ctx.informe_bitacora, "la verificación de la bitácora")
    cobertura_bitacora = _exigir(ctx.informe_cobertura, "la cobertura de la bitácora")
    cobertura = _exigir(
        ctx.cobertura_requerimientos, "la cobertura de los requerimientos"
    )
    completa = all(fila.cubierto for fila in cobertura)
    trazable = (
        informe.valido and cobertura_bitacora.valido and bool(ctx.hash_protocolo_verificado)
    )
    if not completa:
        global_ = "EVIDENCIA INCOMPLETA"
    elif veredicto.aprueba and trazable:
        global_ = "CUMPLE"
    else:
        global_ = "NO CUMPLE"

    incumplidas = veredicto.metricas_incumplidas()
    valores = {
        "id_ejecucion": ctx.id_ejecucion,
        "fecha_ejecucion": ctx.marca_inicio,
        "version_marco": config.version_marco,
        "modelo_tipo": config.modelo.tipo,
        "modelo_version": modelo.version,
        "hash_parametros": modelo.hash_parametros[:12],
        "ruta_manifiesto": f"`{_relativa(config.rutas.manifiesto, config)}`",
        "veredicto_global": global_,
        "estado_explicabilidad": "documentada",
        "ruta_reporte_explicabilidad": f"`{_relativa(config.rutas.reporte_explicabilidad, config)}`",
        "estado_equidad": ESTADOS[veredicto.estado],
        "ruta_reporte_equidad": f"`{_relativa(config.rutas.reporte_equidad, config)}`",
        "estado_trazabilidad": "verificada" if trazable else "con hallazgos",
        "ruta_bitacora": f"`{_relativa(ctx.artefactos['bitacora'], config)}`",
        "resumen_explicabilidad": _resumen_explicabilidad(ctx),
        "subgrupos": ", ".join(s.nombre for s in config.equidad.subgrupos),
        "tabla_umbrales": tabla_protocolo(config),
        "tabla_metricas_equidad": tabla_resultados(
            incumplidas, "_Ninguna combinación evaluable excede su umbral._"
        ),
        "metricas_incumplidas": (
            ", ".join(
                f"{r.subgrupo}/{r.actividad}/{r.metrica}" for r in incumplidas
            )
            or "ninguna"
        ),
        "n_inferencias": formatear_miles(informe.n_registros),
        "estado_verificacion_bitacora": "VÁLIDA" if informe.valido else "NO VÁLIDA",
        "estado_cobertura": "COMPLETA" if cobertura_bitacora.valido else "INCOMPLETA",
        "alcance": alcance_declarado(),
        "tabla_requerimientos": _tabla_requerimientos(cobertura),
        "tabla_articulacion_normativa": _tabla_articulacion(config),
        "git_commit": instantanea_entorno()["git_commit"],
    }
    return _escribir(
        Path(config.rutas.reporte_cumplimiento),
        rellenar_plantilla(_plantilla(ctx, "reporte_cumplimiento.md"), valores),
    )


def _resumen_explicabilidad(ctx: "ContextoEjecucion") -> str:
    from src.explicabilidad.lenguaje import etiqueta_caracteristica

    global_ = _exigir(ctx.explicacion_global, "la importancia global")
    destacadas = ", ".join(
        etiqueta_caracteristica(nombre, ctx.config.datos.nombres_zona)
        for nombre in global_.top(3)
    )
    return (
        f"Se explicaron {formatear_miles(global_.n_explicaciones)} inferencias, "
        "todas las del conjunto de evaluación, con atribución local por evento "
        f"(R3.1) y agregación global (R3.2). Características más influyentes: "
        f"{destacadas}. El reporte incluye los enunciados en lenguaje llano "
        "exigidos por el R3.3."
    )


def _tabla_requerimientos(cobertura: list) -> str:
    filas = [
        "| Código | Principio | Requerimiento | Evidencia | Estado |",
        "|---|---|---|---|---|",
    ]
    for fila in cobertura:
        requerimiento = fila.requerimiento
        evidencia = ", ".join(f"`{clave}`" for clave in fila.presentes) or "—"
        estado = "cubierto" if fila.cubierto else "FALTA: " + ", ".join(fila.faltantes)
        filas.append(
            f"| {requerimiento.codigo} | {requerimiento.principio} | "
            f"{requerimiento.enunciado} | {evidencia} | {estado} |"
        )
    return "\n".join(filas)


def _tabla_articulacion(config: "Configuracion") -> str:
    filas = ["| Principio | ENIA Costa Rica | AI Act EU | NIST AI RMF |", "|---|---|---|---|"]
    for principio, mapeo in config.articulacion_normativa.items():
        filas.append(
            f"| {principio.capitalize()} | {mapeo['enia_cr']} | "
            f"{mapeo['ai_act_eu']} | {mapeo['nist_ai_rmf']} |"
        )
    return "\n".join(filas)


def generar_bitacora_ejecucion(ctx: "ContextoEjecucion") -> Path:
    """Escribe la bitácora de ejecución: qué paso corrió, cuándo y con qué
    entradas y salidas (producto del paso 6).

    Deja el Markdown legible y, al lado, el mismo contenido en JSON para que
    otra herramienta pueda consumirlo sin volver a parsear una tabla.

    Returns:
        Ruta del Markdown; el JSON queda junto a él con la misma raíz.
    """
    from src.comun.utilidades import escribir_json

    config = ctx.config
    destino = Path(config.rutas.bitacora_ejecucion)
    lineas = [
        f"# Bitácora de ejecución — {ctx.id_ejecucion}",
        "",
        "> Producto del **paso 6** del procedimiento (Tabla 9).",
        f"> Inicio de la corrida: {ctx.marca_inicio}",
        "",
    ]
    for evento in ctx.eventos:
        lineas.append(f"## {evento['paso']} — {evento['marca_temporal']}")
        lineas.append("")
        lineas.append("| Campo | Valor |")
        lineas.append("|---|---|")
        for clave, valor in evento.items():
            if clave not in ("paso", "marca_temporal"):
                lineas.append(f"| {clave} | `{valor}` |")
        lineas.append("")
    escribir_json(destino.with_suffix(".json"), ctx.eventos)
    return _escribir(destino, "\n".join(lineas))


def generar_manifiesto(ctx: "ContextoEjecucion") -> Path:
    """Emite `config.rutas.manifiesto`: JSON determinista con

        - id y marcas temporales de la ejecución,
        - instantánea del entorno (`src.comun.semillas.instantanea_entorno`),
        - `config.yaml` crudo usado,
        - hash de datos crudos, características, modelo,
        - hash de cada artefacto generado,
        - veredicto de equidad y estado de verificación de la bitácora.

    Es la pieza que hace la ejecución "auditable" y reproducible.

    Se emite al final del paso 6: hashea los artefactos ya escritos, así que
    cualquier artefacto posterior quedaría fuera del sello.
    """
    from src.comun.semillas import instantanea_entorno
    from src.comun.utilidades import escribir_json, hash_archivo

    config = ctx.config
    veredicto = _exigir(ctx.veredicto_equidad, "el veredicto de equidad")
    informe = _exigir(ctx.informe_bitacora, "la verificación de la bitácora")
    cobertura_bitacora = _exigir(ctx.informe_cobertura, "la cobertura de la bitácora")
    cobertura = _exigir(
        ctx.cobertura_requerimientos, "la cobertura de los requerimientos"
    )
    modelo = _exigir(ctx.modelo, "el modelo sellado")
    evaluadas, posibles = veredicto.cobertura

    destino = Path(config.rutas.manifiesto)
    escribir_json(
        destino,
        {
            "id_ejecucion": ctx.id_ejecucion,
            "marca_inicio": ctx.marca_inicio,
            "marca_manifiesto": ahora_utc_iso(),
            "entorno": instantanea_entorno(),
            "protocolo": {
                "archivo": _relativa(config.ruta_archivo, config),
                "hash_sellado": ctx.hash_protocolo,
                "hash_verificado_en_paso_6": ctx.hash_protocolo_verificado,
            },
            "configuracion": config.crudo,
            "datos": {
                "eventos_crudos": ctx.n_eventos_crudos,
                "ventanas": len(ctx.caracteristicas)
                if ctx.caracteristicas is not None
                else None,
                "hash_crudos": ctx.hash_datos_crudos,
                "hash_procesados": ctx.hash_datos,
            },
            "modelo": {
                "tipo": config.modelo.tipo,
                "version": modelo.version,
                "hash_parametros": modelo.hash_parametros,
                "hash_datos_entrenamiento": modelo.hash_datos_entrenamiento,
                "version_sklearn": modelo.version_sklearn,
            },
            "equidad": {
                "estado": veredicto.estado,
                "combinaciones_evaluadas": evaluadas,
                "combinaciones_posibles": posibles,
                "incumplidas": [
                    {
                        "subgrupo": r.subgrupo,
                        "actividad": r.actividad,
                        "metrica": r.metrica,
                        "valor": r.valor_observado,
                        "umbral": r.umbral,
                    }
                    for r in veredicto.metricas_incumplidas()
                ],
            },
            "bitacora": {
                "registros": informe.n_registros,
                "valida": informe.valido,
                "cobertura_valida": cobertura_bitacora.valido,
                "problemas": [*informe.problemas, *cobertura_bitacora.problemas],
            },
            "requerimientos": {
                fila.requerimiento.codigo: {
                    "cubierto": fila.cubierto,
                    "evidencia": list(fila.presentes),
                    "faltantes": list(fila.faltantes),
                }
                for fila in cobertura
            },
            "artefactos": {
                nombre: {
                    "ruta": _relativa(ruta, config),
                    "sha256": hash_archivo(ruta),
                }
                for nombre, ruta in sorted(ctx.artefactos.items())
                if Path(ruta).is_file()
            },
            "eventos": ctx.eventos,
        },
    )
    return destino


class EvidenciaIncompleta(RuntimeError):
    """Falta en el contexto un dato que un artefacto necesita declarar."""
