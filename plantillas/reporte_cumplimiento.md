# Reporte de cumplimiento — ejecución {{id_ejecucion}}

- **Fecha (UTC):** {{fecha_ejecucion}}
- **Versión del marco:** {{version_marco}}
- **Modelo:** {{modelo_tipo}} v{{modelo_version}} ({{hash_parametros}})
- **Manifiesto:** {{ruta_manifiesto}}

## Veredicto global
**{{veredicto_global}}**

| Principio | Estado | Evidencia |
|---|---|---|
| 1. Explicabilidad | {{estado_explicabilidad}} | {{ruta_reporte_explicabilidad}} |
| 2. Equidad | {{estado_equidad}} | {{ruta_reporte_equidad}} |
| 3. Trazabilidad | {{estado_trazabilidad}} | {{ruta_bitacora}} |

## 1. Explicabilidad
{{resumen_explicabilidad}}

## 2. Equidad
- Subgrupos evaluados: {{subgrupos}}
- Umbrales PRE-DECLARADOS (de `config.yaml`, sin ajuste posterior):

{{tabla_umbrales}}

- Resultados observados:

{{tabla_metricas_equidad}}

- Métricas incumplidas: {{metricas_incumplidas}}

## 3. Trazabilidad
- Registros de inferencia: {{n_inferencias}}
- Verificación de integridad: {{estado_verificacion_bitacora}}
- Cobertura (1 registro por inferencia del set de prueba): {{estado_cobertura}}

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
