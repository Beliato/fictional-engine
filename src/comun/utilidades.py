"""Utilidades transversales: hashing, tiempo UTC, E/S de artefactos."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Bloque de lectura para el hashing de archivos. 1 MiB: suficiente para que la
# sobrecarga de llamadas sea despreciable sin cargar el archivo en memoria.
_BLOQUE = 1024 * 1024


def ahora_utc_iso() -> str:
    """Devuelve la marca temporal actual en UTC, formato ISO 8601 con sufijo Z.

    Se usa para todas las marcas de tiempo del proyecto: nunca hora local. Una
    bitácora con marcas en hora local sería inauditable en cuanto el sistema
    cambiara de zona o de horario de verano.
    """
    marca = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    # `isoformat` produce "+00:00"; la bitácora usa el sufijo Z, más corto y
    # el que espera el verificador.
    return marca.replace("+00:00", "Z")


def hash_sha256(datos: bytes) -> str:
    """SHA-256 en hexadecimal de una secuencia de bytes."""
    return hashlib.sha256(datos).hexdigest()


def hash_archivo(ruta: str | Path) -> str:
    """SHA-256 en hexadecimal del contenido de un archivo, leído por bloques.

    Raises:
        FileNotFoundError: si `ruta` no existe.
    """
    digest = hashlib.sha256()
    with Path(ruta).open("rb") as f:
        while bloque := f.read(_BLOQUE):
            digest.update(bloque)
    return digest.hexdigest()


def escribir_json(ruta: str | Path, obj: Any) -> None:
    """Serializa `obj` a JSON determinista y lo escribe en `ruta`.

    Determinista significa: claves ordenadas, UTF-8 sin escapar, sangría fija
    y salto de línea final. Dos ejecuciones equivalentes deben producir
    archivos byte a byte idénticos, o el manifiesto de evidencia no sirve para
    comparar corridas.
    """
    ruta = Path(ruta)
    asegurar_directorio(ruta.parent)
    with ruta.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")


def asegurar_directorio(ruta: str | Path) -> Path:
    """Crea el directorio `ruta` (y sus padres) si no existe y lo devuelve."""
    directorio = Path(ruta)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio
