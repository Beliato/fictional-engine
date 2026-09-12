"""Prepara el conjunto multi-hogar del piloto a partir del release de CASAS.

Regla de selección, declarada antes de medir nada:

    los hogares `hh101` a `hh110` con al menos `dias` días de registro,
    truncados a sus primeros `dias` días.

El truncado uniforme tiene dos motivos. Acota el costo de la corrida, y sobre
todo evita que la comparación entre viviendas dependa de cuánto se observó a
cada persona: contrastar un hogar de 497 días contra uno de 30 confundiría
disparidad con tiempo de observación.

Uso:
    python scripts/preparar_hogares.py <directorio_labeled> [dias]

El directorio es el que trae `labeled_data.zip` del DOI
10.5281/zenodo.15708568. Los archivos copiados quedan en
`datos/crudos/hogares/`, fuera de git.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "datos" / "crudos" / "hogares"
HOGARES = tuple(f"hh{n}" for n in range(101, 111))
DIAS_POR_DEFECTO = 30


def _truncar(origen: Path, destino: Path, dias: int) -> tuple[int, int]:
    """Copia las líneas de los primeros `dias` días distintos.

    El corte es por día y no por número de líneas: la partición del marco es
    temporal y un día a medias produciría una ventana que mezcla jornadas.

    Returns:
        (líneas escritas, días encontrados).
    """
    vistos: list[str] = []
    escritas = 0
    with origen.open(encoding="utf-8", errors="replace") as entrada, destino.open(
        "w", encoding="utf-8", newline="\n"
    ) as salida:
        for linea in entrada:
            fecha = linea.split(",", 1)[0] if linea.strip() else ""
            if not fecha:
                continue
            if fecha not in vistos:
                if len(vistos) == dias:
                    break
                vistos.append(fecha)
            salida.write(linea)
            escritas += 1
    return escritas, len(vistos)


def _dias(archivo: Path) -> int:
    fechas = set()
    with archivo.open(encoding="utf-8", errors="replace") as f:
        for linea in f:
            if linea.strip():
                fechas.add(linea.split(",", 1)[0])
    return len(fechas)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    origen = Path(argv[0])
    dias = int(argv[1]) if len(argv) > 1 else DIAS_POR_DEFECTO
    if not origen.is_dir():
        print(f"ERROR: no existe el directorio {origen}")
        return 1

    DESTINO.mkdir(parents=True, exist_ok=True)
    for viejo in DESTINO.glob("*.csv"):
        viejo.unlink()

    incluidos, excluidos, total = [], [], 0
    for hogar in HOGARES:
        archivo = origen / f"{hogar}.csv"
        if not archivo.is_file():
            excluidos.append((hogar, "no está en el origen"))
            continue
        disponibles = _dias(archivo)
        if disponibles < dias:
            excluidos.append((hogar, f"{disponibles} días, menos de {dias}"))
            continue
        escritas, encontrados = _truncar(archivo, DESTINO / f"{hogar}.csv", dias)
        incluidos.append((hogar, escritas, encontrados))
        total += escritas

    print(f"regla: hogares {HOGARES[0]}-{HOGARES[-1]} con {dias} días o más, "
          f"truncados a {dias} días")
    print(f"\nincluidos ({len(incluidos)}):")
    for hogar, escritas, encontrados in incluidos:
        print(f"  {hogar}: {escritas:>8,} eventos en {encontrados} días")
    print(f"\nexcluidos ({len(excluidos)}):")
    for hogar, motivo in excluidos:
        print(f"  {hogar}: {motivo}")
    print(f"\ntotal: {total:,} eventos en {DESTINO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
