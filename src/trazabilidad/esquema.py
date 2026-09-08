"""Esquema del registro de trazabilidad de inferencias.

Cada línea del archivo JSONL de la bitácora es un objeto conforme a
`RegistroInferencia`. El esquema está versionado (`VERSION_ESQUEMA`): todo
cambio incompatible obliga a subir la versión mayor y a documentarlo.

A diferencia del resto de módulos (que son esqueletos), aquí el esquema y su
(de)serialización SÍ están implementados: son la "estructura" que se pide
revisar y no contienen lógica de negocio.
"""

from __future__ import annotations

import json
from dataclasses import MISSING, asdict, dataclass, field, fields
from typing import Any

VERSION_ESQUEMA = "1.0.0"


@dataclass(frozen=True)
class RegistroInferencia:
    """Una fila de la bitácora: todo lo necesario para auditar una inferencia.

    Campos:
        id_evento: identificador único del evento/inferencia (p. ej. UUID o
            id del evento de sensor CASAS).
        marca_temporal: instante de la inferencia, ISO 8601 en UTC (sufijo Z).
        referencia_entrada: puntero a la entrada procesada — hash SHA-256 de
            la fila de características usada como input (no se guardan datos
            crudos personales en la bitácora, solo su hash).
        salida_modelo: etiqueta o valor predicho por el modelo.
        confianza: probabilidad/score asociado a `salida_modelo`, en [0, 1].
        version_modelo: versión semántica del modelo que produjo la salida
            (`config.modelo.version`).
        version_marco: versión del marco operativo (`config.version_marco`).
        referencia_explicacion: puntero al artefacto de explicación local
            generado para esta inferencia (ruta relativa o id).
        responsable: persona/rol declarado como responsable de esta inferencia
            (`config.trazabilidad.responsable_por_defecto` u override).
        version_esquema: versión de este esquema (se rellena automáticamente).
        metadatos: campo abierto para contexto adicional no estructurado.
    """

    id_evento: str
    marca_temporal: str
    referencia_entrada: str
    salida_modelo: str
    confianza: float
    version_modelo: str
    version_marco: str
    referencia_explicacion: str
    responsable: str
    version_esquema: str = VERSION_ESQUEMA
    metadatos: dict[str, Any] = field(default_factory=dict)

    def a_linea_jsonl(self) -> str:
        """Serializa el registro a una línea JSON (claves ordenadas, UTF-8)."""
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    @classmethod
    def desde_diccionario(cls, datos: dict[str, Any]) -> "RegistroInferencia":
        """Reconstruye un registro desde un dict (una línea ya parseada).

        Raises:
            RegistroInvalido: si faltan campos obligatorios o sobran campos
                desconocidos.
        """
        nombres = {f.name for f in fields(cls)}
        obligatorios = {
            f.name
            for f in fields(cls)
            if f.default is MISSING and f.default_factory is MISSING
        }
        faltantes = obligatorios - datos.keys()
        desconocidos = datos.keys() - nombres
        if faltantes or desconocidos:
            raise RegistroInvalido(
                f"faltantes={sorted(faltantes)} desconocidos={sorted(desconocidos)}"
            )
        return cls(**datos)  # type: ignore[arg-type]


class RegistroInvalido(ValueError):
    """Una línea de la bitácora no cumple el esquema."""
