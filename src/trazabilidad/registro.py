"""Escritura del registro estructurado de inferencias (bitácora JSONL).

Diseño append-only: cada inferencia añade una línea; nunca se reescriben
líneas anteriores. Esto hace la bitácora verificable y a prueba de
manipulación accidental.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Iterator

from src.trazabilidad.esquema import RegistroInferencia

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

        TODO: guardar la ruta, crear el directorio padre, no truncar el
            archivo si ya existe.
        """
        raise NotImplementedError

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
            ValueError: si `confianza` no está en [0, 1] o algún campo vacío.

        TODO:
            - Construir el registro.
            - Serializar con `a_linea_jsonl()` y hacer append con un `\\n`.
            - `flush()` + `os.fsync` para durabilidad.
        """
        raise NotImplementedError

    def registrar_lote(
        self, registros: Iterable[dict]
    ) -> list[RegistroInferencia]:
        """Versión por lotes de `registrar`, para inferencia sobre el set de
        prueba completo. Mantiene el orden de entrada.

        TODO: iterar y delegar en `registrar`.
        """
        raise NotImplementedError


def leer_registros(ruta: str | Path) -> Iterator[RegistroInferencia]:
    """Itera los registros de una bitácora JSONL ya existente.

    Args:
        ruta: archivo JSONL a leer.

    Yields:
        Un `RegistroInferencia` por línea.

    Raises:
        FileNotFoundError: si `ruta` no existe.
        src.trazabilidad.esquema.RegistroInvalido: si una línea no cumple el
            esquema.

    TODO: abrir el archivo, parsear cada línea con `json.loads` y
        `RegistroInferencia.desde_diccionario`.
    """
    raise NotImplementedError
