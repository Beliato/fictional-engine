# Arquitectura

## Vista de módulos

```
src/
├── comun/            infraestructura compartida, sin lógica de negocio
│   ├── configuracion.py   carga + validación de config.yaml -> dataclasses frozen
│   ├── lectores.py         CONTRATO DE INGESTA + lector por formato
│   ├── datos.py            validación/características/partición (sin formato)
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
    ├── pasos.py           PRECONDICIONES + los 6 pasos de la Tabla 9, como
    │                      funciones puras sobre ContextoEjecucion
    ├── evidencia.py       ficha, datasheet, protocolo, model card, reporte,
    │                      bitácora, manifiesto
    └── orquestador.py     entrypoint: verifica entorno, fija semilla, encadena
                           precondiciones y luego pasos
```

Los tres módulos de principio no son pasos: se **aplican** dentro del paso 4
(ejecución de pruebas) y se **documentan** en el paso 5 (generación de
artefactos).

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
   │  precondición A
   ▼
datos/intermedios/caracteristicas.parquet ──► ParticionSupervisada
   │  precondición B
   ▼
artefactos/modelo/                (ModeloSellado)
   │
   │  paso 1 ──► artefactos/ficha_caracterizacion.md
   │  paso 2 ──► artefactos/datasheet.md
   │  paso 3 ──► artefactos/protocolo_evaluacion.md  (sella hash de config.yaml)
   ▼
────────────────────── paso 4: ejecución de pruebas ──────────────────────
   │                        │                            │
   ▼                        ▼                            ▼
artefactos/            artefactos/equidad/        artefactos/bitacora/
explicaciones/         (VeredictoEquidad)         inferencias.jsonl
   │                        │                            │
   └────────────────────────┴──────────┬─────────────────┘
                                       │  paso 5
                                       ▼
   artefactos/{reporte_explicabilidad.md, reporte_equidad.md, model_card.md,
              reporte_cumplimiento.md}
                                       │  paso 6
                                       ▼
   artefactos/{bitacora_ejecucion.*, manifiesto.json}
   + comprobación: reconstrucción de decisiones · hash del protocolo intacto
     · los 9 requerimientos con artefacto presente
```
