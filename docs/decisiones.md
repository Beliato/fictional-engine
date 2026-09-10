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

## D14 — El cargador rechaza claves desconocidas
`cargar_configuracion` falla no solo cuando falta una clave, sino también
cuando sobra una que no reconoce. El motivo es concreto: si alguien escribe
`demographic_parity_diference` (una `f`), con validación laxa ese umbral
desaparecería en silencio y con él la prueba que gobierna — y el reporte de
equidad diría "aprueba" sin haber medido esa métrica.

Es el mismo criterio que ya aplicaba `trazabilidad.esquema` con los campos de
la bitácora.
**Revisar:** el costo es que agregar una clave al `config.yaml` obliga a
tocar el cargador. Es deliberado (la config no debe crecer sin que el código
la contemple), pero conviene tenerlo presente.

## D15 — Los rangos de umbral se derivan del nombre, no de una lista
El cargador valida que los umbrales terminados en `_min` estén en (0, 1] —son
cocientes, como la regla del 80 %— y que el resto estén en [0, 1] —son
diferencias absolutas—.

La alternativa era incrustar en el código la lista de métricas válidas, pero
eso convertiría al cargador en una segunda fuente de verdad sobre qué se
evalúa, justo lo que el principio de "sin estado oculto" quiere evitar.
**Revisar:** si se agrega una métrica con otra semántica de rango (p. ej. un
estadístico no acotado), la convención de nombres se queda corta.

## D16 — `columnas_sensor_pir` vacía no es un error de configuración
La lista solo puede completarse tras inspeccionar el dataset CASAS concreto,
así que el cargador la acepta vacía. La exigencia de que no lo esté
corresponde a quien consuma los datos (`src/comun/datos.py`), que es donde
falta la información de verdad.
**Revisar:** cuando el dataset esté descargado y la lista completa, considerar
si el cargador debe pasar a exigirla no vacía.

## D17 — Una bitácora vacía es NO VÁLIDA
`verificar_registro` reporta la bitácora vacía como problema, no como caso
trivialmente correcto. El registro es el sustrato material de la rendición de
cuentas: cero inferencias registradas no evidencian el comportamiento de nada,
y un informe "válido" sobre un archivo vacío sería justamente el tipo de
evidencia hueca que el marco quiere evitar.
**Revisar:** si algún flujo legítimo verifica antes de registrar, este criterio
daría un falso negativo.

## D18 — El lote se valida entero antes de escribir la primera línea
`registrar_lote` construye y valida todos los registros y recién entonces
escribe. En una bitácora append-only no hay forma de retirar una línea ya
escrita, así que un lote a medias dejaría evidencia parcial imposible de
corregir sin romper la garantía de inmutabilidad.

El `fsync` va una sola vez al final del lote: la durabilidad del conjunto es
la misma y evita un fsync por fila, que en un set de prueba grande domina el
tiempo de ejecución.

## D19 — La versión de esquema se comprueba al construir el escritor
`RegistroEstructurado.__init__` exige que `config.trazabilidad.version_esquema`
coincida con `VERSION_ESQUEMA` del código, y falla si no. Escribir bajo una
versión y auditar bajo otra no evidencia nada; conviene enterarse antes de la
primera línea y no durante la auditoría.

## D20 — `referencia_explicacion` se resuelve contra la raíz del repositorio
Las referencias a artefactos de explicación se guardan relativas a la raíz
para que la bitácora siga siendo verificable al moverla de máquina. Una ruta
absoluta se respeta tal cual, pero ata la evidencia al equipo que la produjo.
**Revisar:** si el expediente se va a distribuir, conviene prohibir las rutas
absolutas también aquí, como ya hace el cargador de configuración.

## D21 — Dataset del piloto: Aruba anotado
Se evaluaron dos fuentes locales:

- **Consolidado CASAS** (189 hogares, 14 GB): muchos hogares, pero **ningún
  archivo tiene etiquetas de actividad** (se comprobaron los 189: todos con
  exactamente 4 columnas).
- **Aruba anotado** (1,7 M eventos, 2010-11-04 a 2011-06-11): una residente,
  11 actividades anotadas por spans `begin`/`end`.

La tarea declarada en la Tabla 10 es clasificación supervisada de actividades,
así que sin etiquetas no hay modelo: **Aruba es la única opción viable**, por
más hogares que tenga el consolidado.
**Revisar:** conseguir Milan, Cairo y Tulum anotados cerraría la brecha de
equidad (ver D23).

## D22 — Características por zona, no por sensor — y cómo se derivó el mapeo
Las características se nombran `conteo_Kitchen`, no `conteo_M018`. El R3.3
exige que la información de transparencia sea comprensible para destinatarios
no técnicos, y un identificador de sensor no lo es: SHAP atribuyendo peso a
"M018" no le dice nada a un cuidador.

El mapeo sensor -> zona **no se inventó**: se derivó cruzando por marca
temporal el Aruba anotado con el release consolidado oficial de CASAS, que
generaliza los sensores a nombres de habitación. Resultado: 1.596.509 eventos
coincidentes, 35 sensores mapeados, **100 % de acuerdo y cero ambigüedad**.

Ese cruce tiene un segundo valor, para el datasheet: **verifica la procedencia**
de la copia anotada (que vino de un repo de terceros) contra el release
oficial de CASAS, evento por evento.

## D23 — Los subgrupos de equidad son contextuales, no poblacionales
El R4.1 pide desagregar "entre subgrupos de la población monitoreada". Aruba
tiene UNA residente: no existen subgrupos poblacionales. Se retiró
`residente_id`, que habría colapsado a un único valor, y quedan dos subgrupos
**contextuales**: `franja_horaria` y `tipo_dia`.

Miden si el sistema funciona igual de bien en distintas condiciones, no si
discrimina entre personas. **Satisfacen el R4.1 solo parcialmente y el reporte
de equidad debe declararlo.**

Dos advertencias que van al reporte:

1. `franja_horaria` se deriva de la hora, y la hora es además variable de
   entrada del modelo: parte de la disparidad entre franjas es por diseño.
2. `tipo_dia` es relevante en este dominio y no una curiosidad: el README de
   Aruba dice que hijos y nietos visitaban con regularidad, así que el fin de
   semana concentra eventos que no son de la residente.

**Revisar:** cerrar la brecha exige datos anotados de varios hogares.

## D24 — Partición temporal por día, no aleatoria
Se cambió `particion.estratificar` por `particion.estrategia:
temporal_por_dia`. Los eventos de sensores están fuertemente
autocorrelacionados: repartir filas al azar deja ventanas contiguas del mismo
intervalo de actividad a ambos lados y produce exactitud optimista. Sobre esa
exactitud se calculan después explicabilidad y equidad, así que la fuga
contaminaría el expediente entero.

**La decisión ya dio fruto.** Con el corte temporal, `Housekeeping` tiene 368
ventanas en entrenamiento y **0 en prueba**: la actividad desaparece en los
últimos 44 días. `Wash_Dishes` cae del ~20 % esperado al 4,8 %. Es un
desplazamiento temporal real de la distribución que una partición aleatoria
habría ocultado por completo, y que hay que documentar en el model card.

## D25 — Ventanas disjuntas de 30 eventos
Los eventos se agrupan en ventanas que **no se solapan**, para que ninguna
fila comparta eventos con otra. La última ventana del crudo se descarta si
quedó incompleta: tendría conteos sistemáticamente menores y sería una fila
distinta a todas las demás.
**Revisar:** 30 es un valor inicial. Conviene justificarlo con literatura o
con un barrido documentado — pero el barrido, si se hace, va sobre
entrenamiento, nunca mirando la partición de prueba.

## D26 — Los sensores de temperatura no tienen zona
Los `T00x` miden una condición ambiental, no localizan a la persona, así que
no participan del conteo por zona: entran como característica propia
(`temp_T001`...). En cambio se exige que **estén presentes** en el crudo: un
sensor declarado que nunca reporta produciría una columna entera de nulos que
ningún relleno completa y que el clasificador no acepta.

Las lecturas ausentes en una ventana se arrastran de la anterior: que un
sensor no reporte no significa temperatura desconocida, sino que no cambió.

## D27 — Solo se admiten modelos de árbol
`MODELOS_ADMITIDOS` lista cuatro clases de sklearn, todas de árbol, y
`construir_estimador` rechaza cualquier otra.

No es una restricción arbitraria: el módulo de explicabilidad usa
`shap.TreeExplainer` (`config.explicabilidad.explainer`), que exige esa
familia. Admitir un modelo lineal dejaría el pipeline entrenando sin
problemas y reventaría —o peor, produciría atribuciones inválidas— recién en
el paso 4. El acoplamiento es deliberado y el §5.8 ya lo declara: el modelo
de referencia se elige por su compatibilidad con las técnicas de atribución.

La lista vive en el código y no en `config.yaml` porque es un mapeo de nombre
a clase de Python, no un parámetro.
**Revisar:** si se adopta otro explainer, hay que revisar esta lista con él.

## D28 — Se hashean los hiperparámetros efectivos, no el YAML
`hash_parametros` se calcula sobre `estimador.get_params()`, no sobre el
bloque `modelo.hiperparametros`. La diferencia importa: `get_params()`
incluye los valores por defecto que nadie declaró y que igualmente
condicionan el resultado. Un auditor necesita el estado real del estimador,
no el subconjunto que alguien escribió.

## D29 — Cargar un modelo de otra versión de scikit-learn es un error
`cargar_modelo` compara la versión de sklearn registrada al serializar con la
que corre, y lanza `ModeloIncompatible` si difieren. Un estimador
deserializado bajo otra versión puede cambiar de comportamiento sin aviso, y
entonces las predicciones dejarían de corresponder con las registradas en la
bitácora: el expediente no reconstruiría nada.
**Revisar:** es estricto a propósito. Si se necesita cargar modelos antiguos
para comparación histórica, habría que añadir un modo explícito que lo
permita dejando constancia.

## D30 — Sin `predict_proba` no hay modelo válido
`predecir_con_confianza` exige que el estimador exponga `predict_proba`, y la
confianza que devuelve es la probabilidad **de la clase efectivamente
predicha**, no el máximo de otra cosa. El esquema de la bitácora tiene un
campo `confianza` obligatorio por inferencia (R5.1); un modelo que no puede
producirlo no sirve como sujeto de prueba de este marco.

## D31 — Desempeño observado del modelo de referencia
Primera corrida completa sobre Aruba con partición temporal: exactitud 0,704,
exactitud balanceada 0,652, F1 macro 0,432, confianza media 0,565.

Son números modestos y **así debe ser**: la Tabla 10 declara que el modelo es
sujeto de prueba, no objeto de optimización. Perseguir exactitud aquí sería
salirse del alcance del trabajo. El F1 macro bajo refleja las clases raras y
el desplazamiento temporal del D24 —sklearn avisa `y_pred contains classes
not in y_true` porque el modelo predice `Housekeeping`, que no existe en
prueba—. Todo eso va al model card como limitación declarada, no como algo a
corregir.

## D32 — El contrato de ingesta: dónde termina el marco y empieza el dataset
El marco se aplica a *sistemas basados en sensores PIR*, no a CASAS. Hasta
esta refactorización eso era cierto para casi todo el código, pero
`cargar_crudo` tenía incrustado el formato de CASAS: separadores, posiciones
de campo y el vocabulario `begin`/`end`. Un equipo con su propio dataset
habría tenido que **editar `datos.py`**, y editar el instrumento no es
aplicarlo: los resultados dejan de ser comparables entre sistemas, que es
justo lo que el procedimiento promete.

Ahora la costura está declarada. `src/comun/lectores.py` define el contrato
—`marca_temporal`, `sensor`, `valor`, `actividad`, en orden— y `datos.py` ya
no conoce ningún formato. Integrar otro dataset es escribir un lector,
registrarlo y cambiar `datos.formato`.

La forma del contrato no es una abstracción inventada: **todo sistema de
sensores pasivos es un flujo de (cuándo, qué sensor, qué estado)**.

`leer_eventos` **verifica el contrato** sobre lo que devuelve el lector. Sin
esa verificación el contrato sería documentación; con ella, un adaptador mal
escrito falla en la costura y no tres pasos más adelante, con un error que ya
no señala la causa.

Hay una prueba que recorre el pipeline completo con un CSV de formato ajeno
sin tocar `datos.py`, `modelado.py` ni el procedimiento. Es la evidencia
verificable de que el marco es replicable, que hasta ahora era solo una
afirmación del documento.

## D33 — Las franjas horarias son configuración, no una constante
`_FRANJAS` estaba fija en el código. Es una decisión de dominio: un servicio
con turnos de noche distintos querría otros cortes, y ese cambio no debe
exigir tocar código. Pasó a `datos.franjas_horarias`.

El cargador exige que empiecen en 0 y que los cortes sean ascendentes: un
hueco dejaría horas sin franja, y una fila sin subgrupo desaparecería del
análisis desagregado sin que nadie lo note.

Se añadió además una **comprobación cruzada**: los nombres de las franjas
deben coincidir con `equidad.subgrupos[franja_horaria].categorias`. Cada
bloque puede ser válido por separado y el conjunto ser incoherente; esa
discrepancia no rompe la carga, reaparece como una categoría ausente en el
reporte de equidad, ya tarde.

## D34 — Ordenar los eventos es responsabilidad del lector
Lo encontró la verificación del contrato apenas se activó: el crudo de Aruba
**no viene perfectamente ordenado**, y `cargar_crudo` lo ordenaba en silencio
después de parsear.

Se movió el ordenamiento al lector. El contrato exige eventos en orden y cada
formato sabe cómo llegar a eso; que el marco lo arreglara por detrás
significaba que un lector podía entregar cualquier cosa y nadie se enteraba.
El orden es estable, para que dos eventos con la misma marca conserven el del
archivo — el único desempate reproducible disponible.

Verificado que la refactorización no cambió comportamiento: el hash de las
características sobre Aruba es idéntico antes y después.


## D35 — Perturbación `tree_path_dependent`
SHAP necesita simular la "ausencia" de una característica, y hay dos maneras.
`tree_path_dependent` sigue la cobertura de los propios árboles;
`interventional` promedia sobre un conjunto de fondo. Medido sobre el modelo
de referencia de Aruba (300 árboles, 11 clases):

| Método | Costo | Prueba completa (11.175) |
|---|---|---|
| `tree_path_dependent` | 95 ms/inferencia | ~18 min |
| `interventional`, fondo de 100 | 738 ms/inferencia | ~2,3 h |

Se eligió `tree_path_dependent`: es 8 veces más rápido, determinista y no
exige elegir —y justificar— un conjunto de fondo. Su costo conceptual queda
declarado en el reporte: con características correlacionadas puede repartir
el crédito de forma distinta que un método intervencional. Ambos los define
Lundberg et al. (2020), que el documento ya cita en el §5.8.

El cargador acepta `interventional`, pero `construir_explainer` lo rechaza con
`NotImplementedError`, como ya pasa con la partición aleatoria (D24).

## D36 — Toda inferencia de prueba es "relevante"; el artefacto es consolidado
El R3.1 exige explicar "toda predicción **relevante**" y la Tabla 8 registrar
"cada inferencia **relevante**", pero el documento nunca define el término.
En el piloto se consideran relevantes **todas** las inferencias de prueba: el
criterio de éxito (§5.7) es reconstruir el comportamiento completo del
sistema, y una selección dejaría decisiones sin explicación.
**Revisar:** conviene agregar esa definición en el texto de la tesis; un
tribunal puede preguntar qué es "relevante".

Explicar 11.175 inferencias con un archivo por explicación serían 11.175
archivos. Se guarda **un JSONL consolidado** con una línea por inferencia, y
la bitácora referencia `ruta#id_evento`. El verificador de trazabilidad se
extendió en consecuencia: con un fragmento, que el archivo exista no basta,
el registro concreto tiene que estar adentro. Si no, la bitácora estaría
citando una explicación que nadie calculó.

## D37 — La importancia global agrega las locales; `muestras_globales` pasa a `muestras_graficos`
La Tabla 6 define el R3.2 como la "agregación de las atribuciones locales
sobre el conjunto de evaluación". Se implementa literalmente: la importancia
global es la media de |contribución| sobre **todas** las explicaciones
locales. No hay un segundo cálculo SHAP: local y global son coherentes por
construcción y el costo no se paga dos veces.

Eso deja sin función el viejo `muestras_globales`, que decía cuántas filas se
usaban para la atribución global. Se **renombró** a `muestras_graficos` en
lugar de reinterpretarlo en silencio: ahora solo dice cuántos puntos se
dibujan en los gráficos de dependencia. Un nombre que afirma algo falso sobre
el cálculo es peor que un cambio incompatible en la configuración.

## D38 — Se explica la clase predicha, y la aditividad se comprueba
Un bosque multiclase produce una atribución por clase (19 × 11 valores por
inferencia). Se guarda la de la **clase predicha**, que es la que la
bitácora registra.

En un bosque de sklearn la atribución es exactamente aditiva:
`valor_base + Σ contribuciones = P(clase predicha)`, que es la confianza de
la bitácora. `calcular_explicaciones` lo comprueba para cada inferencia antes
de devolverla y lanza `AtribucionIncoherente` si alguna no suma. Cada
explicación trae así su propia prueba de que corresponde a la inferencia que
dice explicar.

## D39 — Enunciados en lenguaje llano por convención de nombres (R3.3)
`lenguaje.py` traduce las atribuciones dominantes a frases del tipo "Pesó a
favor: 9 activaciones de movimiento en Kitchen y la hora del día (8 h)". Se
construyen a partir de la convención de nombres de características de
`datos.py` (`conteo_<zona>`, `temp_<sensor>`...), que es del marco y no de un
dataset, así que valen para cualquier sistema que entre por el contrato de
ingesta.
**Revisar:** los nombres de zona salen de `datos.zonas` y en Aruba están en
inglés. Para cuidadores hispanohablantes conviene un mapeo de nombres para
mostrar; queda como limitación declarada en el reporte.

## D40 — Figuras según el método de visualización del proyecto
La importancia global es una magnitud sobre categorías sin orden natural:
barras horizontales ordenadas, **una sola serie en un solo color**, sin
leyenda (el título dice qué se grafica), barras de 24 px como máximo con el
extremo de dato redondeado, grilla en línea fina recesiva y etiquetas
directas solo en las características destacadas. El texto va en tinta, nunca
en el color de la serie, y la tabla de valores acompaña a cada figura en el
reporte como equivalente accesible.

Se usa la API orientada a objetos de matplotlib, sin `pyplot` (que tiene
estado global), con tamaño, DPI y metadatos fijos: dos corridas equivalentes
producen PNG idénticos byte a byte y el manifiesto puede hashearlos.

## D41 — Las plantillas de artefacto se rellenan en modo estricto
`rellenar_plantilla` falla si a un marcador `{{clave}}` le falta valor, y
también si se le pasa un valor que la plantilla no declara. Lo primero
dejaría `{{tabla}}` literal en un artefacto que va a un auditor; lo segundo
delata que se está rellenando la plantilla equivocada. Es el mismo criterio
del cargador de configuración (D14), y lo van a usar todos los artefactos
del paso 5.
