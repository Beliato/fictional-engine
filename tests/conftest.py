"""Fixtures compartidas de la batería de pruebas."""

from __future__ import annotations

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
