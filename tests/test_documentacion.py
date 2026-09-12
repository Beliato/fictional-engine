"""La guía de reutilización tiene que seguir siendo cierta.

`docs/aplicar-a-otro-dataset.md` sostiene la afirmación central del marco: que
aplicarlo a otro sistema de sensores es escribir un lector y declarar una
configuración. Un ejemplo que ya no carga es peor que no tener ejemplo, porque
quien lo copia descubre el error recién al ejecutar, y porque la promesa deja
de ser verificable.

Estas pruebas comparan el documento con el cargador real, no con lo que el
documento decía cuando se escribió.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from src.comun.configuracion import cargar_configuracion

RAIZ = Path(__file__).resolve().parents[1]
GUIA = RAIZ / "docs" / "aplicar-a-otro-dataset.md"


def _bloques_yaml(ruta: Path) -> list:
    """Los fragmentos ```yaml del documento, ya parseados."""
    texto = ruta.read_text(encoding="utf-8")
    return [
        yaml.safe_load(bloque)
        for bloque in re.findall(r"```yaml\n(.*?)```", texto, re.DOTALL)
    ]


def _config_real() -> dict:
    return yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))


def test_el_bloque_de_equidad_de_la_guia_carga(tmp_path):
    """La guía presenta el bloque de equidad completo: si le faltara una clave
    obligatoria, el cargador lo rechazaría y el ejemplo no serviría."""
    equidad = next(
        b["equidad"] for b in _bloques_yaml(GUIA) if isinstance(b, dict) and "equidad" in b
    )
    crudo = _config_real()
    crudo["equidad"] = equidad

    ruta = tmp_path / "config.yaml"
    ruta.write_text(yaml.safe_dump(crudo, allow_unicode=True), encoding="utf-8")

    config = cargar_configuracion(ruta)
    assert config.equidad.umbrales
    assert config.equidad.justificacion_umbrales


def test_la_guia_no_muestra_claves_que_el_marco_no_reconoce():
    """Una clave inventada o renombrada en el ejemplo induce a error, y el
    cargador rechaza las desconocidas: el documento quedaría prometiendo algo
    que falla."""
    real = _config_real()
    contenedores = {"datos": real["datos"], "equidad": real["equidad"]}

    for bloque in _bloques_yaml(GUIA):
        if not isinstance(bloque, dict):
            continue
        for clave, valor in bloque.items():
            if clave in real:
                esperadas = real[clave]
            elif clave in real["datos"]:
                esperadas = real["datos"][clave]
            elif clave in real["equidad"]:
                esperadas = real["equidad"][clave]
            else:
                raise AssertionError(
                    f"la guía muestra {clave!r}, que no existe en config.yaml"
                )
            if isinstance(valor, dict) and isinstance(esperadas, dict):
                # Las claves de un mapeo libre (zonas, nombres_zona, mapeo) son
                # del dataset de ejemplo; lo que se comprueba es la estructura
                # de los bloques con claves fijas.
                if clave in contenedores or clave == "actividades":
                    desconocidas = sorted(set(valor) - set(esperadas))
                    assert not desconocidas, f"{clave}: {desconocidas}"


def test_la_guia_documenta_los_dos_lectores_registrados():
    """Si se agrega un formato y la guía no lo nombra, el documento deja de
    describir el marco que existe."""
    from src.comun.lectores import LECTORES

    texto = GUIA.read_text(encoding="utf-8")
    for nombre in LECTORES:
        assert nombre in texto, f"la guía no menciona el formato {nombre!r}"
