"""Los nueve requerimientos de la matriz de mapeo y su evidencia.

El criterio de éxito del piloto es que la ejecución del procedimiento genere
los artefactos asociados a los nueve requerimientos y que estos permitan
reconstruir el comportamiento del sistema (Tabla 10). Este módulo declara esa
correspondencia y la comprueba sobre los artefactos realmente producidos.

Los requerimientos son la definición del marco, no parámetros del despliegue:
por eso viven en el código, como `METRICAS_EQUIDAD`, y no en `config.yaml`.
Los enunciados son los de la Tabla 5; la columna de artefactos traduce su
"prueba técnica y artefacto auditable" a las claves que produce el pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Requerimiento:
    """Un requerimiento operativo y los artefactos que lo evidencian."""

    codigo: str
    principio: str
    enunciado: str
    # Claves de `ContextoEjecucion.artefactos`.
    artefactos: tuple[str, ...]


REQUERIMIENTOS = (
    Requerimiento(
        "R3.1",
        "explicabilidad",
        "Toda predicción relevante del sistema debe poder explicarse mediante "
        "la atribución cuantificada de las variables que la determinaron.",
        ("explicaciones_locales", "reporte_explicabilidad"),
    ),
    Requerimiento(
        "R3.2",
        "explicabilidad",
        "El comportamiento global del modelo debe documentarse mediante la "
        "importancia agregada de las variables sobre el conjunto de "
        "evaluación.",
        ("importancia_global", "figura_importancia_global", "reporte_explicabilidad"),
    ),
    Requerimiento(
        "R3.3",
        "explicabilidad",
        "La información de transparencia debe presentarse en un formato "
        "comprensible para destinatarios no técnicos, incluidos cuidadores.",
        # La Tabla 5 asigna este requerimiento al model card; el marco produce
        # además los enunciados en lenguaje llano del reporte de
        # explicabilidad, y ambos se cuentan como su evidencia.
        ("model_card", "reporte_explicabilidad"),
    ),
    Requerimiento(
        "R4.1",
        "equidad",
        "El desempeño del modelo debe evaluarse de forma desagregada entre "
        "subgrupos de la población monitoreada.",
        ("desempeno_desagregado", "reporte_equidad"),
    ),
    Requerimiento(
        "R4.2",
        "equidad",
        "Las disparidades entre subgrupos deben medirse con métricas de "
        "equidad definidas y umbrales declarados previamente.",
        ("protocolo_evaluacion", "metricas_equidad", "reporte_equidad"),
    ),
    Requerimiento(
        "R4.3",
        "equidad",
        "La composición del conjunto de datos y sus sesgos potenciales deben "
        "documentarse antes del entrenamiento del modelo.",
        ("datasheet",),
    ),
    Requerimiento(
        "R5.1",
        "trazabilidad",
        "Cada inferencia relevante debe registrarse de forma estructurada y "
        "persistente, incluyendo marca temporal, entrada, salida y versión "
        "del modelo.",
        ("bitacora",),
    ),
    Requerimiento(
        "R5.2",
        "trazabilidad",
        "El modelo debe documentarse de forma estandarizada, incluyendo "
        "propósito, desempeño desagregado, limitaciones y condiciones de uso.",
        ("ficha_caracterizacion", "model_card"),
    ),
    Requerimiento(
        "R5.3",
        "trazabilidad",
        "Toda decisión del sistema debe poder reconstruirse ex post y "
        "atribuirse a un responsable identificable.",
        ("bitacora", "explicaciones_locales", "bitacora_ejecucion"),
    ),
)


#: Principios rectores de la ENIA (MICITT, 2024, pp. 30-34), en su orden y con
#: su nombre, y si este marco los operacionaliza. La lista completa importa:
#: un reporte que solo muestre los tres cubiertos se lee como si fueran todos.
PRINCIPIOS_ENIA = (
    ("1", "Paz y dignidad humana", False),
    ("2", "Supervisión humana", False),
    ("3", "Transparencia y explicabilidad", True),
    ("4", "Equidad y no discriminación", True),
    ("5", "Responsabilidad", True),
    ("6", "Sostenibilidad y bienestar", False),
    ("7", "Seguridad, ciberseguridad y protección de la información", False),
)

#: Qué queda fuera dentro de los tres principios que el marco sí cubre. Se
#: declara en el reporte de cumplimiento para que no se lea como cobertura
#: total de cada principio (D53).
ALCANCE_PARCIAL = (
    (
        "Transparencia y explicabilidad",
        "El marco produce la explicación de cada decisión automatizada y su "
        "traducción a lenguaje llano. No cubre el derecho de las personas a "
        "saber cuándo están tratando con una IA, ni la prerrogativa de decidir "
        "no ser afectadas por ella, que el mismo principio establece.",
    ),
    (
        "Equidad y no discriminación",
        "El marco detecta disparidad de desempeño entre subgrupos y documenta "
        "la composición de los datos. No corrige el sesgo que encuentra, y no "
        "cubre la accesibilidad ni la adaptación cultural y lingüística que el "
        "principio también exige. Las categorías que la ENIA nombra —edad, "
        "etnia, género, religión, capacidad económica y nivel formativo— no "
        "están publicadas en los conjuntos de datos del dominio, así que la "
        "comparación se hace entre las personas monitoreadas y no entre esas "
        "categorías.",
    ),
    (
        "Responsabilidad",
        "El marco registra y verifica la atribución de cada decisión a un "
        "responsable declarado. La supervisión humana efectiva sobre esas "
        "decisiones corresponde al principio 2, fuera de alcance.",
    ),
)


def alcance_declarado() -> str:
    """Texto del alcance del marco frente a los principios de la ENIA.

    Un expediente que muestre solo lo que cubre induce a error sobre lo que no.
    """
    cubiertos = [f"{n} ({nombre})" for n, nombre, si in PRINCIPIOS_ENIA if si]
    fuera = [f"{n} ({nombre})" for n, nombre, si in PRINCIPIOS_ENIA if not si]
    lineas = [
        f"Este marco operacionaliza **{len(cubiertos)} de los "
        f"{len(PRINCIPIOS_ENIA)} principios rectores** de la ENIA: "
        + ", ".join(cubiertos)
        + ".",
        "",
        "Quedan fuera de alcance los principios "
        + ", ".join(fuera)
        + ", y los cinco principios transversales de la estrategia.",
        "",
        "Dentro de los tres principios cubiertos, el alcance también es "
        "parcial:",
        "",
    ]
    lineas += [f"- **{nombre}.** {detalle}" for nombre, detalle in ALCANCE_PARCIAL]
    return "\n".join(lineas)


@dataclass(frozen=True)
class CoberturaRequerimiento:
    """Estado de un requerimiento frente a los artefactos producidos."""

    requerimiento: Requerimiento
    presentes: tuple[str, ...]
    faltantes: tuple[str, ...]

    @property
    def cubierto(self) -> bool:
        return not self.faltantes


def verificar_cobertura_requerimientos(
    artefactos: dict[str, Path],
) -> list[CoberturaRequerimiento]:
    """Comprueba qué requerimientos quedaron respaldados por su artefacto.

    Un artefacto cuenta solo si la ruta está registrada **y** el archivo
    existe: una ruta anotada sin archivo detrás documentaría una evidencia
    que nadie puede abrir.

    Args:
        artefactos: claves y rutas de `ContextoEjecucion.artefactos`.

    Returns:
        Una fila por requerimiento, en el orden de la matriz de mapeo.
    """
    cobertura = []
    for requerimiento in REQUERIMIENTOS:
        presentes, faltantes = [], []
        for clave in requerimiento.artefactos:
            ruta = artefactos.get(clave)
            destino = presentes if ruta is not None and Path(ruta).is_file() else faltantes
            destino.append(clave)
        cobertura.append(
            CoberturaRequerimiento(
                requerimiento=requerimiento,
                presentes=tuple(presentes),
                faltantes=tuple(faltantes),
            )
        )
    return cobertura
