# Alineamiento con CRISP-ML(Q)

CRISP-ML(Q) es el modelo de proceso de referencia para el ciclo de vida de
aplicaciones de aprendizaje automático con aseguramiento de calidad (Studer
et al., 2021). Este documento sitúa el marco frente a él: qué coincide, qué
añade el marco, en qué diverge a propósito y qué queda fuera.

No es una adhesión. Es una declaración de posición, que es lo que el marco
pide de cualquier sistema que evalúa.

## La relación entre los dos procesos

**CRISP-ML(Q) es un proceso de desarrollo**: guía a quien construye el modelo,
desde entender el negocio hasta mantener el sistema en producción. Su
destinatario es el equipo de desarrollo y su producto es un sistema que
funciona.

**Este marco es un proceso de evaluación de cumplimiento**: se aplica a un
sistema ya construido y su producto es un expediente de evidencia para un
tercero —auditor, regulador, comité de ética—. El modelo no es lo que se
mejora; es lo que se examina (Tabla 10).

No compiten, y la diferencia explica la forma del marco. Las dos
precondiciones —preparar datos, sellar el modelo— comprimen las fases 2 y 3 de
CRISP-ML(Q) en *insumos*: no son pasos del procedimiento porque no son
actividad de cumplimiento, son el sujeto sobre el que el cumplimiento se
comprueba. Los seis pasos de la Tabla 9 se reparten entre las fases 1 y 4.

Las fases 5 y 6 quedan fuera de alcance.

Sobre los nombres: el preprint y la versión publicada rotulan las fases
distinto. Aquí se usan los nombres del preprint —*Business & Data
Understanding, Data Preparation, Modeling, Evaluation, Deployment, Monitoring
& Maintenance*— y se anota entre paréntesis el rótulo de la versión de MAKE
cuando difiere.

## Fase por fase

| Fase CRISP-ML(Q) | Tarea | Correspondencia en el marco |
|---|---|---|
| **1. Business & Data Understanding** (*Business and Data Understanding*) | *Define the Scope of the ML Application* | **Paso 1**, ficha de caracterización: sistema, finalidad, población destinataria y configuración de sensores |
| | *Success Criteria* (negocio / ML / económico) | Divergencia declarada, ver abajo |
| | *Data Collection* — versionado y procedencia | **Precondición A**: doble sello, `hash_datos_crudos` (el crudo como se leyó) y `hash_datos` (el cuadro de características). **Paso 2**: los nueve campos de `datos.documentacion` |
| | *Data Quality Verification* | **Precondición A**: `validar_esquema` contra el contrato de ingesta y `_verificar_contrato` sobre el orden por hogar |
| | *Feasibility* — incluye restricciones legales, explicabilidad, robustez | Parcial. La revisión normativa vive en la tesis (articulación con AI Act y NIST AI RMF), no en el código. El marco **asciende** explicabilidad y restricción legal de casilla de viabilidad a requerimiento medido |
| **2. Data Preparation** (*Data Engineering*) | *Select Data*, *Clean Data*, *Construct Data*, *Standardize Data* | **Precondición A**: `construir_caracteristicas`, `particionar`, y en configuración `actividades.mapeo`, `excluidas` y `etiqueta_sin_actividad` |
| | QA: documentar las decisiones de filtrado y evaluar su impacto | El datasheet del paso 2 las registra; `docs/decisiones.md` guarda el porqué |
| | QA: mismos parámetros de normalización en entrenamiento y prueba | La partición es temporal y posterior a la construcción de características; en el piloto multi-hogar, temporal dentro de cada vivienda |
| | QA: comparar características contra una línea base, quitar las poco usadas | **No se hace después del paso 3**, ver divergencia 2 |
| **3. Modeling** (*Machine Learning Model Engineering*) | *Define quality measures of the model* — seis propiedades | Desempeño ✓ · explicabilidad ✓ · complejidad ✓ (hiperparámetros declarados) · demanda de recursos parcial · escalabilidad parcial · **robustez ✗** (hueco declarado) |
| | *Model Selection* | No aplica: el modelo viene dado. Ver divergencia 3 |
| | *Assure reproducibility* — método | **Precondición B** y model card: semilla declarada, `PYTHONHASHSEED` fijo, `requirements.lock`, hash de parámetros, hash de datos de entrenamiento, versión del estimador |
| | *Assure reproducibility* — resultado (media y varianza sobre varias semillas) | **✗** Semilla única, sellada. Hueco declarado |
| **4. Evaluation** (*Quality Assurance for ML Applications*) | *Validate performance* — conjunto de prueba reservado | **Paso 4**: la prueba no se toca hasta ese punto |
| | *sliced performance analysis* | **Módulo de equidad** (R4.1): desempeño desagregado por subgrupo, con soporte mínimo de 30 en el denominador de cada tasa |
| | *Determine robustness* — entradas ruidosas o falsificadas | **✗** Hueco declarado |
| | *Increase explainability for ML practitioner & end user* | **Módulo de explicabilidad**: atribución local (R3.1) y agregación global (R3.2) para el practicante; enunciados en lenguaje llano y nombres de zona traducidos (R3.3) para la persona destinataria |
| | *Compare results with defined success criteria* | **Paso 6**: reporte de cumplimiento, cobertura de los nueve requerimientos y veredicto de equidad contra umbrales sellados en el paso 3 |
| **5. Deployment** | Cinco tareas | Fuera de alcance. Parcial: el model card cubre en parte *provide user guides and disclaimers* |
| **6. Monitoring & Maintenance** | *Monitor*, *Update* | Fuera de alcance, pero ver abajo: el marco deja construido el insumo |

## Lo que el marco aporta sobre CRISP-ML(Q)

Tres cosas que CRISP-ML(Q) menciona sin operacionalizar:

**Equidad medida, no considerada.** El paper nombra la equidad una vez, entre
las propiedades a tener en cuenta al definir medidas de calidad, y propone el
*sliced performance analysis* como práctica de inspección. El marco la
convierte en un procedimiento con métricas nombradas, subgrupos justificados,
umbrales numéricos y un veredicto de tres estados, donde *no evaluable* no
cuenta como aprobado.

**Umbrales declarados antes de medir.** CRISP-ML(Q) pide comparar resultados
contra criterios de éxito definidos en la fase 1, pero no fija ningún
mecanismo que impida ajustarlos después. El paso 3 sella el hash del archivo
de configuración y el paso 6 lo vuelve a comprobar: si los criterios cambiaron
tras ver resultados, la evidencia queda marcada como no válida. Es la
diferencia entre una recomendación metodológica y un control verificable por
un tercero.

**Evidencia, no documentación.** La fase 1 termina en *Review of Output
Documents*. El marco produce catorce artefactos con hash en un manifiesto,
una bitácora de ejecución append-only y una matriz de cobertura que dice cuál
de los nueve requerimientos sostiene cada artefacto. Un auditor puede
reproducir el sello del protocolo con `sha256sum config.yaml`, sin ejecutar
nada del marco.

## Divergencias declaradas

**1. No hay criterio de éxito de nivel ML.** CRISP-ML(Q) pide tres niveles:
negocio, ML y económico. El marco tiene el de negocio —la corrida produce un
expediente que permite reconstruir el comportamiento del sistema (Tabla 10)— y
**deliberadamente no tiene el de ML**. Fijar un umbral de exactitud
convertiría al modelo en objeto de optimización, que es exactamente lo que la
Tabla 10 excluye: un marco de cumplimiento que premiara el desempeño
incentivaría a ajustar el sistema para aprobar la auditoría. El nivel
económico no aplica. Quien venga de CRISP-ML(Q) va a buscar ese umbral en el
paso 1; no está, y su ausencia es la decisión.

**2. La iteración sobre características se congela en el paso 3.** CRISP-ML(Q)
propone comparar características contra líneas base y retirar las poco usadas,
apoyándose en métodos de explicación. El marco no lo prohíbe: lo ubica
**antes** de la precondición A. Una vez que el paso 3 sella la configuración,
cambiar las características es cambiar el protocolo después de ver resultados,
y el paso 6 lo detecta. La tensión es real y la resolución es temporal, no de
principio.

**3. El modelo no se selecciona.** *Start with a baseline, gradually increase
capacity* es consejo para quien construye. Aquí el modelo llega dado y su
desempeño no se optimiza en función de las pruebas posteriores. Que los
números del piloto sean modestos es coherente con eso, no un defecto a
corregir.

## Huecos declarados

**Robustez.** CRISP-ML(Q) la nombra dos veces: entre las seis propiedades de
calidad de la fase 3 y como tarea propia de la fase 4 (*Determine robustness*,
con entradas ruidosas o falsificadas). El marco no la mide, y ninguno de los
tres principios de la ENIA que operacionaliza la exige.

Dónde sí aparece: el AI Act la trata en su artículo 15 —exactitud, robustez y
ciberseguridad—, que **no** está en la articulación normativa del marco. Esta
declara los artículos 13 (transparencia), 10 (gobernanza de datos y sesgos) y
12 (conservación de registros), uno por principio. El artículo 15 queda fuera
por la misma razón que el resto: el marco cubre tres principios de la ENIA, no
el AI Act completo.

Así que el hueco es de alcance, no de omisión, pero sigue abierto: es el
candidato más claro a una extensión del procedimiento, y un tribunal formado
en CRISP-ML(Q) va a preguntarlo.

**Reproducibilidad de resultado.** El paper distingue entre reproducibilidad
de *método* —documentar semilla, versiones, hiperparámetros, hardware— y de
*resultado*: validar la media y estimar la varianza sobre varias semillas, en
vez de reportar una corrida. El marco cubre la primera y no la segunda: fija
una semilla y la sella. Medir la varianza exigiría varias corridas del modelo,
lo que no rompe el protocolo —los umbrales siguen sellados— pero sí obliga a
decidir qué corrida entra al expediente. Queda pendiente.

## Fases 5 y 6: fuera de alcance, con una salvedad

El marco no cubre despliegue ni monitoreo. No hay estrategia de despliegue
incremental, plan de reversión, *safety cage* ni prueba de aceptación con
personas usuarias; tampoco detección de deriva ni reentrenamiento.

La salvedad vale la pena: **la fase 6 consume lo que el marco produce**.
CRISP-ML(Q) propone monitorear comparando estadísticas de los datos entrantes
y de las etiquetas predichas contra las del entrenamiento, y usar la
validación de esquema de la fase 1 para tratar las entradas no conformes como
anomalías. El registro estructurado de inferencias del R5.1 —una entrada por
decisión, con hash de la fila de entrada, predicción, confianza y referencia a
su explicación local— y el contrato de ingesta validado en la precondición A
son precisamente ese insumo. El marco no monitorea, pero deja instalado lo que
hace falta para monitorear.

## Referencia

Studer, S., Bui, T. B., Drescher, C., Hanuschkin, A., Ludwig, L.,
Lauber-Rönsberg, A., & Klöpper, B. (2021). Towards CRISP-ML(Q): A Machine
Learning Process Model with Quality Assurance Methodology. *Machine Learning
and Knowledge Extraction*, 3(2), 392–413.
https://doi.org/10.3390/make3020020
