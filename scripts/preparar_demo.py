"""Prepara una corrida de demostración del marco sobre menos días.

El pipeline completo explica cada inferencia del conjunto de evaluación, y
sobre el dataset entero eso tarda unos 17 minutos: demasiado para mostrarlo
en vivo. Este script recorta el crudo a los primeros días y deriva un
`config.demo.yaml` que usa **el mismo protocolo** —umbrales, subgrupos,
soporte mínimo y modelo— y escribe sus artefactos en `artefactos/demo/`,
sin tocar el expediente del piloto.

Lo único que cambia es cuántos datos entran. El procedimiento que se
demuestra es el mismo que se audita.

Uso:
    python scripts/preparar_demo.py [dias]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
DIAS_POR_DEFECTO = 20
DESTINO_CONFIG = RAIZ / "config.demo.yaml"


def _recortar_crudo(origen: Path, destino: Path, dias: int) -> tuple[int, int]:
    """Copia las líneas de los primeros `dias` días distintos del crudo.

    Se corta por día y no por número de líneas porque la partición del marco
    es temporal: un día a medias produciría una ventana que mezcla jornadas.

    Returns:
        (líneas escritas, días encontrados).
    """
    vistos: list[str] = []
    escritas = 0
    with origen.open(encoding="utf-8") as entrada, destino.open(
        "w", encoding="utf-8", newline="\n"
    ) as salida:
        for linea in entrada:
            fecha = linea.split(maxsplit=1)[0] if linea.strip() else ""
            if not fecha:
                continue
            if fecha not in vistos:
                if len(vistos) == dias:
                    break
                vistos.append(fecha)
            salida.write(linea)
            escritas += 1
    return escritas, len(vistos)


def _config_de_demo(crudo_demo: Path) -> dict:
    """Deriva la configuración de la demo desde `config.yaml`.

    Se deriva en vez de mantener una copia: dos configuraciones paralelas se
    desincronizan, y entonces la demo dejaría de mostrar el protocolo real.
    """
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    config["datos"]["archivo_crudo"] = crudo_demo.relative_to(RAIZ).as_posix()
    config["rutas"] = {
        clave: _bajo_demo(valor) for clave, valor in config["rutas"].items()
    }
    return config


def _bajo_demo(valor: object) -> object:
    """Reubica una ruta de artefactos bajo `artefactos/demo/`.

    Incluye la propia clave `artefactos`, que no lleva barra: varios módulos
    derivan sus subcarpetas de ella (explicaciones, equidad), y si no se
    reubica, la demo escribe encima del expediente del piloto.
    """
    if not isinstance(valor, str):
        return valor
    if valor == "artefactos":
        return "artefactos/demo"
    if valor.startswith("artefactos/"):
        return "artefactos/demo/" + valor[len("artefactos/") :]
    return valor


def main(argv: list[str]) -> int:
    dias = int(argv[0]) if argv else DIAS_POR_DEFECTO
    config = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    origen = RAIZ / config["datos"]["archivo_crudo"]
    if not origen.is_file():
        print(f"ERROR: no existe el crudo {origen}")
        print("Colóquelo primero; las instrucciones están en el datasheet.")
        return 1

    destino = origen.with_name(f"{origen.stem}-demo{origen.suffix}")
    escritas, encontrados = _recortar_crudo(origen, destino, dias)
    DESTINO_CONFIG.write_text(
        yaml.safe_dump(_config_de_demo(destino), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    print(f"crudo de demo:  {destino.relative_to(RAIZ)}")
    print(f"  {escritas:,} eventos de {encontrados} días")
    print(f"configuración:  {DESTINO_CONFIG.relative_to(RAIZ)}")
    print("  mismo protocolo; artefactos en artefactos/demo/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
