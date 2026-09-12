"""Control centralizado de la aleatoriedad para lograr ejecución determinista.

Nota sobre `PYTHONHASHSEED`: no puede fijarse de forma efectiva desde dentro
del proceso ya arrancado. Debe exportarse como variable de entorno antes de
lanzar el intérprete (lo hacen `scripts/setup.sh` y el `Makefile`). Aquí solo
se **verifica** que su valor coincide con el declarado en `config.yaml`.
"""

from __future__ import annotations

import os
import platform
import random
import subprocess
from importlib import metadata

# Paquetes cuya versión se registra en el manifiesto. Cambiar cualquiera puede
# cambiar los resultados, así que la evidencia tiene que decir cuáles se
# usaron.
PAQUETES = ("numpy", "pandas", "scikit-learn", "shap", "matplotlib", "pyyaml")


def fijar_semilla_global(semilla: int) -> None:
    """Fija la semilla en todas las fuentes de aleatoriedad del proceso.

    Cubre el módulo `random` y el estado global de `numpy.random`. Los
    estimadores de scikit-learn reciben la semilla vía `random_state` desde la
    configuración, no desde aquí: `verificar_coherencia_semillas` comprueba
    que sea la misma.

    Args:
        semilla: valor entero declarado en `config.yaml` (`semilla`).
    """
    import numpy as np

    random.seed(semilla)
    np.random.seed(semilla)


def verificar_pythonhashseed(esperado: int) -> None:
    """Comprueba que `PYTHONHASHSEED` está fijado al valor esperado.

    Args:
        esperado: valor declarado en `config.yaml`
            (`determinismo.pythonhashseed`).

    Raises:
        EntornoNoDeterminista: si la variable no está fijada o difiere. Se
            falla antes de producir evidencia: una corrida que no se puede
            repetir no sirve como prueba de cumplimiento, y el orden de
            iteración de los conjuntos depende de esta variable.
    """
    valor = os.environ.get("PYTHONHASHSEED")
    if valor is None:
        raise EntornoNoDeterminista(
            "PYTHONHASHSEED no está fijado; expórtelo antes de arrancar el "
            f"intérprete: PYTHONHASHSEED={esperado}"
        )
    if valor != str(esperado):
        raise EntornoNoDeterminista(
            f"PYTHONHASHSEED vale {valor!r} y la configuración declara "
            f"{esperado}; la ejecución no sería reproducible"
        )


def _version(paquete: str) -> str:
    try:
        return metadata.version(paquete)
    except metadata.PackageNotFoundError:
        return "(ausente)"


def _git(*argumentos: str) -> str | None:
    """Ejecuta un comando de git y devuelve su salida, o None si no se puede.

    Tolerante a fallos a propósito: el marco debe poder ejecutarse fuera de un
    repositorio de git. La ausencia del commit se declara en el manifiesto en
    vez de abortar la corrida.
    """
    try:
        salida = subprocess.run(
            ["git", *argumentos],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return salida.stdout.strip() if salida.returncode == 0 else None


def instantanea_entorno() -> dict[str, str]:
    """Devuelve una instantánea del entorno relevante para reproducibilidad.

    Returns:
        Diccionario con versión de Python, plataforma, `PYTHONHASHSEED`,
        versiones de las dependencias directas y, si está disponible, el
        commit de git y si el árbol de trabajo tenía cambios sin confirmar.
        Se incrusta en el manifiesto de evidencia.

    Un commit con el árbol sucio no identifica el código que corrió, así que
    el estado del árbol se declara junto al commit en vez de omitirse.
    """
    entorno = {
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", "(no fijado)"),
    }
    for paquete in PAQUETES:
        entorno[paquete] = _version(paquete)

    commit = _git("rev-parse", "HEAD")
    entorno["git_commit"] = commit or "(no disponible)"
    if commit is not None:
        sucio = _git("status", "--porcelain")
        entorno["git_arbol_limpio"] = "sí" if sucio == "" else "no"
    else:
        entorno["git_arbol_limpio"] = "(no disponible)"
    return entorno


class EntornoNoDeterminista(RuntimeError):
    """El entorno de ejecución no garantiza resultados reproducibles."""
