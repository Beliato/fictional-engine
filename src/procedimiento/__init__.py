"""Procedimiento — orquestación del marco operativo de cumplimiento.

Precondiciones (el modelo es sujeto de prueba, no objeto de optimización):
    - Preparación de datos       (src.comun.datos)
    - Sellado del modelo         (src.comun.modelado)

Los 6 pasos del procedimiento (Tabla 9), según las funciones del NIST AI RMF:
    1. Caracterización del sistema        -> ficha de caracterización   MAPEAR
    2. Documentación del conjunto de datos-> datasheet                  MAPEAR
    3. Declaración de criterios           -> protocolo declarado        MAPEAR
    4. Ejecución de las pruebas técnicas  -> resultados + bitácora      MEDIR
    5. Generación de artefactos auditables-> reportes + model card      GOBERNAR
    6. Verificación de auditabilidad      -> expediente de evidencia    GESTIONAR

Los tres módulos de principio (explicabilidad, equidad, trazabilidad) se
aplican dentro del paso 4; sus artefactos se consolidan en el paso 5.
"""
