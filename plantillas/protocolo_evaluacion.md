# Protocolo de evaluación declarado — ejecución {{id_ejecucion}}

> Producto del **paso 3** del procedimiento (Tabla 9).
> Función NIST AI RMF: **MAPEAR**.
> Requerimiento **R4.2**: las disparidades deben medirse con métricas
> definidas y **umbrales declarados previamente**.

## Sellado del protocolo

| Campo | Valor |
|---|---|
| Declarado en | {{marca_temporal}} |
| Hash SHA-256 de `config.yaml` | `{{hash_protocolo}}` |
| Commit de git | `{{commit_git}}` |

> **Control metodológico.** Este hash se calcula **antes** de ejecutar las
> pruebas del paso 4 y se vuelve a comprobar en el paso 6. Si difiere, los
> criterios se alteraron después de observar resultados y la evidencia de
> equidad queda marcada como no válida. Sin esta comprobación, la afirmación
> "los umbrales no se ajustaron a los resultados" no es verificable por un
> auditor externo: es una declaración de buena fe.

## Subgrupos de comparación
{{tabla_subgrupos}}

Justificación de la selección:
{{justificacion_subgrupos}}

## Métricas de equidad y umbrales

{{tabla_umbrales}}

Justificación de cada umbral:
{{justificacion_umbrales}}

## Limitaciones declaradas de la evaluación
{{limitaciones}}

## Métricas de desempeño (no de equidad)
{{metricas_desempeno}}
