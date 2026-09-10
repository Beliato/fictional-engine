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


#: Lectores disponibles, por el nombre con que se declaran en `config.yaml`.
#: Registrar uno nuevo aquí es todo lo que hace falta para que el marco
#: acepte otro formato; ningún otro módulo cambia.
LECTORES: dict[str, type[LectorEventos]] = {
    LectorEventosCASAS.nombre: LectorEventosCASAS,
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
    if tuple(eventos.columns) != COLUMNAS_EVENTOS:
        raise ContratoIncumplido(
            f"{quien}: las columnas deben ser exactamente "
            f"{list(COLUMNAS_EVENTOS)}, se recibió {list(eventos.columns)}"
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
    if not eventos["marca_temporal"].is_monotonic_increasing:
        raise ContratoIncumplido(
            f"{quien}: los eventos deben venir ordenados por marca_temporal; "
            "la ventana y la partición temporal dependen de ese orden"
        )


class FormatoNoReconocido(ValueError):
    """El formato declarado no existe, o el archivo no corresponde a él."""


class ContratoIncumplido(TypeError):
    """Un lector devolvió algo que no cumple el contrato de eventos."""
