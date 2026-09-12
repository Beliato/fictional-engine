"""Validación, características y partición determinista de eventos de sensores.

Este módulo **no sabe de qué dataset provienen los datos**. Recibe eventos ya
normalizados según el contrato de `src.comun.lectores` —marca temporal,
sensor, valor y actividad— y todo lo que hace vale igual para cualquier
sistema de sensores pasivos.

Lo propio de cada formato de origen vive en un lector, no aquí. Aplicar el
marco a otro dataset PIR no requiere tocar este archivo: ver
`docs/aplicar-a-otro-dataset.md`.

Este módulo tampoco descarga datos: espera el archivo crudo en la ruta
declarada en `config.yaml` (`datos.archivo_crudo`) y su procedencia se
documenta en el datasheet.

Representación de modelado
--------------------------
Los eventos se agrupan en ventanas disjuntas de `ventana.n_eventos` eventos
consecutivos y cada ventana produce una fila tabular. Las características se
nombran por **zona del hogar** (`conteo_Kitchen`), no por sensor
(`conteo_M018`): el R3.3 exige que la información de transparencia sea
comprensible para destinatarios no técnicos, y un identificador de sensor no
lo es. El mapeo vive en `config.datos.zonas`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from src.comun.lectores import COLUMNA_HOGAR, leer_eventos
from src.comun.utilidades import hash_sha256

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion, FranjaHoraria


@dataclass(frozen=True)
class ParticionSupervisada:
    """Resultado de la partición train/test, con las columnas sensibles
    conservadas por separado para el análisis de equidad."""

    X_entrenamiento: "pd.DataFrame"
    X_prueba: "pd.DataFrame"
    y_entrenamiento: "pd.Series"
    y_prueba: "pd.Series"
    sensibles_entrenamiento: "pd.DataFrame"
    sensibles_prueba: "pd.DataFrame"


def cargar_crudo(config: "Configuracion") -> "pd.DataFrame":
    """Lee el crudo con el lector declarado en `config.datos.formato`.

    Delega en `src.comun.lectores.leer_eventos`, que instancia el adaptador
    del formato y **verifica el contrato** sobre lo que devuelve. Este módulo
    no conoce ningún formato de origen: esa es la condición para que el marco
    se aplique a otros datasets sin modificarlo.

    Args:
        config: configuración del marco.

    Returns:
        DataFrame con columnas `marca_temporal`, `sensor`, `valor` y
        `actividad`, ordenado en el tiempo.

    Raises:
        FileNotFoundError: si no existe `config.datos.archivo_crudo`.
        FormatoNoReconocido: si el formato no está registrado, o el archivo
            no corresponde al formato declarado.
        ContratoIncumplido: si el lector devolvió algo fuera de contrato.
    """
    return leer_eventos(config)


def validar_esquema(df: "pd.DataFrame", config: "Configuracion") -> None:
    """Valida que el DataFrame crudo tiene el esquema esperado.

    Raises:
        EsquemaDatosInvalido: si alguna comprobación falla.
    """
    faltantes = {"marca_temporal", "sensor", "valor", "actividad"} - set(df.columns)
    if faltantes:
        raise EsquemaDatosInvalido(f"faltan columnas: {sorted(faltantes)}")

    for columna in ("marca_temporal", "sensor", "valor"):
        if df[columna].isna().any():
            raise EsquemaDatosInvalido(f"{columna}: contiene nulos")

    if COLUMNA_HOGAR in df.columns and df[COLUMNA_HOGAR].isna().any():
        raise EsquemaDatosInvalido(f"{COLUMNA_HOGAR}: contiene nulos")

    ordenado = (
        df.groupby(COLUMNA_HOGAR, sort=False)["marca_temporal"]
        .is_monotonic_increasing.all()
        if COLUMNA_HOGAR in df.columns
        else df["marca_temporal"].is_monotonic_increasing
    )
    if not ordenado:
        raise EsquemaDatosInvalido(
            "marca_temporal: los eventos no están ordenados en el tiempo; la "
            "partición temporal y la ventana dependen de ese orden"
        )

    if not config.datos.columnas_sensor_pir:
        raise EsquemaDatosInvalido(
            "config.datos.columnas_sensor_pir está vacía: sin sensores PIR "
            "declarados no se puede construir ninguna característica"
        )

    presentes = set(df["sensor"].unique())
    pir_ausentes = set(config.datos.columnas_sensor_pir) - presentes
    if pir_ausentes:
        raise EsquemaDatosInvalido(
            f"sensores PIR declarados pero ausentes del crudo: "
            f"{sorted(pir_ausentes)}"
        )

    # Un sensor de temperatura declarado que nunca reporta produciría una
    # columna entera de nulos, que ningún relleno puede completar y que el
    # clasificador no acepta. Mejor detenerse acá que fallar al entrenar.
    temp_ausentes = set(config.datos.sensores_temperatura) - presentes
    if temp_ausentes:
        raise EsquemaDatosInvalido(
            f"sensores de temperatura declarados pero ausentes del crudo: "
            f"{sorted(temp_ausentes)}"
        )

    # Los sensores de temperatura no tienen zona y no deben tenerla: no
    # localizan a la persona, miden una condición ambiental. Sus lecturas
    # entran como característica propia, no como conteo por zona.
    ubicacion = presentes - set(config.datos.sensores_temperatura)
    sin_zona = {s for s in ubicacion if s not in config.datos.zonas}
    if sin_zona:
        raise EsquemaDatosInvalido(
            f"sensores presentes en el crudo sin zona asignada: {sorted(sin_zona)}"
        )


def franja_horaria(hora: int, franjas: "tuple[FranjaHoraria, ...]") -> str:
    """Devuelve la franja horaria a la que pertenece `hora` (0-23).

    Las franjas vienen de `config.datos.franjas_horarias`. Son una decisión
    de dominio, no una constante: un servicio con turnos de noche distintos
    querría otros cortes, y ese cambio no debería exigir tocar código.
    """
    etiqueta = franjas[0].nombre
    for franja in franjas:
        if hora >= franja.desde:
            etiqueta = franja.nombre
    return etiqueta


def construir_caracteristicas(
    df: "pd.DataFrame", config: "Configuracion"
) -> "pd.DataFrame":
    """Deriva las características de modelado a partir de los eventos crudos.

    Agrupa los eventos en ventanas disjuntas de `config.datos.ventana.n_eventos`
    y produce una fila por ventana:

        - `conteo_<zona>`: activaciones de sensores en esa zona.
        - `temp_<sensor>`: última lectura de cada sensor de temperatura.
        - `eventos_puerta`: aperturas y cierres de puerta.
        - `hora_del_dia`, `dia_semana`, `duracion_segundos`.
        - `franja_horaria` y `tipo_dia`: columnas sensibles para el análisis
          desagregado; NO son características del modelo.
        - `actividad`: la etiqueta de la ventana, tomada de su último evento.

    Se descartan las ventanas cuya etiqueta esté en
    `config.datos.actividades.excluidas`.

    Returns:
        DataFrame de características listo para particionar.
    """
    n = config.datos.ventana.n_eventos
    zonas = config.datos.zonas
    zonas_distintas = config.datos.zonas_distintas
    temperatura = set(config.datos.sensores_temperatura)
    puertas = set(config.datos.sensores_puerta)

    trabajo = df.copy()
    trabajo["zona"] = trabajo["sensor"].map(zonas)
    # Con varias viviendas las ventanas se forman dentro de cada una: una
    # ventana que cruzara hogares mezclaría a dos personas en una sola fila.
    # El identificador lleva el hogar y la posición con ceros a la izquierda
    # para que el orden siga siendo el cronológico dentro de cada vivienda.
    if COLUMNA_HOGAR in trabajo.columns:
        posicion = trabajo.groupby(COLUMNA_HOGAR).cumcount() // n
        trabajo["ventana"] = (
            trabajo[COLUMNA_HOGAR] + "|" + posicion.map(lambda i: f"{i:08d}")
        )
    else:
        trabajo["ventana"] = trabajo.index // n
    # La última ventana se descarta si quedó incompleta: una ventana corta
    # tendría conteos sistemáticamente menores y sería una fila distinta a
    # todas las demás.
    completas = trabajo.groupby("ventana")["sensor"].transform("size") == n
    trabajo = trabajo[completas]

    # Todo lo que sigue está vectorizado a propósito. Iterar 57 000 grupos con
    # `groupby` tarda casi dos minutos, y el pipeline está hecho para
    # re-ejecutarse y comparar corridas bit a bit: dos minutos por corrida
    # desalientan justamente la práctica que el marco quiere fomentar.
    grupos = trabajo.groupby("ventana", sort=True)
    primero = grupos.first()
    ultimo = grupos.last()
    indice = ultimo.index

    conteos = (
        trabajo[~trabajo["sensor"].isin(temperatura | puertas)]
        .pivot_table(
            index="ventana", columns="zona", aggfunc="size", fill_value=0
        )
        .reindex(index=indice, columns=list(zonas_distintas), fill_value=0)
        .astype(int)
    )
    conteos.columns = [f"conteo_{z}" for z in conteos.columns]

    lecturas = trabajo[trabajo["sensor"].isin(temperatura)]
    temperaturas = (
        lecturas.assign(_v=pd.to_numeric(lecturas["valor"], errors="coerce"))
        .pivot_table(index="ventana", columns="sensor", values="_v", aggfunc="last")
        .reindex(index=indice, columns=list(config.datos.sensores_temperatura))
    )
    temperaturas.columns = [f"temp_{s}" for s in temperaturas.columns]

    marca = ultimo["marca_temporal"]
    caracteristicas = pd.concat([conteos, temperaturas], axis=1)
    caracteristicas["eventos_puerta"] = (
        trabajo[trabajo["sensor"].isin(puertas)]
        .groupby("ventana")
        .size()
        .reindex(indice, fill_value=0)
        .astype(int)
    )
    caracteristicas["hora_del_dia"] = marca.dt.hour.astype(int)
    caracteristicas["dia_semana"] = marca.dt.dayofweek.astype(int)
    caracteristicas["duracion_segundos"] = (
        marca - primero["marca_temporal"]
    ).dt.total_seconds()
    caracteristicas["franja_horaria"] = [
        franja_horaria(h, config.datos.franjas_horarias)
        for h in caracteristicas["hora_del_dia"]
    ]
    caracteristicas["tipo_dia"] = caracteristicas["dia_semana"].map(
        lambda d: "fin_de_semana" if d >= 5 else "laborable"
    )
    caracteristicas["fecha"] = marca.dt.date
    if COLUMNA_HOGAR in trabajo.columns:
        caracteristicas[COLUMNA_HOGAR] = ultimo[COLUMNA_HOGAR]
    caracteristicas[config.datos.columna_objetivo] = ultimo["actividad"]
    caracteristicas = caracteristicas.reset_index(drop=True)

    excluidas = set(config.datos.actividades.excluidas)
    if excluidas:
        caracteristicas = caracteristicas[
            ~caracteristicas[config.datos.columna_objetivo].isin(excluidas)
        ].reset_index(drop=True)

    # Las lecturas de temperatura se arrastran de la ventana anterior: un
    # sensor que no reportó no significa que la temperatura sea desconocida,
    # sino que no cambió.
    columnas_temp = [f"temp_{s}" for s in config.datos.sensores_temperatura]
    caracteristicas[columnas_temp] = caracteristicas[columnas_temp].ffill().bfill()
    return caracteristicas


def columnas_caracteristicas(
    caracteristicas: "pd.DataFrame", config: "Configuracion"
) -> list[str]:
    """Columnas que ve el modelo: ni la etiqueta ni las sensibles ni la fecha."""
    # `hogar` nunca es característica: es clave de agrupación y columna
    # sensible. Que el modelo aprenda a distinguir viviendas sería justamente
    # lo que el análisis desagregado quiere poder descartar.
    excluidas = {config.datos.columna_objetivo, "fecha", COLUMNA_HOGAR} | {
        s.columna for s in config.equidad.subgrupos
    }
    return [c for c in caracteristicas.columns if c not in excluidas]


def particionar(
    df: "pd.DataFrame", config: "Configuracion"
) -> ParticionSupervisada:
    """Realiza la partición train/test de forma determinista.

    Con `estrategia: temporal_por_dia` los últimos días del período van a
    prueba y los primeros a entrenamiento. Los eventos de sensores están
    fuertemente autocorrelacionados: repartir filas al azar deja ventanas
    contiguas del mismo intervalo de actividad a ambos lados de la partición
    y produce una exactitud optimista. Sobre esa exactitud se calculan después
    la explicabilidad y la equidad, así que la fuga contaminaría el expediente
    de evidencia entero.

    Un corte por día, además, es el que refleja el uso real del sistema:
    predecir el comportamiento de mañana con lo aprendido hasta hoy.

    Raises:
        EsquemaDatosInvalido: si la partición dejaría vacío alguno de los dos
            lados.
    """
    if config.datos.particion.estrategia != "temporal_por_dia":
        raise NotImplementedError(
            f"estrategia {config.datos.particion.estrategia!r} todavía no "
            "implementada; use 'temporal_por_dia'"
        )

    if COLUMNA_HOGAR in df.columns:
        # Cada vivienda se parte por sus propios días: así todas aparecen en
        # entrenamiento y en prueba, y el desempeño por hogar es comparable.
        es_prueba = pd.Series(False, index=df.index)
        for hogar, grupo in df.groupby(COLUMNA_HOGAR, sort=True):
            dias_prueba = _dias_de_prueba(sorted(grupo["fecha"].unique()), config, hogar)
            es_prueba |= (df[COLUMNA_HOGAR] == hogar) & df["fecha"].isin(dias_prueba)
    else:
        dias_prueba = _dias_de_prueba(sorted(df["fecha"].unique()), config, None)
        es_prueba = df["fecha"].isin(dias_prueba)
    columnas = columnas_caracteristicas(df, config)
    sensibles = [s.columna for s in config.equidad.subgrupos]
    objetivo = config.datos.columna_objetivo

    entrenamiento, prueba = df[~es_prueba], df[es_prueba]
    if entrenamiento.empty or prueba.empty:
        raise EsquemaDatosInvalido(
            "la partición dejó un lado vacío; revise test_size"
        )

    return ParticionSupervisada(
        X_entrenamiento=entrenamiento[columnas].reset_index(drop=True),
        X_prueba=prueba[columnas].reset_index(drop=True),
        y_entrenamiento=entrenamiento[objetivo].reset_index(drop=True),
        y_prueba=prueba[objetivo].reset_index(drop=True),
        sensibles_entrenamiento=entrenamiento[sensibles].reset_index(drop=True),
        sensibles_prueba=prueba[sensibles].reset_index(drop=True),
    )


def _dias_de_prueba(
    dias: list, config: "Configuracion", hogar: str | None
) -> set:
    """Últimos días del período que van a prueba.

    Raises:
        EsquemaDatosInvalido: si no hay al menos dos días distintos que
            partir.
    """
    if len(dias) < 2:
        de_quien = f" del hogar {hogar}" if hogar else ""
        raise EsquemaDatosInvalido(
            f"se necesitan al menos 2 días distintos para partir por día{de_quien}, "
            f"hay {len(dias)}"
        )
    n_prueba = max(1, round(len(dias) * config.datos.particion.test_size))
    n_prueba = min(n_prueba, len(dias) - 1)
    return set(dias[-n_prueba:])


def hash_dataframe(df: "pd.DataFrame") -> str:
    """Devuelve un hash estable (SHA-256) del contenido de un DataFrame.

    Se usa para sellar la versión de los datos en el manifiesto de evidencia.
    Incluye los nombres de columna: dos tablas con los mismos valores bajo
    nombres distintos no son el mismo dato.
    """
    cabecera = "\x1f".join(map(str, df.columns)).encode("utf-8")
    valores = pd.util.hash_pandas_object(df, index=False).values.tobytes()
    return hash_sha256(cabecera + valores)


def hash_filas(df: "pd.DataFrame") -> list[str]:
    """SHA-256 de cada fila, para la `referencia_entrada` de la bitácora.

    La bitácora no guarda los datos de una vivienda: guarda el hash de la
    fila que produjo la inferencia (R5.1). Incluye los nombres de columna,
    igual que `hash_dataframe`: dos filas con los mismos valores bajo nombres
    distintos no son la misma entrada.

    El hash es estable dentro del entorno fijado en `requirements.txt`, que
    es el que el manifiesto declara.
    """
    cabecera = "\x1f".join(map(str, df.columns))
    return [
        hash_sha256("\x1f".join([cabecera, *map(repr, fila)]).encode("utf-8"))
        for fila in df.itertuples(index=False, name=None)
    ]


class EsquemaDatosInvalido(ValueError):
    """El dataset crudo no cumple el esquema esperado."""
