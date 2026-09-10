# Aplicar el marco a otro dataset

El marco operativo se aplica a **sistemas de IA basados en sensores PIR para
monitoreo domiciliario**, no a un dataset concreto. Este documento define qué
debe aportar un equipo para evaluar su propio sistema, y qué obtiene a cambio
sin escribir una línea.

Es también la condición de una afirmación del marco: que el procedimiento sea
*utilizable por equipos de desarrollo distintos de quienes lo diseñaron* y que
sus resultados sean *comparables entre sistemas*. Si aplicar el marco exigiera
modificarlo, cada equipo terminaría evaluando con un instrumento distinto y la
comparación perdería sentido.

## Lo que el marco ya le da a cualquier dataset

| Módulo | Qué aporta |
|---|---|
| `comun/configuracion.py` | Carga y validación estricta, sin valores por defecto ocultos |
| `comun/datos.py` | Ventanas, características por zona, partición temporal, hash de datos |
| `comun/modelado.py` | Entrenamiento determinista y sellado con procedencia |
| `explicabilidad/` | Atribución local y global (R3.1, R3.2, R3.3) |
| `equidad/` | Desempeño desagregado y disparidad contra umbrales (R4.1, R4.2) |
| `trazabilidad/` | Bitácora append-only y verificación de auditabilidad (R5.1, R5.3) |
| `procedimiento/` | Los 6 pasos de la Tabla 9 y los artefactos del expediente |

Ninguno de esos módulos conoce un formato de origen. Todos operan sobre el
contrato de eventos.

## El contrato de eventos

Un lector devuelve un DataFrame con **exactamente** estas columnas, ordenado
por tiempo:

| Columna | Tipo | Contenido |
|---|---|---|
| `marca_temporal` | `datetime64` | Instante del evento |
| `sensor` | `str` | Identificador del sensor que lo emitió |
| `valor` | `str` | Estado reportado (`ON`, `OPEN`, `21.5`…) |
| `actividad` | `str` | Etiqueta vigente en ese instante |

Esa forma no es una abstracción inventada para este proyecto: **todo sistema
de sensores pasivos es un flujo de (cuándo, qué sensor, qué estado)**. La
columna `actividad` es la etiqueta supervisada; los eventos que no caen en
ninguna actividad anotada llevan `datos.actividades.etiqueta_sin_actividad`.

`leer_eventos` **verifica el contrato** sobre lo que devuelve el lector. Un
adaptador mal escrito falla en la costura, no tres pasos más adelante con un
error que ya no señala la causa.

## Qué tiene que aportar un equipo

### 1. Un lector — solo si su formato no está registrado

```python
# src/comun/lectores.py
class LectorEventosMiSistema(LectorEventos):
    nombre = "mi_sistema"
    formato = "descripción del formato, para el datasheet"

    def leer(self, config):
        crudo = pd.read_csv(config.datos.archivo_crudo)
        return pd.DataFrame({
            "marca_temporal": pd.to_datetime(crudo["ts"]),
            "sensor": crudo["dispositivo"].astype(str),
            "valor": crudo["estado"].astype(str),
            "actividad": crudo["etiqueta"].astype(str),
        })


LECTORES = {
    LectorEventosCASAS.nombre: LectorEventosCASAS,
    LectorEventosMiSistema.nombre: LectorEventosMiSistema,   # <- añadir
}
```

Y en `config.yaml`: `datos.formato: mi_sistema`. **Eso es todo el código.**

### 2. El inventario de sensores

```yaml
datos:
  columnas_sensor_pir: [PIR_SALA, PIR_COCINA, ...]
  sensores_puerta: [PUERTA_PRINCIPAL]
  sensores_temperatura: [TEMP_01]
```

Depende físicamente de cada instalación y por eso vive en configuración. El
marco exige que los declarados **estén presentes** en el crudo: uno declarado
que nunca reporta daría una columna entera de nulos.

### 3. El mapeo sensor → zona

```yaml
  zonas:
    PIR_SALA: LivingRoom
    PIR_COCINA: Kitchen
```

**Es obligatorio para todo sensor de ubicación.** El R3.3 exige que la
información de transparencia sea comprensible para destinatarios no técnicos:
una atribución SHAP sobre `PIR_017` no le dice nada a un cuidador; sobre
`conteo_Kitchen`, sí. El cargador rechaza la configuración si falta alguna.

Los sensores de temperatura **no** llevan zona: miden una condición
ambiental, no localizan a la persona.

### 4. Las decisiones de dominio

```yaml
  actividades:
    etiqueta_sin_actividad: Otro     # o descartar esos eventos
    excluidas: [ClaseDemasiadoRara]
  franjas_horarias:
    - {desde: 0, nombre: turno_noche}
    - {desde: 8, nombre: turno_dia}
  ventana:
    n_eventos: 30
  particion:
    estrategia: temporal_por_dia
    test_size: 0.2
```

Cada una es una decisión con consecuencias, y el marco obliga a declararla en
vez de heredar un valor por defecto.

### 5. Los subgrupos de equidad y sus umbrales

```yaml
equidad:
  subgrupos:
    - nombre: residente
      columna: residente_id
      categorias: []
  umbrales:
    demographic_parity_difference: 0.10
```

Aquí está la exigencia más fuerte del marco: **los umbrales se declaran antes
de ejecutar las pruebas**, y el paso 3 sella el hash de `config.yaml` para que
un auditor externo pueda comprobar que no se ajustaron después de ver los
resultados.

## Lo que el marco no puede resolver por nadie

Ser honestos sobre esto es parte del instrumento.

**Los subgrupos dependen de los metadatos que existan.** Un dataset con un
único residente no permite desagregar por población, y ninguna ingeniería lo
arregla: hacen falta datos de varias personas. El marco puede exigir que la
limitación se declare, no suplirla.

**El mapeo a zonas requiere conocer la instalación.** No se infiere del
archivo.

**La calidad de la anotación condiciona todo lo demás.** El marco evalúa
cumplimiento, no repara etiquetas.

## Lista de verificación

Antes de correr `make pipeline` sobre un sistema nuevo:

- [ ] El lector está registrado y `datos.formato` lo nombra
- [ ] Todos los sensores del crudo están declarados por tipo
- [ ] Todo sensor de ubicación tiene zona
- [ ] Las actividades excluidas están justificadas en el datasheet
- [ ] Las franjas horarias coinciden con las categorías del subgrupo
- [ ] Los umbrales de equidad están declarados **y justificados**
- [ ] `trazabilidad.responsable_por_defecto` nombra a una persona real, no al
      placeholder — el verificador rechaza la bitácora si conserva `TODO`
- [ ] `modelo.tipo` es de árbol (lo exige `TreeExplainer`)

Si algo falta, el cargador o el verificador lo dicen. Ese es el punto: las
omisiones tienen que ser ruidosas.
