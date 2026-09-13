# Reporte de cumplimiento — ejecución {{id_ejecucion}}

- **Fecha (UTC):** {{fecha_ejecucion}}
- **Versión del marco:** {{version_marco}}
- **Modelo:** {{modelo_tipo}} v{{modelo_version}} ({{hash_parametros}})
- **Manifiesto:** {{ruta_manifiesto}}

## Veredicto global
**{{veredicto_global}}**

| Componente del marco | Principio rector de la ENIA | Estado | Evidencia |
|---|---|---|---|
| Explicabilidad | 3 — Transparencia y explicabilidad | {{estado_explicabilidad}} | {{ruta_reporte_explicabilidad}} |
| Equidad | 4 — Equidad y no discriminación | {{estado_equidad}} | {{ruta_reporte_equidad}} |
| Trazabilidad | 5 — Responsabilidad | {{estado_trazabilidad}} | {{ruta_bitacora}} |

> Los tres componentes del marco no son los principios 1, 2 y 3 de la ENIA:
> corresponden al 3, al 4 y al 5. El apartado de alcance lista los siete.

## Explicabilidad
{{resumen_explicabilidad}}

## Equidad
- Subgrupos evaluados: {{subgrupos}}
- Umbrales PRE-DECLARADOS, sellados por hash en el paso 3 y sin ajuste
  posterior:

{{tabla_umbrales}}

- Resultados observados:

{{tabla_metricas_equidad}}

- Métricas incumplidas: {{metricas_incumplidas}}

## Trazabilidad
- Registros de inferencia: {{n_inferencias}}
- Verificación de integridad: {{estado_verificacion_bitacora}}
- Cobertura (1 registro por inferencia del set de prueba): {{estado_cobertura}}

## Alcance del marco frente a la ENIA

{{alcance}}

## Cobertura de los nueve requerimientos

> Criterio de éxito del piloto: que la ejecución genere los artefactos
> asociados a los nueve requerimientos y que estos permitan reconstruir el
> comportamiento del sistema.

{{tabla_requerimientos}}

## Articulación normativa
{{tabla_articulacion_normativa}}

## Reproducción de esta ejecución
```
git checkout {{git_commit}}
make setup
# colocar el crudo en datos/crudos/ (ver datasheet.md)
make pipeline
```
Los hashes del manifiesto deben coincidir bit a bit.
