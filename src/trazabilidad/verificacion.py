"""Verificación de integridad y completitud de la bitácora de inferencias.

Responde a la pregunta de auditoría: "¿el registro es confiable y está
completo?". Ejecutable de forma independiente:

    python -m src.trazabilidad.verificacion --config config.yaml
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.trazabilidad.esquema import RegistroInferencia, RegistroInvalido
from src.trazabilidad.registro import leer_registros

if TYPE_CHECKING:
    from src.comun.configuracion import Configuracion

# Un `responsable` con este texto delata la plantilla sin rellenar. El
# principio de responsabilidad exige atribución a una persona física o
# jurídica identificable: "TODO: Nombre Apellido" no atribuye nada.
_MARCA_PLACEHOLDER = "TODO"


@dataclass(frozen=True)
class InformeVerificacion:
    """Resultado de verificar una bitácora."""

    ruta: Path
    n_registros: int
    valido: bool
    problemas: list[str] = field(default_factory=list)

    def resumen(self) -> str:
        """Devuelve un resumen legible del informe."""
        estado = "VÁLIDA" if self.valido else "NO VÁLIDA"
        lineas = [
            f"Bitácora: {self.ruta}",
            f"Registros: {self.n_registros}",
            f"Estado: {estado}",
        ]
        if self.problemas:
            lineas.append(f"Problemas ({len(self.problemas)}):")
            lineas.extend(f"  - {p}" for p in self.problemas)
        return "\n".join(lineas)


def _marca_temporal_utc(valor: str) -> datetime | None:
    """Parsea una marca ISO 8601 y exige que sea UTC. `None` si no lo es."""
    try:
        momento = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    if momento.utcoffset() is None or momento.utcoffset().total_seconds() != 0:
        return None
    return momento


def _ruta_explicacion(
    referencia: str, config: "Configuracion"
) -> tuple[Path, str | None]:
    """Resuelve una referencia de explicación a `(archivo, fragmento)`.

    Dos formas admitidas:

        artefactos/explicaciones/e.json                  un archivo por explicación
        artefactos/explicaciones/local/e.jsonl#evt-001   un registro de un
                                                          artefacto consolidado

    En la segunda, el fragmento es el `id_evento` de una línea del JSONL. Las
    rutas se guardan relativas a la raíz del repositorio para que la bitácora
    siga siendo verificable al moverla de máquina.
    """
    archivo, _, fragmento = referencia.partition("#")
    ruta = Path(archivo)
    if not ruta.is_absolute():
        ruta = config.rutas.artefactos.parent / ruta
    return ruta, (fragmento or None)


def _ids_en_artefacto(
    ruta: Path, cache: dict[Path, set[str] | None]
) -> set[str] | None:
    """`id_evento` presentes en un artefacto JSONL consolidado.

    Cada archivo se lee una sola vez: una bitácora de 11.000 inferencias
    referencia 11.000 veces el mismo artefacto. Devuelve `None` si el archivo
    no se puede leer como JSONL con `id_evento` por línea.
    """
    if ruta not in cache:
        try:
            with ruta.open("r", encoding="utf-8") as f:
                cache[ruta] = {
                    str(json.loads(linea)["id_evento"])
                    for linea in f
                    if linea.strip()
                }
        except (OSError, ValueError, KeyError, TypeError):
            cache[ruta] = None
    return cache[ruta]


def verificar_registro(
    ruta: str | Path, config: "Configuracion"
) -> InformeVerificacion:
    """Verifica una bitácora JSONL completa.

    Comprobaciones:
        - Toda línea es JSON válido y conforme al esquema.
        - `version_esquema` coincide con `config.trazabilidad.version_esquema`.
        - `id_evento` sin duplicados.
        - `marca_temporal` en ISO 8601 UTC y en orden no decreciente.
        - `confianza` en [0, 1].
        - `version_modelo` == `config.modelo.version` para todos los registros.
        - `referencia_explicacion` apunta a un artefacto existente y, si es
          un artefacto consolidado (`archivo#id_evento`), el registro está
          adentro (si `config.explicabilidad.guardar_local_por_inferencia`).
        - `responsable` no vacío ni con el texto placeholder "TODO".

    Una bitácora vacía se reporta como no válida: el registro es el sustrato
    de la rendición de cuentas, y cero inferencias registradas no evidencian
    el comportamiento de nada.

    Returns:
        El `InformeVerificacion` con la lista de problemas encontrados.
    """
    ruta = Path(ruta)
    problemas: list[str] = []

    try:
        registros = list(leer_registros(ruta))
    except FileNotFoundError:
        return InformeVerificacion(
            ruta=ruta,
            n_registros=0,
            valido=False,
            problemas=[f"no existe la bitácora: {ruta}"],
        )
    except RegistroInvalido as exc:
        return InformeVerificacion(
            ruta=ruta, n_registros=0, valido=False, problemas=[str(exc)]
        )

    if not registros:
        return InformeVerificacion(
            ruta=ruta,
            n_registros=0,
            valido=False,
            problemas=["la bitácora está vacía: no hay inferencias registradas"],
        )

    vistos: set[str] = set()
    anterior: datetime | None = None
    artefactos: dict[Path, set[str] | None] = {}

    for n, registro in enumerate(registros, start=1):
        etiqueta = f"registro {n} (id_evento={registro.id_evento!r})"

        if registro.version_esquema != config.trazabilidad.version_esquema:
            problemas.append(
                f"{etiqueta}: version_esquema {registro.version_esquema!r} != "
                f"{config.trazabilidad.version_esquema!r} declarada en config"
            )

        if registro.id_evento in vistos:
            problemas.append(f"{etiqueta}: id_evento duplicado")
        vistos.add(registro.id_evento)

        momento = _marca_temporal_utc(registro.marca_temporal)
        if momento is None:
            problemas.append(
                f"{etiqueta}: marca_temporal {registro.marca_temporal!r} no es "
                "ISO 8601 en UTC"
            )
        else:
            if anterior is not None and momento < anterior:
                problemas.append(
                    f"{etiqueta}: marca_temporal fuera de orden respecto del "
                    "registro anterior"
                )
            anterior = momento

        if not 0.0 <= registro.confianza <= 1.0:
            problemas.append(
                f"{etiqueta}: confianza {registro.confianza} fuera de [0, 1]"
            )

        if registro.version_modelo != config.modelo.version:
            problemas.append(
                f"{etiqueta}: version_modelo {registro.version_modelo!r} != "
                f"{config.modelo.version!r} declarada en config"
            )

        problemas.extend(_problemas_responsable(registro, etiqueta))

        if config.explicabilidad.guardar_local_por_inferencia:
            problemas.extend(
                _problemas_explicacion(registro, etiqueta, config, artefactos)
            )

    return InformeVerificacion(
        ruta=ruta,
        n_registros=len(registros),
        valido=not problemas,
        problemas=problemas,
    )


def _problemas_responsable(
    registro: RegistroInferencia, etiqueta: str
) -> list[str]:
    """Comprueba que el responsable atribuye la decisión a alguien real."""
    if not registro.responsable.strip():
        return [f"{etiqueta}: responsable vacío"]
    if _MARCA_PLACEHOLDER in registro.responsable:
        return [
            f"{etiqueta}: responsable {registro.responsable!r} conserva el "
            "texto de la plantilla; la decisión no queda atribuida a nadie"
        ]
    return []


def _problemas_explicacion(
    registro: RegistroInferencia,
    etiqueta: str,
    config: "Configuracion",
    cache: dict[Path, set[str] | None],
) -> list[str]:
    """Comprueba que la explicación referenciada existe de verdad (R3.1).

    Con un artefacto consolidado, que el archivo exista no basta: el registro
    concreto tiene que estar adentro, o la bitácora estaría citando una
    explicación que nadie calculó.
    """
    referencia = registro.referencia_explicacion
    destino, fragmento = _ruta_explicacion(referencia, config)
    if not destino.exists():
        return [
            f"{etiqueta}: referencia_explicacion {referencia!r} no apunta a un "
            "artefacto existente"
        ]
    if fragmento is None:
        return []
    ids = _ids_en_artefacto(destino, cache)
    if ids is None:
        return [
            f"{etiqueta}: {destino.name} no es un artefacto JSONL legible con "
            "id_evento por línea"
        ]
    if fragmento not in ids:
        return [
            f"{etiqueta}: referencia_explicacion {referencia!r} apunta a un "
            f"registro {fragmento!r} que no está en {destino.name}"
        ]
    return []


def verificar_cobertura(
    ruta_registro: str | Path, ids_esperados: set[str], config: "Configuracion"
) -> InformeVerificacion:
    """Comprueba que hay exactamente un registro por cada inferencia esperada.

    La verificación de integridad no basta: una bitácora impecable que omite
    la mitad de las inferencias sigue sin permitir reconstruir el
    comportamiento del sistema.

    Args:
        ruta_registro: bitácora JSONL.
        ids_esperados: `id_evento` de todas las filas del set de prueba.
        config: configuración del marco.

    Returns:
        Un informe cuyos problemas listan faltantes y sobrantes.
    """
    ruta = Path(ruta_registro)
    try:
        registros = list(leer_registros(ruta))
    except FileNotFoundError:
        return InformeVerificacion(
            ruta=ruta,
            n_registros=0,
            valido=False,
            problemas=[f"no existe la bitácora: {ruta}"],
        )
    except RegistroInvalido as exc:
        return InformeVerificacion(
            ruta=ruta, n_registros=0, valido=False, problemas=[str(exc)]
        )

    registrados = {r.id_evento for r in registros}
    problemas: list[str] = []

    faltantes = ids_esperados - registrados
    if faltantes:
        problemas.append(
            f"faltan {len(faltantes)} inferencias en la bitácora: "
            f"{_muestra(faltantes)}"
        )

    sobrantes = registrados - ids_esperados
    if sobrantes:
        problemas.append(
            f"la bitácora tiene {len(sobrantes)} registros no esperados: "
            f"{_muestra(sobrantes)}"
        )

    # Un id repetido no aparece en ninguno de los dos conjuntos anteriores,
    # pero rompe la correspondencia 1:1 igual que un faltante.
    if len(registrados) != len(registros):
        problemas.append(
            f"hay {len(registros) - len(registrados)} id_evento duplicados: "
            "la correspondencia con el set de prueba no es 1:1"
        )

    return InformeVerificacion(
        ruta=ruta,
        n_registros=len(registros),
        valido=not problemas,
        problemas=problemas,
    )


def _muestra(ids: set[str], maximo: int = 5) -> str:
    """Lista unos pocos ids ordenados, para que el error sea accionable."""
    ordenados = sorted(ids)
    visibles = ", ".join(ordenados[:maximo])
    resto = len(ordenados) - maximo
    return f"{visibles}…(+{resto})" if resto > 0 else visibles


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada CLI. Devuelve 0 si la bitácora es válida, 1 si no."""
    from src.comun.configuracion import cargar_configuracion

    args = _construir_parser().parse_args(argv)
    config = cargar_configuracion(args.config)
    informe = verificar_registro(config.rutas.registro_inferencias, config)
    print(informe.resumen())
    return 0 if informe.valido else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
