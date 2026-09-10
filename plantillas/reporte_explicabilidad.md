# Reporte de explicabilidad (Principio 1) — ejecución {{id_ejecucion}}

> Requerimientos que documenta: **R3.1** (explicación local de cada
> predicción), **R3.2** (importancia global) y **R3.3** (enunciados en
> lenguaje llano para destinatarios no técnicos).

- **Método:** {{explainer}} (SHAP {{version_shap}}), perturbación `{{perturbacion}}`
- **Inferencias explicadas:** {{n_explicaciones}} — todas las del conjunto de evaluación
- **Puntos por gráfico de dependencia:** {{muestras_graficos}} (muestra determinista)
- **Semilla:** {{semilla}}

## Importancia global de características

Media de |contribución| a la probabilidad de la clase predicha, sobre todas
las explicaciones locales (R3.2). La tabla es el equivalente accesible de la
figura.

![Importancia global]({{ruta_figura_resumen}})

{{tabla_importancia_global}}

## Gráficos de dependencia (características destacadas)

{{figuras_dependencia}}

## Ejemplos de atribución local

> Selección determinista con la semilla: {{ejemplos_por_tipo}} aciertos y
> {{ejemplos_por_tipo}} errores del conjunto de evaluación.

{{ejemplos_locales}}

## Notas de interpretación

{{notas_interpretacion}}
