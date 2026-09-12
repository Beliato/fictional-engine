# Guion de demostración

Cómo mostrar el marco funcionando en vivo, en menos de un minuto, y qué decir
sobre cada artefacto que produce.

## Qué es esta demo

Una corrida **real** del procedimiento completo de la Tabla 9 —las dos
precondiciones y los seis pasos— sobre los primeros 20 días del dataset en
vez de los 220. Mismo protocolo, mismos umbrales, mismos artefactos. Lo único
que cambia es cuántos datos entran.

No reemplaza al expediente del piloto: escribe en `artefactos/demo/` y no
toca `artefactos/`.

| | Piloto completo | Demo |
|---|---:|---:|
| Eventos | 1.719.552 | 133.827 |
| Ventanas | 57.297 | 4.457 |
| Inferencias registradas | 11.175 | 1.054 |
| Duración | ~17 min | **~28 s** |

El costo está casi todo en explicar cada inferencia con SHAP, que es
precisamente lo que el R3.1 exige y lo que hace lenta la corrida completa.

## El comando

```bash
make demo
```

Con más días, si hay tiempo: `make demo DIAS=40`.

Requisitos: el crudo en `datos/crudos/` (ver el datasheet) y el entorno creado
con `make setup`.

La salida termina así:

```
Ejecución: demo
Equidad: no aprueba
Requerimientos cubiertos: los nueve
Código de salida: 2
```

**Lo primero que conviene explicar:** el código 2 no es un error. Es un
hallazgo: el pipeline completó y la evidencia dice que el sistema auditado no
cumple equidad. Un error de ejecución sale con 1.

## Recorrido por la evidencia

Siete artefactos, en este orden. Cada uno responde una pregunta distinta.

### 1. ¿El sistema cumple? — `reporte_cumplimiento.md`

```bash
head -40 artefactos/demo/reporte_cumplimiento.md
```

Abre con el veredicto global, el estado de los tres principios y la tabla de
cobertura de los **nueve requerimientos**. Es la única pantalla que hay que
mostrar si el tiempo es corto.

El veredicto distingue dos cosas que se confunden: `EVIDENCIA INCOMPLETA`
(falta un artefacto) no es lo mismo que `NO CUMPLE` (la evidencia está
completa y muestra un incumplimiento).

### 2. ¿Cómo sé que no ajustaron los umbrales? — `protocolo_evaluacion.md`

```bash
head -25 artefactos/demo/protocolo_evaluacion.md
```

El control metodológico del paso 3: el hash SHA-256 del `config.yaml` sellado
**antes** de medir, y comprobado otra vez en el paso 6. Un auditor lo
reproduce con `sha256sum config.yaml` sin ejecutar nada del marco.

Este es el punto más fuerte frente a un tribunal: la declaración previa de
criterios deja de ser una afirmación de buena fe.

### 3. ¿Por qué no cumple? — `reporte_equidad.md`

```bash
sed -n '/## Veredicto/,/## Protocolo/p' artefactos/demo/reporte_equidad.md
```

Las combinaciones que exceden su umbral, con las tasas de cada categoría y el
número de casos detrás de cada una. También declara las que **no son
evaluables** por falta de soporte: no se descartan en silencio ni cuentan
como aprobadas.

### 4. ¿Por qué decidió eso? — `reporte_explicabilidad.md`

```bash
sed -n '/### Aciertos/,/### Errores/p' artefactos/demo/reporte_explicabilidad.md
```

Una explicación en lenguaje llano, del tipo *"El sistema infirió «Relax» con
una confianza del 94 %. Pesó a favor: 28 activaciones de movimiento en
LoungeChair…"*. Las zonas se nombran por habitación y no por identificador de
sensor, que es lo que exige el R3.3.

### 5. ¿Quién responde por esta decisión? — la bitácora

```bash
head -1 artefactos/demo/bitacora/inferencias.jsonl | python3 -m json.tool
```

Los ocho campos mínimos de la Tabla 8. Dos cosas que conviene señalar:

- `referencia_entrada` es un **hash** de la fila, no los eventos: la bitácora
  de un sistema de monitoreo domiciliario no puede contener la rutina de la
  vivienda.
- `referencia_explicacion` apunta al artefacto de explicación con la forma
  `archivo#id_evento`.

### 6. Reconstruir una decisión de punta a punta

```bash
grep '"id_evento": "ven-00000"' \
  artefactos/demo/explicaciones/local/explicaciones.jsonl | python3 -m json.tool
```

Del registro se llega a la atribución de variables de esa inferencia concreta.
Eso es el R5.3: reconstruir *ex post* y atribuir a un responsable
identificable.

### 7. ¿Es reproducible? — `manifiesto.json`

```bash
python3 -c "import json;m=json.load(open('artefactos/demo/manifiesto.json'));print(len(m['artefactos']),'artefactos sellados');print(m['entorno']['git_commit'], 'árbol limpio:', m['entorno']['git_arbol_limpio'])"
```

El sello final: hash de cada artefacto, hashes de datos crudos y procesados,
versiones de todas las dependencias, commit de git y si el árbol de trabajo
tenía cambios sin confirmar. Ese último dato es incómodo a propósito: un
commit con el árbol sucio no identifica el código que corrió.

## Preguntas probables, y con qué se responden

| Pregunta | Artefacto |
|---|---|
| ¿Cómo sabemos que los umbrales no se ajustaron a los resultados? | `protocolo_evaluacion.md` (hash sellado) y el historial de git |
| ¿Por qué la paridad demográfica no decide el veredicto? | `reporte_equidad.md`, sección de notas, y D42 |
| ¿Qué pasa con las actividades con pocos casos? | Tabla de "no evaluables" del reporte de equidad |
| ¿El marco sirve para otro dataset? | `docs/aplicar-a-otro-dataset.md`: hay que escribir un lector |
| ¿Se puede repetir esta corrida? | Bloque final del `reporte_cumplimiento.md` |

## Mostrar el expediente del piloto completo

Los artefactos de la corrida sobre los 220 días están en `artefactos/`, con la
misma estructura. La demo sirve para mostrar el **proceso**; el piloto, para
mostrar los **resultados** que van en la tesis.
