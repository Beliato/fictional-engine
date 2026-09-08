# Marco operativo de cumplimiento regulatorio para IA de sensores PIR

Proyecto de investigación académica. Desarrolla un **marco operativo** que
verifica tres principios de la **Estrategia Nacional de IA de Costa Rica**
(explicabilidad, equidad, trazabilidad), articulados con el **AI Act de la UE**
y el **NIST AI RMF**, sobre un sistema de IA que clasifica actividad
domiciliaria a partir de **sensores PIR** (dataset público **CASAS**), y
produce **evidencia auditable**.

El requisito transversal del proyecto es **reproducibilidad y trazabilidad**;
por eso el propio repositorio es ejemplar en eso: versiones fijadas, semillas
declaradas, ejecución determinista y sin estado oculto.

> **Estado:** esqueleto. Firmas, tipos, docstrings y estructura están puestos;
> la lógica está marcada con `TODO` / `raise NotImplementedError`. La única
> pieza implementada es el esquema de trazabilidad
> (`src/trazabilidad/esquema.py`) y sus pruebas.

---

## Requisitos

- Windows 11 + WSL2 (Ubuntu) — o cualquier Linux. Sin GPU.
- **Python 3.11.x** (ver `.python-version`).
  ```bash
  sudo apt install python3.11 python3.11-venv
  ```

## Instalación

```bash
make setup          # crea .venv e instala requirements.txt (versiones exactas)
source .venv/bin/activate
make lock           # congela el cierre transitivo -> requirements.lock (versiónelo)
```

## Datos

El dataset CASAS **no** se versiona. Descárguelo de
<http://casas.wsu.edu/datasets/> y coloque el CSV en:

```
datos/crudos/casas.csv
```

La ruta y el nombre están en `config.yaml` (`datos.archivo_crudo`). La
procedencia y composición se documentan en `plantillas/datasheet.md`.

## Uso

```bash
make test                 # batería de pruebas
make pipeline             # ejecuta los 6 pasos del marco (usa config.yaml)
make verificar-registro   # verifica la bitácora de inferencias
make clean                # borra artefactos generados (no toca datos/)
make help                 # lista todos los comandos
```

Ejecución directa del orquestador:

```bash
python -m src.procedimiento.orquestador --config config.yaml
```

Códigos de salida: `0` completo y equidad aprueba · `2` completo pero equidad
**no** aprueba · `1` error de ejecución.

---

## Arquitectura

Detalle en [`docs/arquitectura.md`](docs/arquitectura.md).

```
src/
├── comun/            configuración, datos, modelado, semillas, utilidades
├── explicabilidad/   Principio 1 — atribución SHAP local y global
├── equidad/          Principio 2 — desempeño desagregado + métricas fairlearn
├── trazabilidad/     Principio 3 — registro JSONL + verificación
└── procedimiento/    orquestador de los 6 pasos + generación de evidencia
```

Convenciones de reproducibilidad:

| Mecanismo | Dónde |
|---|---|
| Semilla única declarada | `config.yaml` → `semilla` |
| `PYTHONHASHSEED` fijado antes de arrancar Python | `Makefile`, `scripts/setup.sh` |
| Ejecución de un solo hilo (`n_jobs=1`) | `config.yaml` |
| Versiones exactas + lock transitivo | `requirements.txt` + `requirements.lock` |
| Sin estado oculto: toda parametrización en un archivo | `config.yaml` |
| Config y contexto inmutables (`frozen`) | `src/comun/configuracion.py`, `src/procedimiento/pasos.py` |
| Manifiesto con hashes de toda entrada/salida | paso 6 → `artefactos/manifiesto.json` |

## Flujo del procedimiento

Los 6 pasos son, uno a uno, los de la **Tabla 9** del documento de tesis.
Detalle y mapeo normativo en
[`docs/marco_operativo.md`](docs/marco_operativo.md).

**Precondiciones** — no son pasos del marco. El modelo es *sujeto de prueba,
no objeto de optimización*, así que preparar los datos y sellar el modelo
deben estar resueltos antes de que el procedimiento empiece. Si una falla, es
error de ejecución (código 1), no un hallazgo de cumplimiento.

| # | Paso | Producto | NIST | Requerimientos |
|---|---|---|---|---|
| 1 | Caracterización del sistema | Ficha de caracterización | MAPEAR | insumo de R5.2 |
| 2 | Documentación del dataset | Datasheet | MAPEAR | R4.3 |
| 3 | Declaración de criterios | Protocolo declarado | MAPEAR | R4.2 |
| 4 | Ejecución de pruebas técnicas | Resultados + bitácora | MEDIR | R3.1-R3.3, R4.1, R4.2, R5.1 |
| 5 | Generación de artefactos | Reportes + model card | GOBERNAR | R5.2 |
| 6 | Verificación de auditabilidad | Expediente de evidencia | GESTIONAR | R5.3 |

```
precondiciones:  crudos ─▶ características ─▶ modelo sellado
                                                    │
procedimiento:   ①ficha ─▶ ②datasheet ─▶ ③protocolo (sella hash de config)
                                                    │
                 ④ explicabilidad · equidad · bitácora   ◀── umbrales sellados
                                                    │
                 ⑤ reportes + model card ─▶ ⑥ verificación + manifiesto
```

Los tres módulos de principio se **aplican** en el paso 4 y se **documentan**
en el paso 5. El paso 3 sella el hash de `config.yaml` y el paso 6 lo vuelve a
comprobar: es lo que hace demostrable —y no solo declarable— que los umbrales
de equidad no se ajustaron después de ver los resultados.

## Configuración (`config.yaml`)

Única fuente de verdad para parámetros: semilla, rutas, hiperparámetros del
modelo, definición de subgrupos de comparación y **umbrales de las métricas de
equidad**.

> **Regla:** los umbrales de equidad se declaran en `config.yaml` **antes** de
> ejecutar las pruebas y **nunca** se ajustan después de ver resultados. Todo
> cambio de umbral queda en el historial de git con su justificación.

## Esquema de la bitácora de inferencias

Cada línea de `artefactos/bitacora/inferencias.jsonl` registra:
`id_evento`, `marca_temporal` (UTC ISO 8601), `referencia_entrada` (hash
SHA-256 de la fila de entrada — no se guardan datos crudos), `salida_modelo`,
`confianza`, `version_modelo`, `version_marco`, `referencia_explicacion`,
`responsable`, `version_esquema`. Definido en `src/trazabilidad/esquema.py`.

## Estructura del repositorio

```
.
├── config.yaml              configuración central (única fuente de verdad)
├── requirements.txt         dependencias directas, versiones exactas
├── requirements.lock        cierre transitivo (generado por `make lock`)
├── Makefile                 setup · test · pipeline · verificar-registro · clean
├── pyproject.toml           configuración de pytest (sin empaquetar)
├── .python-version          3.11
├── scripts/setup.sh         crea el venv e instala todo
├── src/                     código de producción (ver Arquitectura)
├── tests/                   pytest (skeletons + esquema implementado)
├── datos/                   crudos/ e intermedios/  (ignorados por git)
├── artefactos/              salidas generadas       (ignorado por git)
├── plantillas/              model card, datasheet, reportes
├── notebooks/               solo exploración
└── docs/                    arquitectura · marco operativo · decisiones
```

## Documentación

- [`docs/arquitectura.md`](docs/arquitectura.md) — módulos, principios de diseño, flujo de datos.
- [`docs/marco_operativo.md`](docs/marco_operativo.md) — los 6 pasos y la articulación normativa.
- [`docs/decisiones.md`](docs/decisiones.md) — decisiones tomadas al montar el esqueleto, para revisar.
