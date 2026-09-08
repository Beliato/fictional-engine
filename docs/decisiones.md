# Decisiones de diseño (para revisar)

Registro de decisiones tomadas al montar el esqueleto. Cada una es revisable
y reversible antes de empezar a implementar.

## D1 — Los 6 pasos del marco
El enunciado no los enumeraba. Se definieron como:
preparar datos · entrenar modelo · explicabilidad · equidad · trazabilidad ·
evidencia auditable. Los pasos 3-5 corresponden 1:1 con los tres principios.
**Revisar:** ¿el "entrenamiento" debe ser un paso del marco de *cumplimiento*
o una precondición externa? Si el modelo ya viene dado, el paso 2 pasa a ser
"carga y sellado del modelo".

## D2 — Idioma del código
Nombres de módulos, funciones y docstrings en español, para alinearse con el
dominio regulatorio (ENIA-CR) y el público del trabajo académico.
**Revisar:** si se prevé publicación internacional del código, quizá inglés.

## D3 — `src/comun/modelado.py`
El entrenamiento del modelo se ubicó en `comun/` (infraestructura compartida),
no en un cuarto módulo de `src/`. El enunciado pedía "tres módulos, uno por
principio" + procedimiento + comun.
**Revisar:** si prefiere `src/modelo/` como módulo propio.

## D4 — Versiones fijadas
Python 3.11. Conjunto NumPy 1.26.4 / pandas 2.2.2 / scikit-learn 1.4.2 /
shap 0.45.1 / fairlearn 0.10.0 / matplotlib 3.8.4 / pyyaml 6.0.1 / pytest 8.2.0.
Elegido por compatibilidad mutua conocida (NumPy < 2 evita fricción con shap).
**Revisar y confirmar** ejecutando `make setup && make lock`: `requirements.lock`
con el cierre transitivo es lo que hace el entorno realmente reproducible.
Considere además `pip install --require-hashes` sobre el lock para blindarlo.

## D5 — Bitácora en JSONL append-only
Una línea por inferencia, nunca se reescribe. Formato consultable con
herramientas estándar (`jq`, pandas). El `responsable` se toma de
`config.trazabilidad.responsable_por_defecto` salvo override por inferencia.
**Revisar:** ¿hace falta firma/encadenado de hashes (tipo log a prueba de
manipulación) o basta con append-only + verificación?

## D6 — Esquema de trazabilidad implementado
`src/trazabilidad/esquema.py` es el único módulo con lógica real (dataclass +
(de)serialización + validación de campos). Es "estructura", y es la pieza que
conviene revisar concretamente. Versionado con `VERSION_ESQUEMA = "1.0.0"`.
**Revisar:** los campos. En particular `referencia_entrada` guarda un **hash**
de la fila de entrada, no los datos crudos (monitoreo domiciliario = sensible).

## D7 — Subgrupos de equidad
Se propusieron `franja_horaria` (derivada de la marca temporal) y
`residente_id`. Son placeholders.
**Revisar:** qué atributos son relevantes y éticamente defendibles para el
análisis desagregado en este dominio, y si alguno requiere derivación.

## D8 — Umbrales de equidad
Valores iniciales: 0.10 para las diferencias, 0.80 para el ratio (regla del
80 %). **Deben** fijarse con criterio antes de correr nada y NO tocarse
después. Cambiarlos deja rastro en git.
**Revisar:** justificación de cada valor con literatura / marco legal.

## D9 — El fallo de equidad no aborta el pipeline
Código de salida 2 (no aprueba) ≠ 1 (error). Un veredicto negativo es un
resultado auditable, no una excepción.

## D10 — `filterwarnings = error` en pytest
Las pruebas fallan ante cualquier warning. Es estricto a propósito
(reproducibilidad), pero puede requerir listar excepciones concretas cuando
shap/sklearn emitan DeprecationWarnings.

## D11 — Datos y artefactos fuera de git
`datos/crudos/`, `datos/intermedios/` y `artefactos/` están en `.gitignore`
(solo `.gitkeep`). `config.yaml` y `requirements.lock` SÍ se versionan.
**Revisar:** si quiere versionar algún artefacto de referencia (p. ej. un
manifiesto "de oro") para comparación en CI.
