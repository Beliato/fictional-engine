# Arquitectura

## Vista de módulos

```
src/
├── comun/            infraestructura compartida, sin lógica de negocio
│   ├── configuracion.py   carga + validación de config.yaml -> dataclasses frozen
│   ├── datos.py            carga/validación/partición determinista de CASAS
│   ├── modelado.py         construir/entrenar/sellar/persistir el clasificador
│   ├── semillas.py         control de aleatoriedad y verificación de entorno
│   └── utilidades.py       hashing, tiempo UTC, E/S JSON determinista
│
├── explicabilidad/   Principio 1 — SHAP
│   ├── atribucion_local.py    valores SHAP por inferencia -> artefacto por evento
│   ├── atribucion_global.py   importancia agregada + figuras
│   └── reporte.py             consolida el reporte de explicabilidad
│
├── equidad/          Principio 2 — desempeño desagregado + fairness
│   ├── desempeno_desagregado.py   métricas por subgrupo (sin veredicto)
│   ├── metricas_equidad.py        métricas fairlearn vs umbrales -> veredicto
│   └── reporte.py                 consolida el reporte de equidad
│
├── trazabilidad/     Principio 3 — registro + verificación
│   ├── esquema.py         RegistroInferencia (implementado) + (de)serialización
│   ├── registro.py        escritor append-only JSONL
│   └── verificacion.py    integridad + cobertura de la bitácora (CLI)
│
└── procedimiento/    orquestación
    ├── pasos.py           los 6 pasos como funciones puras sobre ContextoEjecucion
    ├── evidencia.py       model card, datasheet, reporte, bitácora, manifiesto
    └── orquestador.py     entrypoint: verifica entorno, fija semilla, encadena pasos
```

## Principios de diseño

- **Sin estado oculto.** Toda la parametrización está en `config.yaml`. El
  código no define constantes de negocio ni valores por defecto que
  sustituyan a los de la config: si falta una clave, el cargador falla.
- **Inmutabilidad.** La configuración y el `ContextoEjecucion` son dataclasses
  `frozen`. Los pasos devuelven un contexto nuevo, no mutan el recibido.
- **Determinismo.** `PYTHONHASHSEED` se exporta antes de arrancar Python;
  `fijar_semilla_global` se llama una sola vez; `n_jobs=1` evita
  no-determinismo por paralelismo.
- **Todo deja rastro.** Cada paso registra entradas, salidas y sus hashes. El
  manifiesto final permite verificar la ejecución bit a bit.
- **Un fallo de equidad es evidencia, no un crash.** El pipeline completa y
  reporta; el código de salida distingue "no aprueba" (2) de "error" (1).

## Flujo de datos

```
datos/crudos/casas.csv
   │  paso 1
   ▼
datos/intermedios/caracteristicas.parquet ──► ParticionSupervisada
   │  paso 2
   ▼
artefactos/modelo/                (ModeloSellado)
   │  paso 3                          │ paso 4
   ▼                                  ▼
artefactos/explicaciones/       artefactos/equidad/  (VeredictoEquidad)
   │                                  │
   └────────────► paso 5 ◄────────────┘
                    ▼
       artefactos/bitacora/inferencias.jsonl  (+ verificación)
                    │  paso 6
                    ▼
   artefactos/{model_card.md, datasheet.md, reporte_cumplimiento.md,
              bitacora_ejecucion.*, manifiesto.json}
```
