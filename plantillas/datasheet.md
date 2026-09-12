# Datasheet del conjunto de datos — ejecución {{id_ejecucion}}

> Producto del **paso 2** del procedimiento (Tabla 9).
> Función NIST AI RMF: **MAPEAR**. Requerimiento **R4.3**.
> Basada en "Datasheets for Datasets" (Gebru et al., 2021). Lo genera
> `evidencia.generar_datasheet` desde `config.yaml` y los datos ya
> preparados: no editar a mano.

## Fuente
{{fuente}}

## Motivación
- **¿Para qué se creó el dataset?** {{motivacion}}
- **¿Quién lo creó?** {{creador}}

## Composición
- **¿Qué representa cada instancia?** un evento de sensor con marca temporal.
- **Nº de instancias (crudo):** {{n_instancias_crudo}}
- **Nº de instancias (tras características):** {{n_instancias_procesado}}
- **Columnas de sensores PIR:** {{columnas_sensor_pir}}
- **Etiqueta:** {{columna_objetivo}} — clases: {{clases}}
- **Datos personales:** {{datos_personales}}
- **Distribución de clases:**

{{distribucion_clases}}

## Proceso de recolección
- **Mecanismo:** {{mecanismo_recoleccion}}
- **Ventana temporal:** {{ventana_temporal}}
- **Consentimiento:** {{consentimiento}}

## Preprocesamiento / limpieza
- **Transformaciones aplicadas:**

{{transformaciones}}

- **Derivación de subgrupos de equidad:**

{{derivacion_subgrupos}}

- **Hash de datos crudos:** {{hash_datos_crudos}}
- **Hash de datos procesados:** {{hash_datos_procesados}}

## Usos
- **Uso en este proyecto:** {{uso_en_proyecto}}
- **Usos no recomendados:** {{usos_no_recomendados}}

## Distribución y mantenimiento
- **Licencia / términos:** {{licencia}}
- **Cómo obtener el crudo:** {{instrucciones_descarga}}
