"""Escritura del registro estructurado de inferencias (bitácora JSONL).

Diseño append-only: cada inferencia añade una línea; nunca se reescriben
líneas anteriores. Esto hace la bitácora verificable y a prueba de
manipulación accidental.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator, TextIO

from src.comun.utilidades import ahora_utc_iso, asegurar_directorio
from src.trazabilidad.esquema import (
    VERSION_ESQUEMA,
    RegistroInferencia,
    RegistroInvalido,
)

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion


class RegistroEstructurado:
    """Escritor append-only de la bitácora de inferencias en formato JSONL."""

    def __init__(self, ruta: str | Path, config: "Configuracion") -> None:
        """Inicializa el escritor.

        Args:
            ruta: archivo JSONL destino (`config.rutas.registro_inferencias`).
            config: configuración del marco (para versión de esquema,
                responsable por defecto, versiones de modelo/marco).

        Raises:
            ValueError: si la versión de esquema declarada en `config` no
                coincide con la del código. Una bitácora escrita bajo una
                versión y verificada contra otra no es evidencia de nada, así
                que la discrepancia se detecta antes de escribir la primera
                línea y no al auditar.
        """
        if config.trazabilidad.version_esquema != VERSION_ESQUEMA:
            raise ValueError(
                "la versión de esquema de la configuración "
                f"({config.trazabilidad.version_esquema!r}) no coincide con la "
                f"del código ({VERSION_ESQUEMA!r})"
            )
        self.ruta = Path(ruta)
        self.config = config
        asegurar_directorio(self.ruta.parent)

    # --- API pública ---------------------------------------------------------

    def registrar(
        self,
        *,
        id_evento: str,
        referencia_entrada: str,
        salida_modelo: str,
        confianza: float,
        referencia_explicacion: str,
        responsable: str | None = None,
    ) -> RegistroInferencia:
        """Construye un `RegistroInferencia`, lo valida y lo añade a la bitácora.

        Rellena automáticamente: `marca_temporal` (UTC ahora), `version_modelo`
        y `version_marco` (desde config), `version_esquema`. Si `responsable`
        es None usa `config.trazabilidad.responsable_por_defecto`.

        Returns:
            El registro efectivamente escrito.

        Raises:
            ValueError: si `confianza` no está en [0, 1] o algún campo está
                vacío.
        """
        registro = self._construir(
            id_evento=id_evento,
            referencia_entrada=referencia_entrada,
            salida_modelo=salida_modelo,
            confianza=confianza,
            referencia_explicacion=referencia_explicacion,
            responsable=responsable,
        )
        with self.ruta.open("a", encoding="utf-8", newline="\n") as f:
            self._volcar(f, registro)
            _sincronizar(f)
        return registro

    def registrar_lote(
        self, registros: Iterable[dict]
    ) -> list[RegistroInferencia]:
        """Versión por lotes de `registrar`. Mantiene el orden de entrada.

        Todos los registros se construyen y validan **antes** de escribir el
        primero: si uno es inválido no se escribe ninguno. En una bitácora
        append-only no hay forma de retirar una línea ya escrita, así que un
        lote a medias dejaría evidencia que no se puede corregir sin romper la
        garantía de inmutabilidad.

        El `fsync` se hace una sola vez al final del lote: la durabilidad
        resultante es la misma para el conjunto y evita un fsync por fila.

        Raises:
            ValueError: si algún registro del lote es inválido.
        """
        construidos = [
            self._construir(**campos) for campos in registros
        ]
        if not construidos:
            return []
        with self.ruta.open("a", encoding="utf-8", newline="\n") as f:
            for registro in construidos:
                self._volcar(f, registro)
            _sincronizar(f)
        return construidos

    # --- Interno -------------------------------------------------------------

    def _construir(
        self,
        *,
        id_evento: str,
        referencia_entrada: str,
        salida_modelo: str,
        confianza: float,
        referencia_explicacion: str,
        responsable: str | None = None,
        metadatos: dict[str, Any] | None = None,
    ) -> RegistroInferencia:
        """Completa los campos automáticos y valida el registro."""
        if isinstance(confianza, bool) or not isinstance(confianza, (int, float)):
            raise ValueError(
                f"confianza: se esperaba un número, se recibió "
                f"{type(confianza).__name__}"
            )
        if not 0.0 <= confianza <= 1.0:
            raise ValueError(
                f"confianza: debe estar en [0, 1], se recibió {confianza}"
            )

        responsable = (
            responsable
            if responsable is not None
            else self.config.trazabilidad.responsable_por_defecto
        )
        obligatorios = {
            "id_evento": id_evento,
            "referencia_entrada": referencia_entrada,
            "salida_modelo": salida_modelo,
            "referencia_explicacion": referencia_explicacion,
            "responsable": responsable,
        }
        for campo, valor in obligatorios.items():
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"{campo}: no puede estar vacío")

        return RegistroInferencia(
            id_evento=id_evento,
            marca_temporal=ahora_utc_iso(),
            referencia_entrada=referencia_entrada,
            salida_modelo=salida_modelo,
            confianza=float(confianza),
            version_modelo=self.config.modelo.version,
            version_marco=self.config.version_marco,
            referencia_explicacion=referencia_explicacion,
            responsable=responsable,
            metadatos=dict(metadatos or {}),
        )

    @staticmethod
    def _volcar(f: TextIO, registro: RegistroInferencia) -> None:
        f.write(registro.a_linea_jsonl())
        f.write("\n")


def _sincronizar(f: TextIO) -> None:
    """Fuerza el volcado a disco de lo ya escrito en `f`.

    Sin esto, una caída del proceso puede perder inferencias que el sistema
    ya dio por registradas — y una bitácora con huecos no evidencia nada.
    """
    f.flush()
    os.fsync(f.fileno())


def leer_registros(ruta: str | Path) -> Iterator[RegistroInferencia]:
    """Itera los registros de una bitácora JSONL ya existente.

    Args:
        ruta: archivo JSONL a leer.

    Yields:
        Un `RegistroInferencia` por línea. Las líneas en blanco se ignoran.

    Raises:
        FileNotFoundError: si `ruta` no existe. Se comprueba de inmediato, no
            al consumir el primer elemento.
        RegistroInvalido: si una línea no es JSON válido o no cumple el
            esquema. El mensaje incluye el número de línea.
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe la bitácora: {ruta}")
    return _iterar_registros(ruta)


def _iterar_registros(ruta: Path) -> Iterator[RegistroInferencia]:
    with ruta.open("r", encoding="utf-8") as f:
        for n, linea in enumerate(f, start=1):
            if not linea.strip():
                continue
            try:
                datos = json.loads(linea)
            except json.JSONDecodeError as exc:
                raise RegistroInvalido(
                    f"{ruta}:{n}: JSON mal formado: {exc}"
                ) from exc
            if not isinstance(datos, dict):
                raise RegistroInvalido(
                    f"{ruta}:{n}: se esperaba un objeto JSON, se recibió "
                    f"{type(datos).__name__}"
                )
            try:
                yield RegistroInferencia.desde_diccionario(datos)
            except RegistroInvalido as exc:
                raise RegistroInvalido(f"{ruta}:{n}: {exc}") from exc
