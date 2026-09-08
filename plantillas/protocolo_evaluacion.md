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

> Declarar aquí qué atributos se consideran relevantes y éticamente
> defendibles para el análisis desagregado en este dominio, y cuáles se
> derivan de otros (p. ej. franja horaria a partir de la marca temporal).

## Métricas de equidad y umbrales

{{tabla_umbrales}}

Justificación de cada umbral:
{{justificacion_umbrales}}

> Cada valor debe sostenerse en literatura o marco legal, no en conveniencia.
> La regla del 80 % para el cociente de tasas de selección tiene origen
> normativo; las diferencias absolutas requieren argumento propio.

## Limitaciones declaradas de la evaluación
{{limitaciones}}

> Documentar aquí la restricción de granularidad por falta de metadatos
> demográficos en los conjuntos de datos públicos del dominio, y su efecto
> sobre la interpretación de los resultados.

## Métricas de desempeño (no de equidad)
{{metricas_desempeno}}

> Se declaran para el desempeño desagregado del requerimiento R4.1. El
> desempeño no es objeto de optimización: se mide, no se persigue.
