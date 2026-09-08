# Marco operativo — los 6 pasos

El marco verifica tres principios de la Estrategia Nacional de IA de Costa Rica
(ENIA-CR), articulados con el AI Act de la UE y el NIST AI RMF, sobre un
sistema de IA que clasifica actividad domiciliaria a partir de sensores PIR
(dataset CASAS). Produce evidencia auditable y reproducible.

## Los 3 principios y su articulación normativa

| Principio | ENIA Costa Rica | AI Act EU | NIST AI RMF |
|---|---|---|---|
| **Explicabilidad** | Transparencia y explicabilidad | Art. 13 (transparencia) | MEASURE 2.9 |
| **Equidad** | Equidad y no discriminación | Art. 10 (gobernanza de datos y sesgos) | MEASURE 2.11 |
| **Trazabilidad** | Rendición de cuentas y trazabilidad | Art. 12 (conservación de registros) | GOVERN 1.4 / MANAGE 4.1 |

> El mapeo concreto de artículos/subcategorías es **provisional** y debe
> validarlo un especialista legal. Vive en `config.yaml`
> (`articulacion_normativa`) para que sea explícito y versionado.

## Los 6 pasos

### Paso 1 — Preparación de datos
Carga determinista de `datos/crudos/casas.csv`, validación de esquema
(columnas PIR, etiqueta, nulos, rango temporal), construcción de
características incluyendo las columnas que definen los subgrupos de equidad
(p. ej. `franja_horaria`), y partición train/test estratificada con
`random_state = semilla`. Se sella el hash de los datos crudos y procesados.

### Paso 2 — Entrenamiento del modelo
Ajuste del clasificador (`config.modelo`, por defecto `RandomForestClassifier`)
con hiperparámetros y `random_state` declarados. Se produce un `ModeloSellado`
(estimador + versión + hash de parámetros + hash de datos + ruta serializada).

### Paso 3 — Explicabilidad (Principio 1)
`shap.TreeExplainer` sobre el modelo. Atribución **global** sobre una muestra
determinista (`config.explicabilidad.muestras_globales`) con figuras de
resumen y dependencia. Atribución **local** para cada fila del set de prueba,
guardada como artefacto por evento y referenciada desde la bitácora.

### Paso 4 — Equidad (Principio 2)
Desempeño desagregado por cada categoría de cada subgrupo
(`config.equidad.subgrupos`) y métricas de equidad con `fairlearn`
(demographic parity, equalized odds, TPR/FPR difference, selection rate
ratio). Cada métrica se contrasta con su **umbral PRE-DECLARADO** en
`config.equidad.umbrales`. Veredicto: aprueba solo si **todas** cumplen.
Un veredicto negativo no detiene el pipeline.

### Paso 5 — Trazabilidad (Principio 3)
Inferencia sobre el set de prueba registrando en `inferencias.jsonl`, por cada
evento: `id_evento`, `marca_temporal` (UTC), `referencia_entrada` (hash de la
fila), `salida_modelo` + `confianza`, `version_modelo`, `version_marco`,
`referencia_explicacion` (artefacto del paso 3), `responsable`. Después se
**verifica** la bitácora: JSON válido, esquema correcto, sin `id_evento`
duplicados, timestamps ordenados, cobertura 1:1 con el set de prueba,
`responsable` no placeholder.

### Paso 6 — Generación de evidencia auditable
Consolidación en `model_card.md`, `datasheet.md`, `reporte_cumplimiento.md` y
`bitacora_ejecucion.*`, más `manifiesto.json`: instantánea del entorno, copia
del `config.yaml` usado, y hashes de todas las entradas y salidas. El
manifiesto es lo que permite re-ejecutar y comparar bit a bit.

## Códigos de salida del pipeline
| Código | Significado |
|---|---|
| 0 | Pipeline completo, equidad aprueba |
| 2 | Pipeline completo, equidad **no** aprueba (evidencia válida) |
| 1 | Error de ejecución (no se pudo completar) |
