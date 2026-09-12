"""Contrato de ingesta: cómo entra cualquier dataset de sensores al marco.

El marco operativo se aplica a *sistemas de IA basados en sensores PIR*, no a
un dataset concreto. Este módulo es la costura entre ambos: define qué le
exige el marco a una fuente de datos, y aísla en un lector todo lo que sea
propio de un formato.

El contrato
-----------
Un lector devuelve un DataFrame de **eventos normalizados** con exactamente
estas columnas, ordenado por tiempo:

    marca_temporal : datetime64   instante del evento
    sensor         : str          identificador del sensor que lo emitió
    valor          : str          estado reportado (ON/OFF, OPEN/CLOSE, 21.5…)
    actividad      : str          etiqueta vigente en ese instante

Y una quinta columna **opcional**:

    hogar          : str          vivienda de la que provino el evento

`hogar` aparece cuando el dataset cubre varias viviendas. No es una
característica del modelo: es una clave de agrupación —las ventanas nunca
cruzan hogares y la partición temporal se hace dentro de cada uno— y una
columna sensible para el análisis desagregado. Cada vivienda es una persona
distinta, así que comparar entre hogares es comparar entre la población
monitoreada, que es lo que pide el R4.1.

Todo lo que va aguas abajo —ventanas, conteos por zona, partición temporal,
modelo, atribución SHAP, equidad, bitácora— opera sobre esa forma y no sabe
de dónde salió. Y la forma no es una abstracción inventada: **todo sistema de
sensores pasivos es un flujo de (cuándo, qué sensor, qué estado)**.

Aplicar el marco a otro dataset
-------------------------------
No se edita `datos.py`: se escribe un lector nuevo, se registra en `LECTORES`
y se declara en `config.yaml` (`datos.formato`). El resto del marco no se
entera, que es la condición para que los resultados sigan siendo comparables
entre sistemas evaluados por equipos distintos.

`leer_eventos` valida el contrato sobre lo que devuelve el lector, así que un
adaptador mal escrito falla en la costura y no tres pasos más adelante, con
un error que ya no señala la causa.

Ver `docs/aplicar-a-otro-dataset.md`.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion

# Las cuatro columnas del contrato, en orden.
COLUMNAS_EVENTOS = ("marca_temporal", "sensor", "valor", "actividad")

#: Columna opcional del contrato: vivienda de origen del evento.
COLUMNA_HOGAR = "hogar"


class LectorEventos(ABC):
    """Adaptador entre un formato de origen y el contrato de eventos."""

    #: Nombre con el que se declara en `config.yaml` (`datos.formato`).
    nombre: str

    #: Descripción del formato que acepta, para los mensajes de error y el
    #: datasheet.
    formato: str

    @abstractmethod
    def leer(self, config: "Configuracion") -> pd.DataFrame:
        """Lee `config.datos.archivo_crudo` y devuelve eventos normalizados.

        La implementación es libre en todo salvo en el resultado, que debe
        cumplir el contrato descrito en el módulo. `leer_eventos` lo verifica.
        """


class LectorEventosCASAS(LectorEventos):
    """Lector del flujo de eventos de CASAS (WSU).

    Un evento por línea, campos separados por espacios; la anotación de
    actividad marca el inicio y el fin de un intervalo:

        2010-11-04 00:03:50.209589 M003 ON Sleeping begin
        2010-11-04 00:03:57.399391 M003 OFF

    Los eventos intermedios no llevan etiqueta: heredan la actividad abierta.
    Los que caen fuera de todo intervalo reciben
    `config.datos.actividades.etiqueta_sin_actividad`.
    """

    nombre = "casas_eventos"
    formato = "flujo de eventos CASAS separado por espacios, anotado por spans"

    #: Vocabulario de anotación propio de CASAS.
    MARCAS = ("begin", "end")

    def leer(self, config: "Configuracion") -> pd.DataFrame:
        ruta = Path(config.datos.archivo_crudo)
        if not ruta.is_file():
            raise FileNotFoundError(f"no existe el archivo crudo: {ruta}")

        conocidos = (
            set(config.datos.columnas_sensor_pir)
            | set(config.datos.sensores_puerta)
            | set(config.datos.sensores_temperatura)
        )
        etiqueta_vacia = config.datos.actividades.etiqueta_sin_actividad

        marcas: list[str] = []
        sensores: list[str] = []
        valores: list[str] = []
        actividades: list[str] = []
        abierta = etiqueta_vacia
        descartadas = 0

        with ruta.open("r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                campos = re.split(r"\s+", linea.strip())
                if len(campos) < 4 or campos[2] not in conocidos:
                    # Aruba trae unas pocas líneas donde el nombre de la
                    # actividad se coló en la columna de sensor. Se descartan
                    # y se cuentan: perderlas en silencio sería falsear la
                    # composición que declara el datasheet.
                    if linea.strip():
                        descartadas += 1
                    continue
                fecha, hora, sensor, valor = campos[:4]
                marcas.append(f"{fecha} {hora}")
                sensores.append(sensor)
                valores.append(valor)

                # El evento que cierra un intervalo pertenece todavía a la
                # actividad que termina.
                actividades.append(abierta)
                if len(campos) >= 6 and campos[-1].lower() in self.MARCAS:
                    nombre = " ".join(campos[4:-1])
                    if campos[-1].lower() == "begin":
                        abierta = nombre
                        actividades[-1] = nombre
                    else:
                        abierta = etiqueta_vacia

        if not marcas:
            raise FormatoNoReconocido(
                f"{ruta}: no se encontró ningún evento con un sensor "
                f"declarado en config.datos. ¿Es el archivo correcto, y "
                f"corresponde al formato {self.nombre!r}?"
            )

        eventos = pd.DataFrame(
            {
                "marca_temporal": pd.to_datetime(marcas, format="mixed"),
                "sensor": sensores,
                "valor": valores,
                "actividad": actividades,
            }
        )
        # El crudo de CASAS no viene perfectamente ordenado. Ordenar es
        # responsabilidad del lector, no del marco: el contrato exige eventos
        # en orden y cada formato sabe cómo llegar a eso. El orden es estable
        # para que dos eventos con la misma marca conserven el del archivo,
        # que es el único desempate reproducible disponible.
        eventos = eventos.sort_values(
            "marca_temporal", kind="stable"
        ).reset_index(drop=True)
        eventos.attrs["lineas_descartadas"] = descartadas
        return eventos


class LectorEventosCASASCSV(LectorEventos):
    """Lector del release de CASAS publicado en Zenodo (CSV, varias viviendas).

    Un evento por línea, campos separados por coma, con los sensores ya
    nombrados por habitación. La anotación de actividad abre y cierra
    intervalos con una sintaxis propia:

        2012-07-20,10:38:54.512364,OutsideDoor,ON,Step_Out="begin"
        2012-07-20,10:38:59.541365,OutsideDoor,OFF
        2012-07-20,10:39:36.167078,Bedroom,ON,Sleep

    El quinto campo puede traer `Actividad="begin"`, `Actividad="end"` o el
    nombre a secas para los eventos interiores del intervalo.

    `datos.archivo_crudo` puede apuntar a un archivo o a un **directorio**: en
    ese caso se leen todos sus `.csv` en orden y el nombre de cada archivo
    pasa a la columna `hogar`.

    Un detalle propio de este formato: un mismo nombre de sensor puede ser de
    movimiento y de puerta a la vez (`OutsideDoor` reporta ON/OFF y también
    OPEN/CLOSE). Como el marco distingue los sensores por nombre, los eventos
    de puerta se renombran a `<sensor>_Puerta`. La ambigüedad es del dataset y
    se resuelve acá, que es donde vive lo propio de cada formato.
    """

    nombre = "casas_csv"
    formato = "CSV de CASAS (Zenodo), una o varias viviendas anotadas por spans"

    #: Valores que identifican un evento de puerta y no de movimiento.
    VALORES_PUERTA = ("OPEN", "CLOSE")

    #: Sufijo con el que se desdobla un sensor que también es puerta.
    SUFIJO_PUERTA = "_Puerta"

    def leer(self, config: "Configuracion") -> pd.DataFrame:
        ruta = Path(config.datos.archivo_crudo)
        archivos = self._archivos(ruta)
        etiqueta_vacia = config.datos.actividades.etiqueta_sin_actividad

        marcos = []
        descartadas = 0
        for archivo in archivos:
            eventos, sin_parsear = self._leer_uno(archivo, etiqueta_vacia)
            descartadas += sin_parsear
            if not eventos.empty:
                marcos.append(eventos)

        if not marcos:
            raise FormatoNoReconocido(
                f"{ruta}: no se encontró ningún evento legible. ¿Es la ruta "
                f"correcta, y corresponde al formato {self.nombre!r}?"
            )

        eventos = pd.concat(marcos, ignore_index=True)
        # Orden estable dentro de cada hogar: el contrato lo exige y la
        # ventana y la partición dependen de él.
        eventos = eventos.sort_values(
            [COLUMNA_HOGAR, "marca_temporal"], kind="stable"
        ).reset_index(drop=True)
        eventos.attrs["lineas_descartadas"] = descartadas
        eventos.attrs["hogares"] = sorted(eventos[COLUMNA_HOGAR].unique())
        return eventos[[*COLUMNAS_EVENTOS, COLUMNA_HOGAR]]

    def _archivos(self, ruta: Path) -> list[Path]:
        if ruta.is_dir():
            archivos = sorted(ruta.glob("*.csv"))
            if not archivos:
                raise FileNotFoundError(f"no hay archivos .csv en {ruta}")
            return archivos
        if ruta.is_file():
            return [ruta]
        raise FileNotFoundError(f"no existe el archivo crudo: {ruta}")

    def _leer_uno(
        self, archivo: Path, etiqueta_vacia: str
    ) -> "tuple[pd.DataFrame, int]":
        marcas: list[str] = []
        sensores: list[str] = []
        valores: list[str] = []
        actividades: list[str] = []
        abierta = etiqueta_vacia
        descartadas = 0

        with archivo.open("r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                campos = linea.rstrip("\n").split(",")
                if len(campos) < 4 or not campos[0] or not campos[2]:
                    if linea.strip():
                        descartadas += 1
                    continue
                fecha, hora, sensor, valor = (c.strip() for c in campos[:4])
                if valor.upper() in self.VALORES_PUERTA:
                    sensor = f"{sensor}{self.SUFIJO_PUERTA}"
                marcas.append(f"{fecha} {hora}")
                sensores.append(sensor)
                valores.append(valor)

                anotacion = campos[4].strip() if len(campos) > 4 else ""
                nombre, marca = self._anotacion(anotacion)
                if not nombre:
                    actividades.append(abierta)
                elif marca == "begin":
                    abierta = nombre
                    actividades.append(nombre)
                elif marca == "end":
                    actividades.append(nombre)
                    abierta = etiqueta_vacia
                else:
                    actividades.append(nombre)

        eventos = pd.DataFrame(
            {
                "marca_temporal": pd.to_datetime(marcas, format="mixed"),
                "sensor": sensores,
                "valor": valores,
                "actividad": actividades,
                COLUMNA_HOGAR: archivo.stem,
            }
        )
        return eventos, descartadas

    def _anotacion(self, campo: str) -> "tuple[str, str]":
        """Descompone `Actividad="begin"` en (actividad, marca)."""
        if not campo:
            return "", ""
        nombre, _, resto = campo.partition("=")
        return nombre.strip(), resto.strip().strip(chr(34)).lower()


#: Lectores disponibles, por el nombre con que se declaran en `config.yaml`.
#: Registrar uno nuevo aquí es todo lo que hace falta para que el marco
#: acepte otro formato; ningún otro módulo cambia.
LECTORES: dict[str, type[LectorEventos]] = {
    LectorEventosCASAS.nombre: LectorEventosCASAS,
    LectorEventosCASASCSV.nombre: LectorEventosCASASCSV,
}


def obtener_lector(config: "Configuracion") -> LectorEventos:
    """Instancia el lector declarado en `config.datos.formato`.

    Raises:
        FormatoNoReconocido: si el formato no está registrado.
    """
    formato = config.datos.formato
    if formato not in LECTORES:
        raise FormatoNoReconocido(
            f"datos.formato: {formato!r} no está registrado. Disponibles: "
            f"{sorted(LECTORES)}. Para añadir un formato, implemente "
            f"LectorEventos y regístrelo en LECTORES (ver "
            f"docs/aplicar-a-otro-dataset.md)."
        )
    return LECTORES[formato]()


def leer_eventos(config: "Configuracion") -> pd.DataFrame:
    """Lee el crudo con el lector declarado y **verifica el contrato**.

    La verificación es lo que convierte el contrato en una garantía: un
    adaptador mal escrito falla acá, en la costura, y no tres pasos más
    adelante con un error que ya no señala la causa.

    Raises:
        FileNotFoundError: si no existe el archivo crudo.
        FormatoNoReconocido: si el formato no está registrado o el archivo no
            corresponde al formato declarado.
        ContratoIncumplido: si el lector devolvió algo que no cumple el
            contrato de eventos.
    """
    lector = obtener_lector(config)
    eventos = lector.leer(config)
    _verificar_contrato(eventos, lector)
    return eventos


def _verificar_contrato(eventos: object, lector: LectorEventos) -> None:
    """Comprueba que `eventos` cumple el contrato de este módulo."""
    quien = type(lector).__name__

    if not isinstance(eventos, pd.DataFrame):
        raise ContratoIncumplido(
            f"{quien}: debía devolver un DataFrame, devolvió "
            f"{type(eventos).__name__}"
        )
    admitidas = (COLUMNAS_EVENTOS, (*COLUMNAS_EVENTOS, COLUMNA_HOGAR))
    if tuple(eventos.columns) not in admitidas:
        raise ContratoIncumplido(
            f"{quien}: las columnas deben ser {list(COLUMNAS_EVENTOS)}, "
            f"opcionalmente seguidas de {COLUMNA_HOGAR!r}; se recibió "
            f"{list(eventos.columns)}"
        )
    if eventos.empty:
        raise ContratoIncumplido(f"{quien}: no devolvió ningún evento")
    if not pd.api.types.is_datetime64_any_dtype(eventos["marca_temporal"]):
        raise ContratoIncumplido(
            f"{quien}: marca_temporal debe ser datetime64, es "
            f"{eventos['marca_temporal'].dtype}"
        )
    for columna in ("sensor", "valor", "actividad"):
        if eventos[columna].isna().any():
            raise ContratoIncumplido(f"{quien}: {columna} contiene nulos")
    if COLUMNA_HOGAR not in eventos.columns:
        if not eventos["marca_temporal"].is_monotonic_increasing:
            raise ContratoIncumplido(
                f"{quien}: los eventos deben venir ordenados por "
                "marca_temporal; la ventana y la partición temporal dependen "
                "de ese orden"
            )
        return

    if eventos[COLUMNA_HOGAR].isna().any():
        raise ContratoIncumplido(f"{quien}: {COLUMNA_HOGAR} contiene nulos")
    # Con varias viviendas el orden global no significa nada: lo que la
    # ventana y la partición necesitan es orden dentro de cada hogar, y que
    # cada hogar venga en un bloque contiguo.
    bloques = int((eventos[COLUMNA_HOGAR] != eventos[COLUMNA_HOGAR].shift()).sum())
    if bloques != eventos[COLUMNA_HOGAR].nunique():
        raise ContratoIncumplido(
            f"{quien}: los eventos de cada hogar deben venir juntos; hay "
            f"{bloques} bloques para {eventos[COLUMNA_HOGAR].nunique()} hogares"
        )
    ordenado = (
        eventos.groupby(COLUMNA_HOGAR, sort=False)["marca_temporal"]
        .is_monotonic_increasing.all()
    )
    if not ordenado:
        raise ContratoIncumplido(
            f"{quien}: dentro de cada hogar los eventos deben venir ordenados "
            "por marca_temporal"
        )


class FormatoNoReconocido(ValueError):
    """El formato declarado no existe, o el archivo no corresponde a él."""


class ContratoIncumplido(TypeError):
    """Un lector devolvió algo que no cumple el contrato de eventos."""
