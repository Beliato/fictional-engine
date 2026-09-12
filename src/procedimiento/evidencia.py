"""Generación de los artefactos documentales del expediente de evidencia.

Produce artefactos legibles por un auditor y un manifiesto que permite
reproducir y verificar la ejecución bit a bit. Cada generador se invoca desde
el paso del procedimiento (Tabla 9) que lo tiene como producto:

    paso 1 -> generar_ficha_caracterizacion
    paso 2 -> generar_datasheet
    paso 3 -> generar_protocolo_evaluacion
    paso 5 -> generar_model_card, generar_reporte_cumplimiento
    paso 6 -> generar_bitacora_ejecucion, generar_manifiesto

Reparto de responsabilidades: lo que el marco puede derivar de los datos o de
la configuración lo calcula aquí; lo que afirma algo sobre el sistema o el
dataset se declara en `config.yaml` y se copia sin interpretar. Así el mismo
código documenta otro sistema sin tocar una línea (D46).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.comun.utilidades import (
    asegurar_directorio,
    rellenar_plantilla,
)
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


class EvidenciaIncompleta(RuntimeError):
    """Falta en el contexto un dato que un artefacto necesita declarar."""
