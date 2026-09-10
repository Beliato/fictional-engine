# Marco operativo — el procedimiento de aplicación (Tabla 9)

El marco verifica tres principios de la Estrategia Nacional de IA de Costa Rica
(ENIA-CR), articulados con el AI Act de la UE y el NIST AI RMF, sobre un
sistema de IA que clasifica actividad domiciliaria a partir de sensores PIR
(dataset CASAS). Produce evidencia auditable y reproducible.

El procedimiento es el **cuarto componente** del marco: la secuencia
documentada y replicable mediante la cual un equipo de desarrollo aplica el
marco a su sistema. Por eso los pasos de este repositorio son, uno a uno, los
de la Tabla 9 del documento: el criterio de éxito del piloto es haber
ejecutado ese procedimiento íntegramente.

## Los 3 principios y su articulación normativa

| Principio | ENIA Costa Rica | AI Act EU | NIST AI RMF |
|---|---|---|---|
| **Explicabilidad** | Transparencia y explicabilidad | Art. 13 (transparencia) | MEASURE 2.9 |
| **Equidad** | Equidad y no discriminación | Art. 10 (gobernanza de datos y sesgos) | MEASURE 2.11 |
| **Trazabilidad** | Rendición de cuentas y trazabilidad | Art. 12 (conservación de registros) | GOVERN 1.4 / MANAGE 4.1 |

> El mapeo concreto de artículos/subcategorías es **provisional** y debe
> validarlo un especialista legal. Vive en `config.yaml`
> (`articulacion_normativa`) para que sea explícito y versionado.

## Precondiciones (no son pasos del marco)

El marco recibe el sistema de IA como entrada. El modelo actúa como **sujeto
de prueba, no como objeto de optimización**, así que ni preparar los datos ni
obtener el modelo son actividades de cumplimiento: son precondiciones que
deben estar resueltas antes de que el procedimiento empiece. Viven en
`pasos.PRECONDICIONES`.

Si una precondición falla, es un **error de ejecución** (código 1), no un
hallazgo de cumplimiento.

### Precondición A — Preparación de datos
Lectura del crudo con el lector declarado en `datos.formato` (ver
`docs/aplicar-a-otro-dataset.md`), validación de esquema (sensores declarados
presentes, zonas asignadas, orden temporal), construcción de características
por ventana —incluidas las columnas que definen los subgrupos de equidad, p.
ej. `franja_horaria`— y partición temporal por día. Se sella el hash de los
datos.

### Precondición B — Sellado del modelo
Si el modelo viene dado, se carga y se sella. Si el caso de estudio exige
producirlo, se ajusta con los hiperparámetros y `random_state` de
`config.modelo`. En ambos casos el producto es un `ModeloSellado` (estimador +
versión + hash de parámetros + hash de datos + ruta serializada), y su
desempeño **no** se optimiza en función de las pruebas posteriores.

## Los 6 pasos del procedimiento

| # | Actividad | Producto | Función NIST | Requerimientos |
|---|---|---|---|---|
| 1 | Caracterización del sistema | Ficha de caracterización | MAPEAR | insumo de R5.2 |
| 2 | Documentación del conjunto de datos | Datasheet | MAPEAR | R4.3 |
| 3 | Declaración de criterios de evaluación | Protocolo declarado | MAPEAR | R4.2 |
| 4 | Ejecución de las pruebas técnicas | Resultados + bitácora | MEDIR | R3.1, R3.2, R3.3, R4.1, R4.2, R5.1 |
| 5 | Generación de artefactos auditables | Reportes + model card | GOBERNAR | R5.2 |
| 6 | Verificación de auditabilidad | Expediente de evidencia | GESTIONAR | R5.3 |

### Paso 1 — Caracterización del sistema
Descripción del sistema evaluado, su finalidad, su población destinataria y la
configuración de sensores empleada. Producto: `ficha_caracterizacion.md`. Es
lo que la función MAPEAR exige tener escrito antes de medir nada.

### Paso 2 — Documentación del conjunto de datos
Procedencia, composición, representatividad de subgrupos y sesgos potenciales
del dataset. Producto: `datasheet.md` (R4.3).

### Paso 3 — Declaración de criterios de evaluación
Subgrupos de comparación, métricas de equidad y umbrales de referencia, todos
declarados **antes** de ejecutar las pruebas del paso 4. Producto:
`protocolo_evaluacion.md` (R4.2).

Este paso sella el hash SHA-256 de `config.yaml` en `ctx.hash_protocolo`. El
paso 6 lo vuelve a comprobar. Es la diferencia entre afirmar que los umbrales
no se ajustaron a los resultados y **poder demostrarlo**.

### Paso 4 — Ejecución de las pruebas técnicas
Aplicación de los tres módulos de principio sobre el modelo sellado.

- **Explicabilidad** — `shap.TreeExplainer` con perturbación
  `tree_path_dependent`. Atribución local de **toda** inferencia de prueba
  (R3.1), guardada en un único artefacto consolidado que la bitácora
  referencia como `archivo#id_evento`; importancia global como media de
  |contribución| sobre todas esas explicaciones, sin un segundo cálculo SHAP
  (R3.2); y traducción de las atribuciones dominantes a enunciados
  comprensibles para destinatarios no técnicos (R3.3).
- **Equidad** — desempeño desagregado por cada categoría de cada subgrupo
  (`config.equidad.subgrupos`, R4.1) y métricas con `fairlearn` contra los
  umbrales sellados en el paso 3 (R4.2). Aprueba solo si **todas** cumplen.
  Un veredicto negativo no detiene el pipeline: es evidencia.
- **Trazabilidad** — inferencia sobre el set de prueba registrando en
  `inferencias.jsonl`, por evento: `id_evento`, `marca_temporal` (UTC),
  `referencia_entrada` (hash de la fila), `salida_modelo` + `confianza`,
  `version_modelo`, `version_marco`, `referencia_explicacion`, `responsable`
  (R5.1). Luego **verifica** el registro: JSON válido, esquema correcto, sin
  `id_evento` duplicados, timestamps ordenados, cobertura 1:1 con el set de
  prueba, `responsable` no placeholder.

### Paso 5 — Generación de artefactos auditables
Elaboración del reporte de explicabilidad, el reporte de equidad y el model
card a partir de los resultados del paso 4. El model card documenta propósito,
desempeño desagregado, limitaciones y condiciones de uso (R5.2).

### Paso 6 — Verificación de auditabilidad
Comprobación de que los artefactos y la bitácora permiten **reconstruir y
atribuir** las decisiones del sistema (R5.3):

- cada inferencia se puede reconstruir ex post y atribuir a un responsable
  identificable,
- `ctx.hash_protocolo` sigue coincidiendo con el `config.yaml` usado,
- los nueve requerimientos tienen su artefacto presente y con hash registrado.

Cierra con `bitacora_ejecucion.*` y `manifiesto.json`: instantánea del
entorno, copia del `config.yaml` usado y hashes de todas las entradas y
salidas. El manifiesto es lo que permite re-ejecutar y comparar bit a bit.

## Códigos de salida del pipeline
| Código | Significado |
|---|---|
| 0 | Procedimiento completo, equidad aprueba |
| 2 | Procedimiento completo, equidad **no** aprueba (evidencia válida) |
| 1 | Error de ejecución (no se pudo completar) |
