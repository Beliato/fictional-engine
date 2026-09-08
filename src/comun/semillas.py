"""Control centralizado de la aleatoriedad para lograr ejecución determinista.

Nota sobre `PYTHONHASHSEED`: no puede fijarse de forma efectiva desde dentro
del proceso ya arrancado. Debe exportarse como variable de entorno antes de
lanzar el intérprete (lo hacen `scripts/setup.sh` y el `Makefile`). Aquí solo
se **verifica** que su valor coincide con el declarado en `config.yaml`.
"""

from __future__ import annotations

import os


def fijar_semilla_global(semilla: int) -> None:
    """Fija la semilla en todas las fuentes de aleatoriedad del proceso.

    Cubre: módulo `random`, `numpy.random`, y el entorno de hashing. Los
    estimadores de scikit-learn reciben la semilla vía `random_state` desde
    la configuración, no aquí.

    Args:
        semilla: valor entero declarado en `config.yaml` (`semilla`).

    TODO:
        - `random.seed(semilla)`
        - `numpy.random.seed(semilla)` y crear un `numpy.random.Generator`
          reutilizable (`default_rng(semilla)`).
        - Registrar en el log qué se fijó y con qué valor.
    """
    raise NotImplementedError


def verificar_pythonhashseed(esperado: int) -> None:
    """Comprueba que `PYTHONHASHSEED` está fijado al valor esperado.

    Args:
        esperado: valor declarado en `config.yaml`
            (`determinismo.pythonhashseed`).

    Raises:
        EntornoNoDeterminista: si la variable no está fijada o difiere.

    TODO: leer `os.environ.get("PYTHONHASHSEED")` y comparar.
    """
    raise NotImplementedError


def instantanea_entorno() -> dict[str, str]:
    """Devuelve una instantánea del entorno relevante para reproducibilidad.

    Returns:
        Diccionario con: versión de Python, plataforma, `PYTHONHASHSEED`,
        versiones de numpy/pandas/scikit-learn/shap/fairlearn, hash del
        commit de git si está disponible. Se incrusta en el manifiesto de
        evidencia.

    TODO: recopilar los datos anteriores de forma tolerante a fallos.
    """
    raise NotImplementedError


class EntornoNoDeterminista(RuntimeError):
    """El entorno de ejecución no garantiza resultados reproducibles."""


_ = os  # referenciado por los TODO; evita el aviso de import sin uso
