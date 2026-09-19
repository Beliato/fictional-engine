Marco operativo de cumplimiento para sistemas de inteligencia artificial basados en sensores PIR

Operational compliance framework for artificial intelligence systems based on PIR sensors

Nombre completo de autor 1
Afiliacion institucional. Pais
Correo electronico
ORCID

Nombre completo de autor 2
Afiliacion institucional. Pais
Correo electronico
ORCID

Nombre completo de autor 3
Afiliacion institucional. Pais
Correo electronico
ORCID

Resumen

Los sistemas de inteligencia artificial aplicados al monitoreo domiciliario de personas adultas mayores prometen apoyar la permanencia segura en el hogar, pero tambien generan exigencias de transparencia, equidad y responsabilidad. En Costa Rica, la Estrategia Nacional de Inteligencia Artificial establece estos principios sin especificar mecanismos tecnicos para verificarlos en sistemas concretos. Este articulo presenta y evalua un marco operativo de cumplimiento para sistemas de clasificacion de actividades basados en sensores de infrarrojo pasivo y otros sensores ambientales. La metodologia consistio en traducir tres principios de la estrategia nacional en nueve requerimientos operativos, articularlos con el AI Act de la Union Europea y el NIST AI Risk Management Framework, e implementarlos como un procedimiento reproducible de seis pasos. El marco integra explicabilidad local y global mediante SHAP, evaluacion de equidad por subgrupos con umbrales declarados previamente, registro estructurado de inferencias y generacion de artefactos auditables. La aplicacion piloto sobre dos configuraciones del conjunto CASAS produjo expedientes completos: Aruba, con 11 175 inferencias, y una serie multi-hogar, con 7561 inferencias. En ambos casos se cubrieron los nueve requerimientos y se obtuvo un veredicto de no cumplimiento del sistema evaluado. Los resultados muestran que el marco permite transformar principios normativos en evidencia tecnica verificable y reproducible.

Palabras clave

Inteligencia artificial; sensores; aprendizaje automatico; explicabilidad; equidad; trazabilidad; auditoria

Abstract

Artificial intelligence systems applied to home monitoring of older adults may support safe aging in place, but they also create requirements for transparency, fairness, and accountability. In Costa Rica, the National Artificial Intelligence Strategy establishes these principles without specifying technical mechanisms to verify them in concrete systems. This article presents and evaluates an operational compliance framework for activity classification systems based on passive infrared sensors and other environmental sensors. The methodology translated three principles of the national strategy into nine operational requirements, aligned them with the European Union AI Act and the NIST AI Risk Management Framework, and implemented them as a reproducible six-step procedure. The framework integrates local and global explainability through SHAP, subgroup fairness evaluation with thresholds declared in advance, structured inference logging, and generation of auditable artifacts. The pilot application on two CASAS dataset configurations produced complete evidence files: Aruba, with 11,175 inferences, and a multi-home series, with 7,561 inferences. In both cases, all nine requirements were covered and the evaluated system received a non-compliance verdict. The results show that the framework can transform normative principles into verifiable and reproducible technical evidence.

Keywords

Artificial intelligence; sensors; machine learning; explainability; fairness; traceability; audit

Introduccion

Los sensores ambientales instalados en viviendas han sido utilizados para reconocer actividades de la vida diaria sin recurrir a camaras ni microfonos. En particular, los sensores de infrarrojo pasivo, junto con sensores magneticos de puerta y sensores de temperatura, permiten registrar patrones de movimiento compatibles con tareas como dormir, cocinar, comer o desplazarse dentro del hogar. Esta clase de sistemas resulta relevante para el monitoreo no intrusivo de personas adultas mayores, pues puede aportar informacion de apoyo a cuidadores y servicios de acompanamiento [1]. Sin embargo, cuando las inferencias automatizadas se usan sobre poblaciones vulnerables, el desempeno tecnico del clasificador no es suficiente para justificar su uso.

La Estrategia Nacional de Inteligencia Artificial de Costa Rica plantea principios rectores para el desarrollo y uso responsable de sistemas de IA, entre ellos transparencia y explicabilidad, equidad y no discriminacion, y responsabilidad [2]. Estos principios son coherentes con instrumentos internacionales como el Reglamento Europeo de Inteligencia Artificial, que establece obligaciones de transparencia, gobernanza de datos y conservacion de registros para sistemas de alto riesgo [3], y con el NIST AI Risk Management Framework, que organiza la gestion de riesgos en funciones de mapear, medir, gobernar y gestionar [4]. No obstante, estos marcos suelen expresarse en un nivel normativo o metodologico que no siempre indica como producir evidencia tecnica verificable sobre un sistema especifico.

El problema abordado en este estudio es la brecha entre principios regulatorios de alto nivel y mecanismos computacionales reproducibles para auditarlos en sistemas de IA basados en sensores domiciliarios. En este dominio, la brecha es particularmente relevante porque los datos describen rutinas domesticas sensibles, los metadatos demograficos disponibles son limitados y los errores pueden afectar de forma desigual a personas con patrones de movilidad o rutina menos representados.

El objetivo de la investigacion fue disenar, implementar y verificar un marco operativo que traduzca tres principios de la Estrategia Nacional de IA de Costa Rica en requerimientos tecnicos, pruebas computacionales y artefactos auditables aplicables a un clasificador de actividades basado en sensores PIR. El articulo resume la arquitectura del marco, la metodologia de implementacion y los resultados obtenidos en dos aplicaciones piloto sobre datos publicos del proyecto CASAS.

Materiales y metodos

Tipo de investigacion y enfoque

La investigacion fue de tipo aplicada y de diseno tecnologico. El objeto evaluado no fue la optimizacion predictiva del modelo, sino la capacidad del marco para generar evidencia verificable de cumplimiento. Por ello, el modelo de aprendizaje automatico se trato como sujeto de prueba: se entreno y sello antes de ejecutar el procedimiento de cumplimiento, y no se ajusto posteriormente con base en los resultados de equidad o explicabilidad.

La metodologia se organizo en cuatro componentes. El primero fue una matriz de mapeo principio-requerimiento. El segundo correspondio a tres modulos de cumplimiento: explicabilidad, equidad y trazabilidad. El tercero fue un registro estructurado de inferencias. El cuarto fue un procedimiento reproducible de seis pasos para generar el expediente de evidencia.

Datos y poblacion de estudio

Se utilizaron datos publicos del proyecto CASAS, compuesto por eventos de sensores ambientales en entornos domiciliarios [1]. La primera configuracion corresponde al hogar Aruba, con una vivienda, sensores PIR, sensores de puerta, sensores de temperatura y actividades anotadas. La segunda corresponde a una serie multi-hogar, compuesta por nueve viviendas de personas adultas mayores de una comunidad de retiro. En ambos casos, la poblacion observada corresponde a personas adultas mayores en viviendas independientes, aunque el proyecto no recolecto datos nuevos ni tuvo contacto con participantes humanos.

Los eventos se transformaron en ventanas disjuntas de 30 eventos consecutivos. Cada ventana genero una fila tabular con conteos por zona del hogar, eventos de puerta, variables temporales y, cuando estaban disponibles, lecturas de temperatura. La particion de entrenamiento y prueba fue temporal por dia, con una proporcion de prueba de 0,2. Esta decision evito mezclar ventanas contiguas de una misma secuencia entre entrenamiento y prueba.

Modelo de referencia

El modelo de referencia fue un clasificador RandomForestClassifier con semilla fija, ejecucion de un solo hilo y versiones de bibliotecas declaradas. Su funcion fue proporcionar inferencias para auditar el marco. La calidad predictiva del modelo no se uso como criterio de exito del estudio, pues el proposito fue comprobar si el procedimiento producia evidencia completa y reconstruible.

Matriz de requerimientos

La matriz tradujo los principios seleccionados en nueve requerimientos operativos. El Cuadro 1 resume la correspondencia entre principio, requerimiento y evidencia esperada.

Cuadro 1. Requerimientos operativos y evidencia del marco.

| Principio | Codigo | Evidencia tecnica y documental |
|---|---|---|
| Transparencia y explicabilidad | R3.1 | Explicacion local por inferencia mediante atribucion cuantificada de variables. |
| Transparencia y explicabilidad | R3.2 | Importancia global agregada sobre el conjunto de evaluacion. |
| Transparencia y explicabilidad | R3.3 | Traduccion de resultados a lenguaje comprensible y model card. |
| Equidad y no discriminacion | R4.1 | Desempeno desagregado por subgrupo. |
| Equidad y no discriminacion | R4.2 | Metricas de disparidad con umbrales declarados antes de medir. |
| Equidad y no discriminacion | R4.3 | Datasheet del conjunto de datos con procedencia, composicion y limitaciones. |
| Responsabilidad | R5.1 | Bitacora estructurada y persistente de inferencias. |
| Responsabilidad | R5.2 | Model card con proposito, desempeno, limitaciones y condiciones de uso. |
| Responsabilidad | R5.3 | Verificacion de reconstruccion y atribucion ex post de decisiones. |

Fuente: elaboracion propia.

Modulo de explicabilidad

El modulo de explicabilidad utilizo SHAP con TreeExplainer para calcular atribuciones locales de las variables de entrada [5], [6]. Para cada inferencia del conjunto de prueba se registro la clase predicha, el valor base, las contribuciones de las variables y una referencia al artefacto de explicacion. La importancia global se obtuvo como la media de las contribuciones absolutas locales, evitando un segundo calculo independiente y manteniendo coherencia entre explicaciones locales y globales. Las variables se nombraron por zonas del hogar, por ejemplo cocina o dormitorio, para favorecer la comprension por parte de destinatarios no tecnicos.

Modulo de equidad

El modulo de equidad evaluo desempeno desagregado y disparidad entre subgrupos. En Aruba, los subgrupos fueron contextuales, como franja horaria y tipo de dia. En la configuracion multi-hogar, se incorporo el hogar como subgrupo poblacional, pues cada vivienda representa una persona o unidad domestica distinta. Las metricas con efecto en el veredicto fueron diferencia de tasa de verdaderos positivos y diferencia de tasa de falsos positivos, ambas con umbral de 0,10 declarado antes de la ejecucion. Tambien se reportaron como descriptivas la diferencia de paridad demografica y el cociente de tasa de seleccion.

Modulo de trazabilidad

La trazabilidad se implemento mediante una bitacora JSONL append-only. Cada linea registro identificador de evento, marca temporal UTC, hash de la entrada procesada, salida del modelo, confianza, version del modelo, version del marco, referencia a la explicacion local, responsable declarado y version del esquema. El uso de hashes evito persistir datos crudos sensibles en la bitacora, sin impedir la reconstruccion tecnica de la decision dentro del expediente.

Procedimiento de aplicacion

El procedimiento siguio seis pasos alineados con las funciones del NIST AI RMF: caracterizacion del sistema, documentacion del conjunto de datos, declaracion de criterios de evaluacion, ejecucion de pruebas tecnicas, generacion de artefactos auditables y verificacion de auditabilidad. El paso de declaracion de criterios sello el hash SHA-256 del archivo de configuracion. En la verificacion final, el marco comprobo que ese hash no hubiera cambiado, que la bitacora fuera valida, que existiera cobertura uno a uno entre inferencias esperadas y registradas, y que los nueve requerimientos contaran con artefactos presentes.

Resultados

El marco fue ejecutado sobre dos configuraciones piloto. El Cuadro 2 sintetiza los resultados generales del expediente.

Cuadro 2. Resultados generales de las aplicaciones piloto.

| Piloto | Configuracion | Viviendas | Inferencias registradas | Requerimientos cubiertos | Veredicto del sistema evaluado |
|---|---|---:|---:|---:|---|
| CASAS Aruba | config.yaml | 1 | 11 175 | 9 de 9 | No cumple |
| CASAS serie hh | config.hogares.yaml | 9 | 7561 | 9 de 9 | No cumple |

Fuente: elaboracion propia con base en la ejecucion documentada del repositorio.

Los dos expedientes generaron la totalidad de los artefactos previstos: ficha de caracterizacion, datasheet, protocolo de evaluacion, explicaciones locales, importancia global, resultados de desempeno desagregado, metricas de equidad, bitacora de inferencias, reporte de explicabilidad, reporte de equidad, model card, reporte de cumplimiento, bitacora de ejecucion y manifiesto de hashes. En ambos pilotos, los nueve requerimientos de la matriz quedaron respaldados por evidencia presente y verificable.

El resultado de no cumplimiento no indica un fallo del marco, sino un hallazgo sobre el sistema evaluado. El procedimiento completo se ejecuto y produjo evidencia suficiente para sostener el veredicto. Esto es consistente con el criterio de exito definido para el piloto: el marco debia demostrar que podia generar un expediente de evidencia, incluso cuando la evidencia revelara incumplimientos del sistema examinado.

Figura 1. Arquitectura funcional del marco operativo de cumplimiento. Fuente: elaboracion propia.

Sistema IA basado en sensores PIR -> matriz principio-requerimiento -> modulos de explicabilidad, equidad y trazabilidad -> procedimiento de seis pasos -> expediente de evidencia verificable.

En el modulo de explicabilidad, cada inferencia registrada en la bitacora quedo vinculada con una explicacion local. Esta relacion satisface simultaneamente R3.1 y R5.3, porque permite partir de una decision registrada y llegar al artefacto que explica las variables que contribuyeron a la prediccion. La agregacion de esas explicaciones permitio construir una importancia global de variables, asociada con R3.2. El uso de nombres de zonas del hogar permitio generar enunciados interpretables para cuidadores y otros destinatarios no tecnicos, en concordancia con R3.3.

En el modulo de equidad, los resultados fueron desagregados por los subgrupos declarados en la configuracion. La existencia de umbrales sellados antes de ejecutar las pruebas permitio diferenciar la medicion de disparidades de una interpretacion posterior ajustada a los resultados. Cuando una combinacion de actividad, subgrupo y metrica no tuvo soporte suficiente, el marco la marco como no evaluable en lugar de contarla como aprobada. Esta decision evito convertir ausencia de evidencia en evidencia de cumplimiento.

En el modulo de trazabilidad, la bitacora estructurada permitio verificar unicidad de identificadores, marcas temporales UTC, rango valido de confianza, version de modelo, version de esquema, responsable declarado y existencia de la explicacion referenciada. La verificacion final agrego la cobertura entre conjunto de prueba y registros producidos, de modo que una bitacora valida pero incompleta no pudiera sostener el cumplimiento.

Adicionalmente, el repositorio documento 272 pruebas automatizadas en verde. Estas pruebas cubrieron configuracion, preparacion de datos, modelado, explicabilidad, equidad, trazabilidad, procedimiento y documentacion. Aunque las pruebas no sustituyen una auditoria externa, aportan evidencia de reproducibilidad del procedimiento y reducen el riesgo de divergencia entre el diseno normativo y la implementacion computacional.

Discusion

Los resultados muestran que es posible operacionalizar principios regulatorios mediante requerimientos discretos, pruebas computacionales y artefactos auditables. La principal contribucion del marco es que no se limita a declarar alineacion con la Estrategia Nacional de IA, el AI Act o el NIST AI RMF, sino que produce evidencias verificables: hashes de configuracion, registros estructurados, reportes, model card, datasheet y matriz de cobertura.

La explicabilidad basada en SHAP resulto adecuada para un modelo de arboles y datos tabulares. Su ventaja principal fue conectar cada inferencia con atribuciones cuantificadas y, posteriormente, agregar esas atribuciones para describir el comportamiento global. No obstante, esta seleccion tambien impone una limitacion: el desempeno computacional y la validez de las explicaciones dependen de la familia de modelos y del modo de perturbacion seleccionado.

La evaluacion de equidad evidencio una restriccion importante del dominio. Los conjuntos publicos de sensores domiciliarios suelen incluir pocos metadatos demograficos, por lo que no siempre permiten comparar categorias protegidas como genero, etnia, capacidad economica o nivel formativo. El piloto multi-hogar mitigo parcialmente esta restriccion al comparar desempeno entre viviendas, pero no la elimina por completo. En consecuencia, el marco debe entenderse como una herramienta para producir evidencia disponible y declarar sus limites, no como garantia absoluta de ausencia de discriminacion.

La trazabilidad fue el componente transversal que permitio unir resultados tecnicos y responsabilidad. Sin una bitacora persistente, las explicaciones y los reportes quedarian desconectados de decisiones concretas. Con el esquema propuesto, cada decision puede reconstruirse a partir de su identificador, entrada hasheada, salida, confianza, version del modelo, explicacion y responsable declarado.

Una diferencia relevante frente a procesos generales de aseguramiento de calidad en aprendizaje automatico, como CRISP-ML(Q), es que el marco no busca optimizar el modelo ni seleccionar la mejor arquitectura [7]. Su proposito es auditar un sistema dado. Por ello, un veredicto de no cumplimiento es un resultado valido: revela que el sistema evaluado no satisface los criterios declarados, pero tambien demuestra que el procedimiento puede producir evidencia para sostener esa conclusion.

Conclusiones y recomendaciones

El marco operativo desarrollado permitio traducir tres principios de la Estrategia Nacional de IA de Costa Rica en nueve requerimientos verificables para sistemas de IA basados en sensores PIR. La implementacion demostro que esos requerimientos pueden evaluarse mediante un procedimiento reproducible de seis pasos, articulado con el AI Act de la Union Europea y el NIST AI RMF.

La aplicacion sobre dos pilotos del conjunto CASAS genero expedientes completos, con 18 736 inferencias registradas en total y cobertura de los nueve requerimientos en ambos casos. Los dos sistemas evaluados obtuvieron veredicto de no cumplimiento, lo cual confirma la utilidad del marco para producir evidencia incluso cuando el resultado es desfavorable para el sistema auditado.

El estudio aporta una forma concreta de pasar de principios normativos a evidencia tecnica. En particular, integra explicabilidad local y global, medicion de equidad con umbrales declarados previamente, trazabilidad por inferencia y documentos auditables. Esta combinacion permite que un tercero revise no solo los resultados, sino tambien el protocolo y los artefactos que los sostienen.

Como trabajo futuro, se recomienda validar los umbrales de equidad con un panel multidisciplinario, incorporar pruebas de robustez ante entradas ruidosas o degradadas, evaluar reproducibilidad de resultado sobre multiples semillas y extender la verificacion a escenarios de monitoreo continuo. Tambien se recomienda aplicar el marco a datasets con metadatos demograficos mas completos, siempre que su uso sea eticamente justificable y compatible con la proteccion de datos personales.

Agradecimientos

Se agradece al proyecto CASAS de Washington State University por la disponibilidad publica de conjuntos de datos de sensores ambientales para investigacion en reconocimiento de actividades. Esta seccion debe ajustarse antes del envio para incluir apoyos institucionales, financiamiento o contribuciones especificas, si corresponde.

Declaracion sobre el uso de inteligencia artificial

Los autores declaramos que hemos utilizado GitHub Copilot para asistir en la estructuracion inicial y redaccion preliminar de este borrador de articulo. La herramienta ayudo a organizar el texto conforme a las instrucciones editoriales y a mejorar la claridad expositiva. Los contenidos, cifras, referencias y conclusiones deben ser revisados, corregidos y validados por los autores antes de cualquier envio, quienes conservan la responsabilidad intelectual y etica sobre la version final.

Referencias

[1] D. Cook, "Learning setting-generalized activity models for smart spaces", IEEE Intelligent Systems, vol. 27, no. 1, pp. 32-38, 2012. https://doi.org/10.1109/MIS.2010.112

[2] Ministerio de Ciencia, Innovacion, Tecnologia y Telecomunicaciones, Estrategia Nacional de Inteligencia Artificial de Costa Rica 2024-2027, San Jose, Costa Rica: MICITT, 2024.

[3] European Parliament and Council, "Regulation (EU) 2024/1689 of the European Parliament and of the Council laying down harmonised rules on artificial intelligence", Official Journal of the European Union, 2024.

[4] National Institute of Standards and Technology, Artificial Intelligence Risk Management Framework (AI RMF 1.0), NIST AI 100-1, Gaithersburg, MD, USA: NIST, 2023. https://doi.org/10.6028/NIST.AI.100-1

[5] S. M. Lundberg and S.-I. Lee, "A unified approach to interpreting model predictions", in Advances in Neural Information Processing Systems 30, 2017, pp. 4765-4774.

[6] S. M. Lundberg et al., "From local explanations to global understanding with explainable AI for trees", Nature Machine Intelligence, vol. 2, pp. 56-67, 2020. https://doi.org/10.1038/s42256-019-0138-9

[7] S. Studer, T. B. Bui, C. Drescher, A. Hanuschkin, L. Ludwig, L. Lauber-Ronsberg and B. Klopper, "Towards CRISP-ML(Q): A machine learning process model with quality assurance methodology", Machine Learning and Knowledge Extraction, vol. 3, no. 2, pp. 392-413, 2021. https://doi.org/10.3390/make3020020