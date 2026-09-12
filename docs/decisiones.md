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
shap 0.45.1 / matplotlib 3.8.4 / pyyaml 6.0.1 / pytest 8.2.0 (`fairlearn`
0.10.0 figuraba al principio y se retiró en D45).
Elegido por compatibilidad mutua conocida (NumPy < 2 evita fricción con shap).
**Resuelto.** `requirements.lock` se generó con `make lock`: 28 paquetes con
el cierre transitivo completo. Antes de congelarlo se desinstaló `fairlearn`
del entorno, que seguía instalado de cuando era dependencia (D45): un lock que
congela un paquete que el proyecto ya no declara no prueba nada sobre el
entorno que corrió.

El lock fija `pyparsing` 3.3.2, la versión cuya deprecación obliga al filtro
de `pyproject.toml` (D10). Con el cierre congelado, ese filtro deja de ser un
parche contra una versión que flota y pasa a documentar una versión concreta.
**Revisar:** `pip install --require-hashes` sobre el lock lo blindaría contra
sustituciones en el índice de paquetes.

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
**Actualización:** antes de calcular ninguna métrica, D42 sacó del veredicto
la paridad demográfica y la regla del 80 %, y D43 agregó el soporte mínimo.
Los umbrales que quedan siguen en 0.10.

## D9 — El fallo de equidad no aborta el pipeline
Código de salida 2 (no aprueba) ≠ 1 (error). Un veredicto negativo es un
resultado auditable, no una excepción. Un veredicto no evaluable (D43)
también sale con 2: no es un aprobado.

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

## D15 — Los rangos de umbral se derivan del nombre, no de una lista — REEMPLAZADA por D44
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

## D42 — Deciden la igualdad de oportunidades y los falsos positivos; la paridad se reporta
La Tabla 5 de la tesis nombra para el R4.2 la "paridad demográfica" y la
"igualdad de oportunidades". Con los subgrupos del piloto, la primera no mide
sesgo. Exige que cada actividad se prediga con la misma frecuencia en todas
las categorías, y las frecuencias reales difieren. En las etiquetas de prueba
—composición de los datos, no resultados del modelo—, `Sleeping` es el
23,1 % de las ventanas de madrugada y el 0,2 % de las de tarde. Un modelo
perfecto tendría una diferencia de paridad de 0,23 y reprobaría el umbral de
0,10 sin tener ningún sesgo. La regla del 80 % tiene el mismo problema,
agravado: viene de la selección de personal, donde existe un resultado
"favorable", y aquí no lo hay.

Deciden el veredicto las dos métricas que condicionan en la actividad real:
la diferencia de tasas de verdaderos positivos (igualdad de oportunidades) y
la de falsos positivos. Juntas equivalen a probabilidades igualadas (Hardt et
al., 2016). La paridad y la regla del 80 % se calculan y se reportan como
**descriptivas**, con esta justificación. No se descartan porque la tesis las
nombra.

La elección es del despliegue, no del marco. Con subgrupos poblacionales y
frecuencias comparables, la paridad puede volver al veredicto moviéndola de
`descriptivas` a `umbrales`. La nota de la Tabla 7 de la tesis lo respalda:
la calibración definitiva de los umbrales "se establece durante la
implementación del módulo".
**Revisar:** que el texto del R4.2 en la tesis refleje la distinción entre las
métricas que deciden y las que describen.

## D43 — Multiclase: cada actividad contra el resto, con soporte mínimo
Las métricas de equidad están definidas para una salida binaria. Con 11
actividades, cada una se evalúa contra el resto, y su disparidad en un
subgrupo es la diferencia entre la tasa máxima y la mínima de sus
categorías.

Una tasa se calcula solo si su denominador en la categoría llega a
`equidad.soporte_minimo` casos (30 en el piloto). Para la tasa de verdaderos
positivos, el denominador son las ventanas de la actividad real; para la de
falsos positivos, las del resto. Las categorías por debajo quedan fuera de la
comparación y el reporte las nombra. Si quedan menos de dos, la combinación
es **no evaluable**: ni se descarta en silencio ni cuenta como aprobada.

El veredicto tiene tres estados:
- **Aprueba:** toda combinación evaluable respeta su umbral.
- **No aprueba:** alguna combinación evaluable lo excede.
- **No evaluable:** ninguna combinación llegó al soporte mínimo.

El reporte declara siempre la cobertura: cuántas combinaciones se evaluaron,
de cuántas posibles.

Por qué se fija ahora: `fairlearn` 0.10.0 devuelve 0,0 en silencio para la
paridad demográfica con etiquetas multiclase, porque toma `pos_label=1`, que
no existe. Eso es un "aprueba" falso. Con probabilidades igualadas, en cambio,
lanza un error.

Consecuencia que el reporte debe decir: `Bed_to_Toilet` tiene 8 casos en
prueba, todos de madrugada, y no es evaluable. Los viajes nocturnos al baño,
clínicamente relevantes por el riesgo de caídas, no se pueden auditar por
equidad con este dataset.
**Revisar:** con 30 casos, el error estándar de una tasa cercana a 0,8 es
≈0,07, y el de la diferencia entre dos categorías ≈0,10: del mismo orden que
el umbral. Con poco soporte, un resultado cercano al umbral no se distingue
del ruido. El reporte muestra el n de cada celda para que se lea así. Una
mejora posible es acompañar cada diferencia con un intervalo de confianza.

## D44 — Catálogo cerrado de métricas de equidad (reemplaza D15)
El cargador valida los nombres de métrica contra `METRICAS_EQUIDAD`. El
catálogo asocia a cada métrica su sentido de cumplimiento: una diferencia
cumple si no supera el umbral; un cociente, si no baja de él.

D15 evitó esa lista para no crear una segunda fuente de verdad sobre qué se
evalúa. Pero el catálogo no dice qué se evalúa, cosa que sigue en
`config.yaml`. Dice qué sabe calcular el marco, igual que `PERTURBACIONES` o
`MODELOS_ADMITIDOS`. Y la convención de nombres dejaba abierto el hueco que
D14 quería cerrar: `demographic_parity_diference` pasaba la validación de
rango, nadie la calculaba, y el veredicto aprobaba sin haberla medido.

Con el catálogo, `selection_rate_ratio_min` pasa a llamarse
`selection_rate_ratio`: el sentido lo da el catálogo, no el sufijo. Además,
una métrica no puede estar a la vez en `umbrales` y en `descriptivas`.

## D45 — Implementación de equidad: tasas propias, contraste exacto, sin `fairlearn`
Las tasas se calculan con conteos explícitos, y cada una conserva su
numerador y su denominador para que un auditor pueda rehacer la cuenta.
`fairlearn` se retiró de las dependencias: no quedaba usada, y con etiquetas
multiclase era la trampa de D43.

Decisiones de detalle:
- **Contraste exacto.** La disparidad se compara con el umbral en
  fracciones, no en coma flotante: 0,8 − 0,7 da 0,10000000000000009 y
  reprobaría un umbral de 0,10 que la diferencia real iguala. Una diferencia
  igual al umbral lo cumple.
- **Qué actividades se evalúan.** Las que aparecen en las etiquetas reales o
  en las predicciones. Una actividad que el modelo predice pero que nunca
  ocurre en la prueba (`Housekeeping`, en el piloto) no tiene tasa de
  verdaderos positivos, pero sí de falsos positivos: sus falsas alarmas
  también pueden repartirse de forma desigual.
- **Probabilidades igualadas** es la mayor de las dos diferencias y solo es
  evaluable si ambas lo son. El **cociente de selección** no es evaluable si
  ninguna categoría comparable tiene predicciones de la actividad (0/0).
- **Desempeño desagregado (R4.1).** Precisión, exhaustividad y F1 se
  promedian en macro sobre las actividades presentes en las etiquetas reales
  de cada categoría; una actividad que ocurre y nunca se predice aporta
  cero.
- **Categorías.** Una categoría que aparece en los datos sin estar declarada
  es un error, no una fila menos. Una declarada sin ventanas aparece con
  n = 0 y sin métricas.
- **Justificaciones y limitaciones como datos.** Pasaron de comentarios del
  YAML a `subgrupos[].justificacion` y `equidad.limitaciones`: el reporte
  las cita tal cual y el código no sabe nada del dataset.
- **Umbrales de solo lectura.** `equidad.umbrales` se carga como un mapeo
  inmutable: `frozen=True` no alcanzaba a los valores de un diccionario.
- **Código de salida.** Un veredicto no evaluable sale con 2, como uno que
  no aprueba (D9).
**Revisar:** la justificación de `franja_horaria` es un borrador; conviene
reescribirla con el criterio del dominio.

## D46 — La descripción del sistema y del dataset son datos, no código
Los pasos 1 y 2 producen la ficha de caracterización y el datasheet. Lo que
esos documentos afirman —finalidad, población destinataria, contexto de
despliegue, procedencia del dataset, consentimiento, licencia— el marco no lo
puede derivar: son declaraciones del despliegue. Viven en los bloques
`sistema` y `datos.documentacion` de `config.yaml`, y el código las copia sin
interpretarlas, igual que las limitaciones de equidad (D45). Auditar otro
sistema es reescribir esos bloques, no tocar el código.

El cargador los exige completos y no vacíos: un apartado en blanco en la
ficha se lee como "no aplica" cuando en realidad significa "nadie lo
escribió".

Lo que sí deriva el marco: número de instancias antes y después de preparar,
clases y su distribución, ventana temporal, hashes, y la descripción de las
transformaciones y de la derivación de subgrupos, armada desde la propia
configuración. Así el datasheet no puede contradecir lo que el pipeline hizo.

**Responsable declarado.** `trazabilidad.responsable_por_defecto` nombra a
los dos autores de la tesis: es quien responde por las inferencias del piloto
(Tabla 8, R5.3). La prueba que comprueba que el verificador detecta el
placeholder dejó de depender del valor del repositorio y declara el suyo.

**Licencia del dataset.** El depósito de CASAS en Zenodo (2025) publica estos
hogares bajo CC BY 4.0 (DOI 10.5281/zenodo.15708568). La copia usada aquí
proviene de la distribución anterior, cuyo README pedía no redistribuir sin
permiso expreso; el crudo sigue fuera del repositorio y el datasheet declara
las dos cosas.

**Dos hashes de datos.** Se sellan por separado el crudo tal como se leyó y
el cuadro de características. Un auditor puede comprobar el origen y la
preparación sin depender de que el otro sea correcto.

**Marcas temporales.** La bitácora de inferencias registrará la hora real de
cada inferencia, como pide la Tabla 8 ("fecha y hora de la inferencia"), y la
ficha declara la fecha de caracterización. En consecuencia, los artefactos
que llevan la identidad de la corrida —ficha, protocolo, bitácora y
manifiesto— no son byte-idénticos entre ejecuciones, mientras que los
técnicos —explicabilidad, equidad— sí lo son. La comparación entre corridas
se hace sobre estos últimos y sobre el contenido de los primeros sin su marca
de tiempo.
**Revisar:** los textos de `sistema` son un borrador redactado a partir del
Capítulo 1 y de la Tabla 10; conviene revisarlos con criterio propio, en
especial la finalidad y las vías de impugnación.

## D47 — Sellado del protocolo, identidad de las inferencias y bitácora irrepetible
El paso 3 sella el **hash del archivo** `config.yaml`, no el de la
configuración ya cargada. Un auditor lo reproduce con `sha256sum config.yaml`
sin ejecutar nada del marco, y por eso `Configuracion` recuerda de qué
archivo se cargó. El paso 6 lo volverá a comprobar (D13).

La tabla de métricas y umbrales del protocolo y la del reporte de equidad
salen de la misma función. Si cada artefacto la construyera por su cuenta,
el expediente podría afirmar dos protocolos distintos para la misma corrida.

**Identificador de inferencia.** `ven-NNNNN`, la posición de la ventana en el
conjunto de evaluación ordenado temporalmente. Es estable mientras lo sean
los datos y la partición, y ambos están sellados por hash. La bitácora, las
explicaciones locales y la verificación de cobertura usan el mismo
identificador, que es lo que permite ir de una decisión a su explicación
(R5.1, R5.3).

**Referencia de entrada.** SHA-256 de la fila de características, no los
eventos. La bitácora de un sistema de monitoreo domiciliario no debe
contener la rutina de la vivienda: el hash prueba qué entrada produjo la
inferencia sin volver a exponerla (Tabla 8).

**La bitácora no se reabre.** Si el archivo ya tiene registros, el paso 4
falla en vez de añadir. Es append-only por diseño (D5): mezclar dos corridas
produciría identificadores duplicados y una evidencia que no corresponde a
ninguna de las dos. Archivar o borrar es una decisión de quien opera, no del
marco, así que el error dice qué hacer y se detiene.

**Justificación de los umbrales como dato.** `equidad.justificacion_umbrales`
la declara y el protocolo la copia. El 0,10 es un criterio propio, no
normativo, y así queda dicho: la tesis deja la calibración definitiva a un
panel de especialistas (Capítulo 6).

**Instantánea del entorno.** Declara el commit de git **y** si el árbol de
trabajo tenía cambios sin confirmar. Un commit con el árbol sucio no
identifica el código que corrió; omitir ese detalle haría el manifiesto más
prolijo y menos cierto.

## D48 — Los nueve requerimientos viven en el código; el expediente se sella al final
El criterio de éxito del piloto es que la corrida genere los artefactos de
los **nueve requerimientos** y que permitan reconstruir el comportamiento del
sistema (Tabla 10). Para poder comprobarlo hacía falta una correspondencia
explícita entre cada requerimiento y su evidencia, que hasta ahora no existía
en ninguna parte: `config.yaml` solo declaraba la articulación normativa por
principio.

Esa correspondencia vive en `src/procedimiento/requerimientos.py`, no en la
configuración. Los nueve requerimientos son la definición del marco —el
producto de la tesis—, no parámetros del despliegue, igual que
`METRICAS_EQUIDAD`. Los enunciados son los de la Tabla 5, textuales.

Un artefacto cuenta como evidencia solo si su ruta está registrada **y** el
archivo existe. Una ruta anotada sin archivo detrás documentaría una
evidencia que nadie puede abrir.

**R3.3 tiene dos artefactos.** La Tabla 5 lo asigna al model card ("secciones
de uso previsto, desempeño y limitaciones en lenguaje llano"), y el marco
produce además los enunciados en lenguaje llano del reporte de
explicabilidad. Se cuentan los dos.

**El reporte de cumplimiento se emite en el paso 6, no en el 5.** Declara la
cobertura de los nueve requerimientos, que solo puede comprobarse cuando ya
existen todos los artefactos. La Tabla 9 asigna al paso 5 el reporte de
explicabilidad, el de equidad y el model card, que es lo que ese paso genera.

**Orden dentro del paso 6:** primero comprobar (hash del protocolo, bitácora,
cobertura), después documentar lo comprobado, y sellar al final. El
manifiesto hashea los artefactos ya escritos, así que cualquier cosa emitida
después quedaría fuera del sello.

**Dos veredictos distintos.** El reporte de cumplimiento separa "falta
evidencia" de "la evidencia muestra un incumplimiento":
- **EVIDENCIA INCOMPLETA:** algún requerimiento sin artefacto.
- **NO CUMPLE:** evidencia completa, pero la equidad no aprueba o la
  trazabilidad tiene hallazgos.
- **CUMPLE:** evidencia completa, equidad aprobada y bitácora verificada con
  el protocolo intacto.

**Código de salida.** 0 solo si la equidad aprueba y los nueve requerimientos
están cubiertos; 2 para cualquier hallazgo, incluida la evidencia incompleta;
1 solo para errores de ejecución. Un hallazgo no es una excepción (D9).

**Qué se puede comparar entre corridas.** Los artefactos que llevan la
identidad de la corrida —ficha, protocolo, datasheet, reportes, bitácora,
manifiesto— cambian con el identificador y la marca de tiempo. Lo que debe
repetirse es el contenido: con el mismo identificador, dos corridas producen
los mismos hashes de datos, de modelo y de los artefactos técnicos. La prueba
de integración lo verifica así.

## D49 — La demo deriva su configuración y escribe aparte
El pipeline completo tarda unos 17 minutos, casi todo en explicar con SHAP las
11.175 inferencias del conjunto de evaluación. Eso no se puede mostrar en
vivo, así que `make demo` corre **el mismo procedimiento** sobre los primeros
20 días: 4.457 ventanas, 1.054 inferencias, 28 segundos.

La configuración de la demo se **deriva** de `config.yaml` en vez de mantener
una copia. Dos configuraciones paralelas se desincronizan, y entonces la demo
dejaría de mostrar el protocolo real: mismos umbrales, mismos subgrupos, mismo
soporte mínimo, mismo modelo. Lo único que cambia es cuántos datos entran y
dónde se escriben los artefactos. `config.demo.yaml` es generado y no se
versiona.

**El corte es por día, no por número de líneas.** La partición del marco es
temporal: un día a medias produciría una ventana que mezcla jornadas.

**Todas las rutas de artefactos se reubican, incluida `rutas.artefactos`.** La
primera versión solo reescribía las que empiezan con `artefactos/`, y esa
clave vale exactamente `artefactos`, sin barra. Como los módulos de
explicabilidad y equidad derivan sus subcarpetas de ella, la demo escribió
encima del expediente del piloto y hubo que regenerarlo. El expediente de una
corrida no puede depender de que otra no lo pise.

**`make` no trata el código 2 como fallo.** El orquestador devuelve 2 cuando
hay hallazgos —equidad que no aprueba o evidencia incompleta— y eso no es un
error de ejecución (D9). El target falla solo con código 1.

El guion de la demostración está en `docs/demo.md`: qué mostrar, en qué orden
y qué preguntas responde cada artefacto.

## D50 — El contrato admite varias viviendas
El contrato de ingesta gana una quinta columna **opcional**: `hogar`. Aparece
cuando el dataset cubre varias viviendas, y cambia tres cosas aguas abajo.

**Por qué.** El R4.1 pide desagregar "entre subgrupos de la población
monitoreada". Con una sola residente eso era imposible y quedó declarado como
limitación (D23). Con varias viviendas cada hogar es una persona distinta, así
que comparar entre hogares **es** comparar entre la población: el subgrupo
deja de ser contextual y pasa a ser poblacional.

**`hogar` no es una característica.** Es clave de agrupación y columna
sensible, y se excluye de forma explícita del cuadro que ve el modelo. Que el
modelo aprendiera a distinguir viviendas sería justamente lo que el análisis
desagregado quiere poder descartar.

**Las ventanas no cruzan hogares.** Una ventana que mezclara dos viviendas
sería una fila que no describe a nadie. El identificador de ventana lleva el
hogar y la posición dentro de él.

**La partición es temporal dentro de cada hogar.** Los últimos días de cada
vivienda van a prueba, no los últimos días del conjunto. Si se partiera
global, una vivienda podría quedar entera de un lado y su desempeño no sería
comparable con el de las demás. Un hogar con menos de dos días distintos es un
error, y el mensaje dice de cuál se trata.

**El orden que exige el contrato pasa a ser por hogar.** Con varias viviendas
el orden global no significa nada; lo que la ventana y la partición necesitan
es que cada hogar venga en un bloque contiguo y ordenado. El verificador del
contrato comprueba las dos cosas.

**Lo propio del formato sigue en el lector.** `LectorEventosCASASCSV` lee un
archivo o un directorio —el nombre del archivo pasa a ser el hogar— y resuelve
una ambigüedad del dataset: `OutsideDoor` reporta ON/OFF como sensor de
movimiento y OPEN/CLOSE como puerta. Como el marco distingue sensores por
nombre, los eventos de puerta se renombran a `<sensor>_Puerta`. La ambigüedad
es del dataset y se resuelve donde vive lo propio de cada formato.

**Limitación declarada.** Las viviendas no tienen las mismas habitaciones. Las
características son la unión de zonas, así que un hogar sin comedor tiene
`conteo_DiningRoom` en cero en todas sus ventanas. Eso es información real
sobre la instalación, pero conviene que el reporte lo diga: una zona ausente y
una zona sin actividad se ven igual en la tabla.

Verificado sobre datos reales del depósito oficial (`hh124` y `hh127`): 64.217
eventos, ventanas por vivienda, las dos presentes en entrenamiento y en
prueba, y `hogar` fuera de las 12 características del modelo.

## D51 — Protocolo del piloto multi-hogar
Segundo piloto, sobre nueve viviendas de adultos mayores del depósito oficial
de CASAS en Zenodo (DOI 10.5281/zenodo.15708568, CC BY 4.0). Todo lo que
sigue se declaró antes de calcular ninguna métrica.

**Selección de viviendas.** Los hogares `hh101` a `hh110` con al menos 30 días
de registro, truncados a sus primeros 30 días. Quedan nueve: `hh110` tiene 27
días y la regla lo excluye. El truncado uniforme acota el costo de la corrida
y, sobre todo, evita que la comparación entre personas dependa de cuánto se
observó a cada una: contrastar una vivienda de 497 días contra una de 30
confundiría disparidad con tiempo de observación. La regla vive en
`scripts/preparar_hogares.py`, así que es reproducible.

**`hogar` decide el veredicto.** Cada vivienda es una persona o unidad
doméstica distinta, así que comparar entre hogares es comparar entre la
población monitoreada: es lo que pide el R4.1 y lo que el piloto de Aruba no
podía hacer (D23). Con nueve categorías, la diferencia entre la mejor y la
peor es más exigente que con dos. **El umbral no se ajusta por eso**: ajustarlo
para que el veredicto salga mejor sería exactamente lo que el sellado del
protocolo existe para impedir. La cobertura declarada en el reporte permite
leer el resultado con ese contexto.

**Mapeo de actividades.** El vocabulario trae 39 etiquetas, con las variantes
de un mismo quehacer separadas por momento del día (`Cook_Breakfast`,
`Cook_Lunch`, `Cook_Dinner`). Sin agrupar, muchas clases quedan con un puñado
de casos y la equidad no se puede evaluar en casi ninguna. Se agrupan catorce
etiquetas en cinco clases —Cook, Eat, Wash_Dishes, Work, Take_Medicine— y
quedan 25 clases. El mapeo se aplica en una sola pasada y el cargador rechaza
que un destino sea también origen: el resultado dependería del orden de las
claves del YAML.

**Exclusiones.** `Nap` (6 eventos) y `Exercise` (9), por el mismo criterio que
`Respirate` en Aruba: con esa cantidad no se puede partir ni evaluar.

**Expediente aparte.** Los artefactos van a `artefactos/hogares/`. Dos
corridas no pueden pisarse la evidencia, que fue la lección de D49.

**Aruba no se retira.** Queda como `config.yaml`, y el marco corre sobre los
dos datasets con formatos distintos sin tocar una línea del núcleo. Es la
demostración de que el contrato de ingesta cumple lo que prometía.

**Composición resultante**, para el datasheet: 1.226.316 eventos, una línea
descartada, 40.866 ventanas repartidas entre 2.050 y 6.624 por vivienda, y 25
clases. Dos cambios que importan frente a Aruba:

- `Bed_Toilet_Transition` pasa de 40 ventanas a **322**. Los traslados
  nocturnos al baño, clínicamente relevantes por el riesgo de caídas, dejan de
  ser inauditables (era la limitación más incómoda de D43).
- Aparece `Take_Medicine` con 388 ventanas, que es adherencia a la
  medicación, y `Otro` baja del 53,8 % al 35,2 %: la anotación cubre más
  comportamiento real.

**Limitación que persiste.** El dataset no publica edad, sexo ni condición de
salud de cada residente. Los subgrupos son poblacionales pero no demográficos:
se compara entre personas, no entre categorías protegidas. Y las nueve
viviendas pertenecen a la misma comunidad de retiro, así que la comparación no
representa la variabilidad de un despliegue heterogéneo.

**Menor, declarado:** 273 eventos de 1,2 millones (0,02 %) traen valores
numéricos en sensores que comparten el nombre de una habitación. Se cuentan
como eventos de esa zona.

## D52 — Resultados del piloto multi-hogar
Nueve viviendas, 1.226.316 eventos, 40.866 ventanas, 7.561 inferencias de
prueba. La corrida completa tarda 9 min 44 s.

**Veredicto: NO CUMPLE**, con evidencia completa: nueve de nueve
requerimientos cubiertos, bitácora válida con cobertura 1 a 1, hash del
protocolo verificado en el paso 6 y catorce artefactos sellados en el
manifiesto. El sistema auditado no cumple; el marco sí produjo el expediente.

**Equidad: no aprueba.** De 108 combinaciones evaluables, 29 exceden su
umbral: 14 entre hogares, 12 entre franjas horarias y 3 entre tipos de día.
Las mayores disparidades entre personas son `Work` (0,872), `Eat` (0,810),
`Cook` (0,503), `Wash_Dishes` (0,447) y `Sleep` (0,425).

**Es la primera vez que el R4.1 se evalúa como lo pide su enunciado.** Hasta
este piloto los subgrupos eran contextuales (D23); ahora cada hogar es una
persona distinta, así que la comparación es entre la población monitoreada.

**Diagnóstico de `Cook`, la disparidad más ilustrativa.** `hh107` tiene el
máximo de ejemplos de entrenamiento (943) y la **peor** tasa de aciertos
(0,292); `hh103` tiene 414 y la mejor (0,795). No es escasez de datos. `hh107`
es la única vivienda con dos residentes del piloto, y cuando falla predice
`Wash_Dishes` 83 veces: consistente con dos personas en la cocina haciendo
cosas distintas. Queda como hipótesis respaldada, no como conclusión: el mismo
`hh107` tiene el **mejor** desempeño en `Sleep` (0,867), así que el patrón
depende de la actividad.

**Advertencia que el reporte debe llevar.** El desempeño global es bajo:
exactitud entre 0,22 y 0,43 por vivienda y F1 macro entre 0,16 y 0,35, contra
0,70 de exactitud en Aruba. Es esperable —25 clases en vez de 11 y un solo
modelo para nueve casas con plantas distintas— pero un modelo más débil tiene
más lugar donde mostrar disparidad, y eso matiza la lectura de los 29
incumplimientos. **El protocolo no se cambia para mejorar ese número**: sería
ajustar después de ver resultados.

## D53 — Los términos se verificaron contra la ENIA, no contra la paráfrasis
Se contrastó lo que el marco afirma con el documento oficial (MICITT, 2024,
versión 1.0 del 24 de octubre de 2024). La numeración y la selección de
principios eran correctas: 3 Transparencia y explicabilidad (p. 32), 4 Equidad
y no discriminación (pp. 32-33), 5 Responsabilidad (p. 33). Tres cosas no lo
eran.

**El nombre del principio 5.** Se llamaba "Principio de rendición de cuentas y
trazabilidad" en `articulacion_normativa`, y la ENIA lo llama
**Responsabilidad**. La rendición de cuentas y la trazabilidad son contenidos
suyos, no su nombre. El texto salía impreso en el model card y en el reporte
de cumplimiento.

**Una página mal citada.** La ficha atribuía el derecho a entender e impugnar
decisiones a las pp. 31-32; está en la p. 32. La p. 31 es supervisión humana,
otro principio y fuera de alcance.

**Una paráfrasis que endurecía la fuente.** Se decía "la edad como diferencia
protegida". La ENIA enumera la edad entre las diferencias que deben respetarse
para asegurar accesibilidad; no usa la categoría jurídica de atributo
protegido.

**Alcance declarado en el expediente.** El marco cubre 3 de los 7 principios
rectores, y dentro de esos tres la cobertura es parcial. El reporte de
cumplimiento ahora lo dice: no cubre el derecho a saber que se trata con una
IA ni la prerrogativa de no ser afectado (principio 3); detecta el sesgo pero
no lo corrige, ni cubre accesibilidad ni adaptación cultural y lingüística
(principio 4); y la supervisión humana efectiva es el principio 2, fuera de
alcance. Un expediente que solo muestre lo que cubre induce a error sobre lo
que no.

**Qué entiende la ENIA por equidad.** Cuatro cosas: no discriminación
algorítmica, accesibilidad e inclusión respetando diferencias de edad, etnia,
género, religión, capacidad económica y nivel formativo, minimización de
sesgos con auditorías continuas que identifiquen **y corrijan**, y
oportunidades de formación para grupos subrepresentados. El marco cubre la
primera y la mitad de la tercera.

**Ninguno de los subgrupos evaluados corresponde a las categorías que la ENIA
nombra**, y no es consecuencia de haber elegido Aruba. Se verificó sobre el
catálogo completo del depósito oficial: los 82 hogares anotados pertenecen a
las series hh, tm, mn, rw, ihs, mva y mv, **todas de personas adultas
mayores**; los conjuntos de familias y de adultos jóvenes existen solo sin
anotar, sin variable objetivo. Ningún hogar publica edad, sexo ni condición de
salud. La limitación es estructural del dominio, tal como anticipaba el
Capítulo 5 de la tesis; el piloto ahora lo demuestra en vez de suponerlo.

Un matiz a favor que conviene escribir: la edad no es variable de comparación
porque es constante. El sistema opera enteramente sobre el grupo que la ENIA
señala como prioritario, así que la exigencia se satisface en el diseño y en
la documentación, no en una comparación entre edades que sería imposible.

**Revisar:** la ENIA exige sistemas cultural y lingüísticamente apropiados
(p. 32), y las explicaciones del piloto nombran las zonas en inglés
(`Movimiento en LoungeChair`). D39 lo anotaba como limitación cosmética: es un
incumplimiento de equidad, y se corrige con un mapeo de nombres para mostrar.

## D54 — Los nombres de zona se muestran en el idioma de las personas
Las explicaciones decían "Movimiento en LoungeChair" y "9 activaciones de
movimiento en Kitchen". D39 lo anotó como limitación cosmética. No lo era: la
ENIA exige sistemas cultural y lingüísticamente apropiados (MICITT, 2024,
p. 32) y el R3.3 exige información comprensible para destinatarios no
técnicos. Para una cuidadora hispanohablante, "LoungeChair" no es información.

`datos.nombres_zona` traduce cada zona al idioma de las personas
destinatarias. Ahora el enunciado dice "9 activaciones de movimiento en la
cocina" y "1 activación de movimiento en el dormitorio".

**Es traducción de presentación, no de datos.** Las columnas, los
identificadores y los nombres técnicos no cambian, y el reporte de
explicabilidad sigue mostrando el nombre técnico en su propia columna: un
auditor puede ir de la frase a la característica sin ambigüedad.

**Una zona sin traducción muestra su identificador.** Es preferible a ocultar
que falta: se ve en el reporte y se corrige.

**Traducir una zona inexistente es un error de configuración.** Un nombre mal
escrito pasaría desapercibido —el reporte seguiría mostrando el identificador—
y el cargador lo rechaza con la lista de zonas declaradas.

**Lo que esto no arregla.** El resto de la adaptación cultural y lingüística
que pide la ENIA sigue fuera de alcance: los nombres de actividad
(`Meal_Preparation`, `Bed_Toilet_Transition`) vienen del dataset y se muestran
tal cual. Traducirlos exigiría un mapeo de etiquetas y afectaría a las tablas
de equidad, donde el nombre técnico es la clave de comparación. Queda
declarado.
