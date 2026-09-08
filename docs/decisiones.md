# Decisiones de diseño (para revisar)

Registro de decisiones tomadas al montar el esqueleto. Cada una es revisable
y reversible antes de empezar a implementar.

## D1 — Los 6 pasos del marco — RESUELTA
Al montar el esqueleto los pasos se definieron como: preparar datos · entrenar
modelo · explicabilidad · equidad · trazabilidad · evidencia auditable, y se
dejó abierta la pregunta de si el entrenamiento era un paso del marco de
*cumplimiento* o una precondición externa.

**El documento la contesta.** La Tabla 10 declara que "el modelo actúa como
sujeto de prueba, no como objeto de optimización": es precondición. Y la
Tabla 9 fija el procedimiento en seis pasos distintos de los que tenía el
esqueleto.

Los pasos se realinearon 1:1 con la Tabla 9 (caracterización · documentación
de datos · declaración de criterios · ejecución de pruebas · generación de
artefactos · verificación de auditabilidad). Preparar datos y sellar el modelo
bajaron a `pasos.PRECONDICIONES`. Los tres módulos de principio, que antes
eran los pasos 3-5, ahora se aplican dentro del paso 4 y se consolidan en el 5.

Motivo de fondo: el criterio de éxito del piloto (§5.7) es haber ejecutado
íntegramente el procedimiento de la Tabla 9. Si el código sigue otra
descomposición, esa afirmación hay que defenderla en prosa en vez de mostrarla.

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

## D12 — "Previo al entrenamiento" en el datasheet (R4.3)
El requerimiento R4.3 y el paso 2 de la Tabla 9 piden documentar la
composición del dataset **antes del entrenamiento del modelo**. En el pipeline,
sin embargo, el sellado del modelo es una precondición y ocurre antes del
paso 2.

Se interpretó "previo al entrenamiento" como una exigencia normativa sobre el
**contenido y la procedencia** del artefacto (documentar el dataset tal como
estaba antes de entrenar, sin información derivada de los resultados del
modelo), no como un orden de ejecución del pipeline. Es coherente con un marco
que audita un sistema ya construido.

**Revisar:** si prefiere honrarlo también como orden — el datasheet se
generaría entre las dos precondiciones — o si alcanza con dejar la
interpretación escrita aquí y en el propio datasheet. La segunda opción es más
simple; la primera es más literal y más fácil de defender si alguien del
tribunal la señala.

## D13 — Sellado del protocolo por hash
El paso 3 sella el SHA-256 de `config.yaml` en `ctx.hash_protocolo` y el paso 6
lo vuelve a comprobar. Sin esto, "los umbrales se declararon antes" es una
declaración de buena fe: el historial de git lo respalda, pero no queda dentro
del expediente de evidencia que se entrega.
**Revisar:** si conviene sellar además el commit de git, y qué debe pasar si
el hash no coincide — hoy se propone marcar la evidencia de equidad como no
válida sin abortar la corrida, en la misma lógica del D9.
