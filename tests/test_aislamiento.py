"""La batería no puede escribir dentro del expediente del repositorio.

El expediente es la evidencia del piloto. Si una prueba escribe encima de
alguno de sus artefactos, el resultado no es un fallo visible sino algo peor:
un expediente que se contradice a sí mismo —una bitácora con miles de
inferencias reales y un reporte que habla de diez— con un manifiesto que sella
los archivos equivocados. Nadie se entera hasta que alguien lo lee.

Eso ocurrió (D57). Estas pruebas existen para que no vuelva a ocurrir en
silencio.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from src.comun.configuracion import Rutas
from tests.conftest import RUTAS_DE_ENTRADA, aislar_rutas

RAIZ = Path(__file__).resolve().parents[1]


def _salidas(rutas) -> dict[str, Path]:
    """Las rutas de salida, derivadas de los campos y no de una lista."""
    return {
        campo.name: Path(getattr(rutas, campo.name))
        for campo in dataclasses.fields(rutas)
        if campo.name not in RUTAS_DE_ENTRADA
    }


def test_aislar_rutas_deja_todas_las_salidas_bajo_la_base(config, tmp_path):
    """Exhaustivo sobre los campos de `Rutas`: agregar una ruta nueva no puede
    dejarla fuera del aislamiento sin que esto falle."""
    base = tmp_path / "artefactos"
    aisladas = aislar_rutas(config.rutas, base)

    escapadas = [
        nombre
        for nombre, valor in _salidas(aisladas).items()
        if not valor.is_relative_to(base)
    ]
    assert not escapadas, f"rutas fuera del temporal: {escapadas}"


def test_el_aislamiento_conserva_la_forma_del_arbol(config, tmp_path):
    """Aislar no debe aplanar: la bitácora vive en un subdirectorio y el
    código deriva rutas de `artefactos`, así que la estructura importa."""
    aisladas = aislar_rutas(config.rutas, tmp_path / "artefactos")

    assert aisladas.registro_inferencias.parent.name == "bitacora"
    assert aisladas.manifiesto.parent == aisladas.artefactos
    assert aisladas.registro_inferencias.name == config.rutas.registro_inferencias.name


def test_las_rutas_de_entrada_son_campos_reales():
    """Si un campo se renombra, `RUTAS_DE_ENTRADA` deja de protegerlo y pasaría
    a aislarse una entrada —o a no aislarse una salida— sin aviso."""
    campos = {campo.name for campo in dataclasses.fields(Rutas)}
    desconocidas = RUTAS_DE_ENTRADA - campos
    assert not desconocidas, f"no son campos de Rutas: {sorted(desconocidas)}"


def test_el_config_de_prueba_no_apunta_al_expediente_del_repositorio(config_piloto):
    """La regresión concreta: el fixture del procedimiento redirigía cinco de
    las catorce rutas y las otras nueve escribían en `artefactos/` del repo."""
    expediente = RAIZ / "artefactos"

    dentro = {
        nombre: str(valor)
        for nombre, valor in _salidas(config_piloto.rutas).items()
        if valor.is_relative_to(expediente)
    }
    assert not dentro, f"la prueba escribiría en el expediente: {dentro}"
