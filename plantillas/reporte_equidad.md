# Reporte de equidad (Principio 2) — ejecución {{id_ejecucion}}

> Requerimientos que documenta: **R4.1** (desempeño desagregado entre
> subgrupos) y **R4.2** (disparidades medidas con métricas definidas y
> umbrales declarados antes de la ejecución).

## Veredicto

**{{veredicto}}**

{{resumen_veredicto}}

### Combinaciones que incumplen su umbral

{{tabla_incumplidas}}

## Protocolo declarado

> Tomado del bloque `equidad` del archivo de configuración. Se fija **antes** de
> ejecutar las pruebas y el paso 3 lo sella por hash: cualquier cambio queda
> trazado en git con su justificación.

{{tabla_protocolo}}

- **Evaluación multiclase:** cada actividad se evalúa contra el resto.
- **Soporte mínimo:** {{soporte_minimo}} casos en el denominador de cada
  tasa. Una categoría por debajo queda fuera de la comparación; con menos de
  dos categorías, la combinación es no evaluable.

## Subgrupos evaluados

{{lista_subgrupos}}

## Desempeño desagregado (R4.1)

{{tabla_desempeno_desagregado}}

## Métricas que deciden el veredicto (R4.2)

> Entre paréntesis, el denominador de cada tasa; «fuera» indica que no llega
> al soporte mínimo y no entra en la comparación. TVP: tasa de verdaderos
> positivos. TFP: tasa de falsos positivos.

{{tabla_metricas_veredicto}}

### No evaluables

{{tabla_no_evaluables}}

## Métricas descriptivas

> Se calculan y se reportan, pero no deciden el veredicto.

{{tabla_descriptivas}}

## Notas de interpretación

{{notas_interpretacion}}

## Limitaciones declaradas

{{limitaciones}}
