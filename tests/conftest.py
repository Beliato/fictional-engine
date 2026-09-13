"""Fixtures compartidas de la batería de pruebas."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def ruta_config() -> Path:
    """Ruta al `config.yaml` real del repositorio."""
    return RAIZ / "config.yaml"


@pytest.fixture
def config(ruta_config):
    """Configuración cargada desde el `config.yaml` del repo."""
    from src.comun.configuracion import cargar_configuracion

    return cargar_configuracion(ruta_config)


#: Campos de `Rutas` que son **entrada** del marco: insumos que las pruebas
#: leen del repositorio. Todos los demás son salida, y una prueba nunca debe
#: escribirlos fuera de su directorio temporal.
RUTAS_DE_ENTRADA = frozenset({"datos_crudos", "datos_intermedios", "plantillas"})


def aislar_rutas(rutas, base: Path):
    """Reubica bajo `base` todas las rutas de salida del marco.

    Se deriva de los campos de `Rutas`, no de una lista escrita a mano: una
    ruta nueva queda aislada sin que nadie tenga que acordarse de agregarla.

    La lista a mano fue exactamente la falla. El fixture del procedimiento
    redirigía cinco de las catorce rutas; las otras nueve conservaban el valor
    del `config.yaml` real, así que cada corrida de la batería sobrescribía el
    model card, los tres reportes, la bitácora de ejecución y el manifiesto
    del expediente del piloto (D57).
    """
    raiz = Path(rutas.artefactos)
    cambios = {}
    for campo in dataclasses.fields(rutas):
        if campo.name in RUTAS_DE_ENTRADA:
            continue
        valor = Path(getattr(rutas, campo.name))
        if valor == raiz:
            cambios[campo.name] = base
            continue
        try:
            cambios[campo.name] = base / valor.relative_to(raiz)
        except ValueError:
            # Una salida declarada fuera del árbol de artefactos se aísla por
            # nombre. Lo que no puede pasar es que quede fuera de `base`.
            cambios[campo.name] = base / valor.name
    return dataclasses.replace(rutas, **cambios)


@pytest.fixture
def config_piloto(config, tmp_path, crudo_sintetico):
    """Config con crudo sintético y artefactos en `tmp_path`.

    Bosque chico: lo que se prueba es el procedimiento, no el desempeño.
    """
    crudo = tmp_path / "crudo.txt"
    crudo.write_text(crudo_sintetico(dias=12, eventos_por_dia=150), encoding="utf-8")
    rutas = aislar_rutas(config.rutas, tmp_path / "artefactos")
    datos = dataclasses.replace(config.datos, archivo_crudo=crudo)
    modelo = dataclasses.replace(
        config.modelo,
        hiperparametros={**config.modelo.hiperparametros, "n_estimators": 8},
    )
    return dataclasses.replace(config, rutas=rutas, datos=datos, modelo=modelo)


@pytest.fixture
def crudo_sintetico():
    """Genera un crudo determinista con el formato de Aruba.

    La batería no puede depender del dataset real: pesa 61 MB, está fuera de
    git y su licencia prohíbe redistribuirlo. Este generador produce el mismo
    formato —incluidos los spans `begin`/`end`— sobre un puñado de días.
    """

    def generar(dias: int = 10, eventos_por_dia: int = 120) -> str:
        import numpy as np

        rng = np.random.default_rng(0)
        sensores = [f"M{n:03d}" for n in range(1, 32)]
        lineas = []
        for d in range(dias):
            fecha = f"2010-11-{d + 1:02d}"
            segundo = 0
            for i in range(eventos_por_dia):
                segundo += int(rng.integers(5, 60))
                hora = f"{segundo // 3600 % 24:02d}:{segundo // 60 % 60:02d}:{segundo % 60:02d}.000000"
                sensor = sensores[int(rng.integers(0, len(sensores)))]
                # Un span de actividad cada 40 eventos, de 20 de largo.
                sufijo = ""
                if i % 40 == 0:
                    sufijo = " Sleeping begin"
                elif i % 40 == 20:
                    sufijo = " Sleeping end"
                lineas.append(f"{fecha} {hora} {sensor} ON{sufijo}")
            for t in range(1, 6):
                lineas.append(
                    f"{fecha} 23:5{t}:00.000000 T00{t} {20 + t / 2:.1f}"
                )
            lineas.append(f"{fecha} 23:59:30.000000 D001 OPEN")
        return "\n".join(lineas) + "\n"

    return generar
