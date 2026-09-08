# notebooks/

**Solo exploración.** El código de producción vive en `src/`.

Reglas:

1. Un notebook nunca es dependencia de `src/` ni del pipeline. Si algo de un
   notebook hace falta en producción, se migra a `src/` con pruebas.
2. Al inicio de cada notebook, fijar la semilla y registrar versiones:
   ```python
   from src.comun.semillas import fijar_semilla_global, instantanea_entorno
   fijar_semilla_global(42)
   instantanea_entorno()
   ```
3. Antes de commitear: `Kernel > Restart & Run All` y limpiar salidas
   voluminosas. Los `.ipynb_checkpoints/` están ignorados por git.
4. Nombrar `NN_tema.ipynb` (p. ej. `01_exploracion_casas.ipynb`).
