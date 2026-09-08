# Datasheet — Dataset CASAS (eventos de sensores PIR)

> Basada en "Datasheets for Datasets" (Gebru et al.). Los marcadores `{{...}}`
> se rellenan en el paso 6; las secciones sin marcador se completan a mano una
> sola vez y se versionan.

## Motivación
- **¿Para qué se creó el dataset?** {{motivacion}}
- **¿Quién lo creó?** WSU CASAS smart home project — http://casas.wsu.edu/

## Composición
- **¿Qué representa cada instancia?** un evento de sensor con marca temporal.
- **Nº de instancias (crudo):** {{n_instancias_crudo}}
- **Nº de instancias (tras características):** {{n_instancias_procesado}}
- **Columnas de sensores PIR:** {{columnas_sensor_pir}}
- **Etiqueta:** {{columna_objetivo}} — clases: {{clases}}
- **Distribución de clases:** {{distribucion_clases}}
- **Datos personales:** {{datos_personales}} (monitoreo domiciliario: tratar
  como sensible aunque esté anonimizado).

## Proceso de recolección
- **Mecanismo:** sensores instalados en viviendas de prueba.
- **Ventana temporal:** {{ventana_temporal}}
- **Consentimiento:** {{consentimiento}}

## Preprocesamiento / limpieza
- **Transformaciones aplicadas:** {{transformaciones}}
- **Derivación de subgrupos de equidad:** {{derivacion_subgrupos}}
- **Hash de datos crudos:** {{hash_datos_crudos}}
- **Hash de datos procesados:** {{hash_datos_procesados}}

## Usos
- **Uso en este proyecto:** entrenamiento y evaluación del clasificador de
  actividad para el marco de cumplimiento.
- **Usos no recomendados:** {{usos_no_recomendados}}

## Distribución y mantenimiento
- **Licencia / términos:** {{licencia}}
- **Cómo obtener el crudo:** {{instrucciones_descarga}}
  (colocar en `datos/crudos/`, nunca versionar).
