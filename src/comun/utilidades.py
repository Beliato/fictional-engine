"""Utilidades transversales: hashing, tiempo UTC, E/S de artefactos."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def ahora_utc_iso() -> str:
    """Devuelve la marca temporal actual en UTC, formato ISO 8601 con sufijo Z.

    Se usa para todas las marcas de tiempo del proyecto: nunca hora local.

    TODO: `datetime.now(timezone.utc).isoformat(timespec="milliseconds")`.
    """
    raise NotImplementedError


def hash_sha256(datos: bytes) -> str:
    """SHA-256 en hexadecimal de una secuencia de bytes.

    TODO: `hashlib.sha256(datos).hexdigest()`.
    """
    raise NotImplementedError


def hash_archivo(ruta: str | Path) -> str:
    """SHA-256 en hexadecimal del contenido de un archivo, leído por bloques.

    TODO: leer en chunks para no cargar archivos grandes en memoria.
    """
    raise NotImplementedError


def escribir_json(ruta: str | Path, obj: Any) -> None:
    """Serializa `obj` a JSON de forma determinista (claves ordenadas,
    codificación UTF-8, salto de línea final) y lo escribe en `ruta`,
    creando los directorios intermedios.

    TODO: `json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)`.
    """
    raise NotImplementedError


def asegurar_directorio(ruta: str | Path) -> Path:
    """Crea el directorio `ruta` (y sus padres) si no existe y lo devuelve.

    TODO: `Path(ruta).mkdir(parents=True, exist_ok=True)`.
    """
    raise NotImplementedError
