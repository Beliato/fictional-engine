# Model Card — {{modelo_tipo}} v{{modelo_version}}

> Generada automáticamente por el paso 6 del marco. No editar a mano:
> los marcadores `{{...}}` los rellena `src.procedimiento.evidencia.generar_model_card`.

## 1. Detalles del modelo
- **Tipo:** {{modelo_tipo}}
- **Versión:** {{modelo_version}}
- **Fecha de entrenamiento (UTC):** {{fecha_entrenamiento}}
- **Hiperparámetros:** {{hiperparametros}}
- **Semilla:** {{semilla}}
- **Hash de parámetros:** {{hash_parametros}}
- **Hash de datos de entrenamiento:** {{hash_datos_entrenamiento}}
- **Versión del marco:** {{version_marco}}
- **Responsable declarado:** {{responsable}}

## 2. Uso previsto
- **Tarea:** clasificación de actividad domiciliaria a partir de eventos de
  sensores PIR (dataset CASAS).
- **Usuarios previstos:** {{usuarios_previstos}}
- **Usos fuera de alcance:** {{usos_fuera_alcance}}

## 3. Datos
- **Fuente:** {{datos_fuente}}
- **Partición:** train/test {{test_size}} (estratificada: {{estratificar}})
- Ver `datasheet.md` para procedencia y composición.

## 4. Desempeño global
{{tabla_desempeno_global}}

## 5. Desempeño desagregado (Principio 2 — Equidad)
{{tabla_desempeno_desagregado}}

## 6. Métricas de equidad vs umbrales PRE-DECLARADOS
> Umbrales fijados en `config.yaml` **antes** de ejecutar. No ajustados a posteriori.

{{tabla_metricas_equidad}}

- **Veredicto de equidad:** {{veredicto_equidad}}

## 7. Explicabilidad (Principio 1)
- **Método:** {{explainer}}
- **Importancia global (top):** {{importancia_global_top}}
- Figuras: {{rutas_figuras_explicabilidad}}

## 8. Trazabilidad (Principio 3)
- **Bitácora de inferencias:** {{ruta_bitacora}} ({{n_inferencias}} registros)
- **Verificación de la bitácora:** {{estado_verificacion_bitacora}}

## 9. Limitaciones y riesgos
{{limitaciones}}

## 10. Articulación normativa
| Principio | ENIA Costa Rica | AI Act EU | NIST AI RMF |
|---|---|---|---|
| Explicabilidad | {{enia_explicabilidad}} | {{aiact_explicabilidad}} | {{nist_explicabilidad}} |
| Equidad | {{enia_equidad}} | {{aiact_equidad}} | {{nist_equidad}} |
| Trazabilidad | {{enia_trazabilidad}} | {{aiact_trazabilidad}} | {{nist_trazabilidad}} |

## 11. Reproducibilidad
- **Manifiesto:** {{ruta_manifiesto}}
- **Instantánea del entorno:** {{instantanea_entorno}}
