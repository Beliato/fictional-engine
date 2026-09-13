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
from src.procedimiento.requerimientos import (
    PRINCIPIOS_ENIA,
    REQUERIMIENTOS,
)

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


# =============================================================================
# La numeración de los principios
# =============================================================================

PLANTILLAS = RAIZ / "plantillas"


def _numero_enia_por_componente() -> dict[str, str]:
    """El código de cada requerimiento lleva el número del principio: R3.1
    documenta el principio 3 de la ENIA. De ahí sale el mapeo, sin lista
    aparte que pueda desincronizarse."""
    mapa: dict[str, str] = {}
    for requerimiento in REQUERIMIENTOS:
        numero = requerimiento.codigo[1]
        anterior = mapa.setdefault(requerimiento.principio, numero)
        assert anterior == numero, (
            f"{requerimiento.codigo} rompe el mapeo: "
            f"{requerimiento.principio} ya apuntaba al principio {anterior}"
        )
    return mapa


def test_cada_componente_apunta_a_un_principio_declarado_como_cubierto():
    """Si un componente apuntara a un principio que el marco declara fuera de
    alcance, el expediente se contradiría consigo mismo."""
    cubiertos = {n for n, _, cubierto in PRINCIPIOS_ENIA if cubierto}
    for componente, numero in _numero_enia_por_componente().items():
        assert numero in cubiertos, (
            f"{componente} documenta el principio {numero}, que no está "
            f"declarado como cubierto"
        )


def test_el_reporte_de_cumplimiento_nombra_los_principios_como_el_codigo():
    """La tabla del reporte escribe los números y nombres a mano; esto los ata
    a `PRINCIPIOS_ENIA`, que es la fuente verificada contra el PDF (D53)."""
    texto = (PLANTILLAS / "reporte_cumplimiento.md").read_text(encoding="utf-8")
    for numero, nombre, cubierto in PRINCIPIOS_ENIA:
        if cubierto:
            assert f"{numero} — {nombre}" in texto, f"falta {numero} — {nombre}"


#: `decisiones.md` es el registro histórico: su trabajo es citar los textos
#: que se corrigieron, así que es el único archivo que puede nombrar la
#: numeración vieja.
SIN_REVISAR = {"decisiones.md"}


def _fuentes_de_texto():
    """Todo el texto del repositorio donde podría reaparecer la numeración."""
    yield RAIZ / "README.md"
    for patron in ("docs/*.md", "plantillas/*.md", "src/**/*.py"):
        for ruta in sorted(RAIZ.glob(patron)):
            if ruta.name not in SIN_REVISAR:
                yield ruta


def test_nada_en_el_repositorio_numera_sus_propios_principios():
    """El marco tenía su propia numeración —1 explicabilidad, 2 equidad,
    3 trazabilidad— y la ENIA numera 3, 4 y 5. En el mismo reporte convivían
    "2. Equidad" y "principio 2 (Supervisión humana), fuera de alcance"
    (D58). La numeración de la ENIA es la única.

    La primera versión de esta prueba solo miraba `plantillas/`, y la
    numeración vieja sobrevivió en el README y en `docs/arquitectura.md`
    (D59). Mira todo el texto del repositorio."""
    for ruta in _fuentes_de_texto():
        texto = ruta.read_text(encoding="utf-8")
        for n in (1, 2, 3):
            assert f"Principio {n}" not in texto, (
                f"{ruta.relative_to(RAIZ)} usa la numeración propia: "
                f"'Principio {n}'"
            )
