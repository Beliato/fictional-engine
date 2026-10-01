# Marco operativo de cumplimiento regulatorio para IA de sensores PIR

Proyecto de investigación académica. Desarrolla un **marco operativo** que
verifica tres de los siete principios rectores de la **Estrategia Nacional de
IA de Costa Rica** —el 3 (transparencia y explicabilidad), el 4 (equidad y no
discriminación) y el 5 (responsabilidad)—, articulados con el **AI Act de la
UE** y el **NIST AI RMF**, sobre un sistema de IA que clasifica actividad
domiciliaria a partir de **sensores PIR** (dataset público **CASAS**), y
produce **evidencia auditable**.

Sus tres componentes —explicabilidad, equidad y trazabilidad— documentan esos
principios; el reporte de cumplimiento declara qué queda fuera dentro de cada
uno.

El requisito transversal del proyecto es **reproducibilidad y trazabilidad**;
por eso el propio repositorio es ejemplar en eso: versiones fijadas, semillas
declaradas, ejecución determinista y sin estado oculto.

> **Estado:** el marco está completo y se ejecutó sobre **dos pilotos**, con
> **272 pruebas** en verde.
>
> | Piloto | Configuración | Viviendas | Inferencias | Requerimientos |
> |---|---|---|---:|---|
> | CASAS Aruba | `config.yaml` | 1 | 11.175 | 9 de 9 |
> | CASAS serie `hh` | `config.hogares.yaml` | 9 | 7.561 | 9 de 9 |
>
> Los dos expedientes están completos y los dos dan **NO CUMPLE**: el
> veredicto es del sistema evaluado, no del marco. Que el procedimiento
> produzca la evidencia de un incumplimiento es exactamente lo que se le pide
> (Tabla 10).
>
> Quedan dos `NotImplementedError` deliberados, que rechazan una opción
> declarada en configuración en vez de fallar a medias: la perturbación
> `interventional` de SHAP y las estrategias de partición distintas de
> `temporal_por_dia`.

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

Los datos **no se versionan**: el crudo vive en `datos/crudos/`, que git
ignora. Cada piloto necesita el suyo.

### Piloto de Aruba (`config.yaml`)

Crudo anotado en `datos/crudos/aruba.txt`, la ruta que declara
`datos.archivo_crudo`.

La copia anotada **no se puede bajar del depósito oficial**. El depósito de
CASAS en [Zenodo](https://zenodo.org/records/15708568), bajo CC BY 4.0,
publica Aruba sin etiquetas de actividad, y sus 82 hogares anotados son de
otras series (D53). La copia usada viene de la distribución anterior de CASAS,
obtenida de un repositorio de terceros, cuyo README pedía no redistribuirla sin
permiso expreso. Su procedencia se verificó contra el release oficial, evento
por evento (D22).

**Formato esperado** — un evento por línea, campos separados por espacios; la
anotación marca el inicio y el fin de cada intervalo de actividad:

```
2010-11-04 00:03:50.209589 M003 ON Sleeping begin
2010-11-04 00:03:57.399391 M003 OFF
```

Aruba son 1.719.552 eventos utilizables entre 2010-11-04 y 2011-06-11, con 31
sensores PIR (`M001`-`M031`), 3 de puerta y 5 de temperatura, y 11 actividades
anotadas. Procedencia y composición se documentan en el datasheet que genera
el paso 2 (`artefactos/datasheet.md`); las decisiones de preparación, en
[`docs/decisiones.md`](docs/decisiones.md) (D21-D26).

### Piloto multi-hogar (`config.hogares.yaml`)

Nueve viviendas de personas adultas mayores, de la serie `hh`. Bajar
`labeled_data.zip` del mismo [depósito de Zenodo](https://zenodo.org/records/15708568),
descomprimirlo y preparar las viviendas:

```bash
python scripts/preparar_hogares.py <directorio_de_labeled_data> 30
```

El script aplica la regla de selección, declarada antes de medir: los hogares
`hh101` a `hh110` con al menos 30 días de registro, truncados a sus primeros
30. Deja un CSV por vivienda en `datos/crudos/hogares/`. El formato y la
lectura de varias viviendas se explican en
[`docs/aplicar-a-otro-dataset.md`](docs/aplicar-a-otro-dataset.md).

### Características

Los eventos se agrupan en ventanas disjuntas de 30 y cada ventana produce una
fila. Las características se nombran **por zona del hogar**
(`conteo_Kitchen`), no por sensor (`conteo_M018`): el R3.3 exige que la
explicación sea comprensible para destinatarios no técnicos, y `M018` no lo
es. En Aruba, el mapeo sensor → zona vive en `config.yaml` y se derivó
cruzando la copia anotada con el release consolidado de CASAS: 1.596.509
eventos coincidentes, 100 % de acuerdo. En la serie `hh` los sensores ya
vienen nombrados por la habitación donde están instalados.

> **Partición temporal, no aleatoria.** Los últimos días van a prueba. Los
> eventos están autocorrelacionados: repartirlos al azar deja ventanas
> contiguas del mismo intervalo a ambos lados e infla la exactitud, y sobre
> esa exactitud se calculan después explicabilidad y equidad.

## Uso

```bash
make test                 # batería de pruebas
make pipeline             # ejecuta los 6 pasos del marco (usa config.yaml)
make pipeline CONFIG=config.hogares.yaml   # el piloto multi-hogar
make demo                 # los 6 pasos sobre 20 días, en menos de un minuto (ver docs/demo.md)
make verificar-registro   # verifica la bitácora de inferencias
make clean                # borra artefactos generados (no toca datos/)
make help                 # lista todos los comandos
```

Ejecución directa del orquestador:

```bash
python -m src.procedimiento.orquestador --config config.yaml
```

Códigos de salida: `0` completo, con la equidad aprobada y los nueve
requerimientos cubiertos · `2` completo pero con hallazgos (la equidad no
aprueba, no es evaluable, o falta evidencia) · `1` error de ejecución.

---

## Arquitectura

Detalle en [`docs/arquitectura.md`](docs/arquitectura.md).

```
src/
├── comun/            configuración, lectores, datos, modelado, utilidades
├── explicabilidad/   ENIA principio 3 — atribución SHAP local y global
├── equidad/          ENIA principio 4 — desagregado + disparidad vs umbrales
├── trazabilidad/     ENIA principio 5 — registro JSONL + verificación
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
`responsable`, `version_esquema` y, opcionalmente, `metadatos`. Definido en
`src/trazabilidad/esquema.py`.

## Estructura del repositorio

```
.
├── config.yaml              piloto de Aruba: toda la parametrización en un archivo
├── config.hogares.yaml      piloto multi-hogar
├── requirements.txt         dependencias directas, versiones exactas
├── requirements.lock        cierre transitivo (generado por `make lock`)
├── Makefile                 setup · lock · test · pipeline · demo · verificar-registro · clean
├── pyproject.toml           configuración de pytest (sin empaquetar)
├── .python-version          3.11
├── scripts/                 setup.sh · preparar_demo.py · preparar_hogares.py
├── src/                     código de producción (ver Arquitectura)
├── tests/                   batería de pruebas (pytest)
├── datos/                   crudos/ e intermedios/  (ignorados por git)
├── artefactos/              expedientes generados   (ignorado por git)
├── plantillas/              model card, datasheet, reportes
├── notebooks/               solo exploración
├── docs/                    arquitectura · marco operativo · decisiones · demo · CRISP-ML(Q)
├── articulo/                artículo en LaTeX para Tecnología en Marcha
└── articulo_tecnologia_en_marcha.md, .docx   borrador original del artículo
```

## Documentación

- [`docs/arquitectura.md`](docs/arquitectura.md) — módulos, principios de diseño, flujo de datos.
- [`docs/marco_operativo.md`](docs/marco_operativo.md) — los 6 pasos y la articulación normativa.
- [`docs/decisiones.md`](docs/decisiones.md) — registro de las decisiones del proyecto, con su porqué.
- [`docs/aplicar-a-otro-dataset.md`](docs/aplicar-a-otro-dataset.md) — **el contrato de ingesta**: qué debe aportar un equipo para evaluar su propio sistema con este marco.
- [`docs/crisp-ml-q.md`](docs/crisp-ml-q.md) — dónde se sitúa el marco frente a CRISP-ML(Q): coincidencias, divergencias declaradas y huecos abiertos.
- [`docs/demo.md`](docs/demo.md) — cómo mostrar el marco funcionando en vivo.
- [`articulo/README.md`](articulo/README.md) — cómo compilar el artículo, su historia y los pendientes.
