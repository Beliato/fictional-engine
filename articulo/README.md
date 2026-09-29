# Artículo — Tecnología en Marcha

Versión LaTeX del borrador de Laura Segura
([`articulo_tecnologia_en_marcha.md`](../articulo_tecnologia_en_marcha.md)),
con el formato de la plantilla de **Tecnología en Marcha** (TEC).

## Compilar en Overleaf

1. Subir el contenido de esta carpeta a un proyecto nuevo (*New Project →
   Upload Project*, con un .zip de `articulo/`).
2. *Menu → Compiler*: **pdfLaTeX**. *Main document*:
   **`tecnologia-en-marcha.tex`**.
3. Compilar. Overleaf corre `biber` solo para la bibliografía.

## Estructura

| Archivo | Contenido |
|---|---|
| `tecnologia-en-marcha.tex` | Preámbulo y formato de la plantilla |
| `contenido/00-metadatos.tex` | Título, autores, resumen, palabras clave |
| `contenido/01-…06-*.tex` | Una sección por archivo |
| `contenido/macros.tex` | Marcas de revisión |
| `referencias.bib` | Bibliografía verificada |

El contenido está separado del formato a propósito: si el artículo termina en
otra revista —por ejemplo **Revista Ingeniería** (UCR), cuya guía también está
disponible—, se agrega otro archivo principal y las secciones no cambian.

## Marcas de revisión

El PDF muestra dos tipos de marca:

- **[Pendiente: …]** en rojo: algo que falta escribir o decidir.
- **[Revisar: …]** en naranja: una afirmación del texto que no coincide con la
  evidencia del repositorio o que no se pudo verificar.

Antes del envío, en `contenido/macros.tex` cambiar `\notastrue` por
`\notasfalse`: las marcas desaparecen sin tocar el texto.

## Qué cambió respecto del borrador

Cuatro cosas; la redacción es la de Laura, palabra por palabra. Se comprobó
comparando las palabras del borrador con las de los `.tex`, sin acentos ni
comandos: las únicas diferencias son la numeración de cuadros y figura, que
genera LaTeX, y el punto 3.

1. **Acentos restaurados.** El .md y el .docx venían sin tildes.
2. **La referencia de CRISP-ML(Q) estaba mal.** Los autores 5 a 7 son
   Winkler, Peters y Müller, verificados en Crossref y arXiv. "Ludwig,
   Lauber-Rönsberg, Klöpper" venía de `docs/crisp-ml-q.md`, donde se escribió
   de memoria.
3. **La segunda frase de Agradecimientos** era una nota para las personas
   autoras; ahora es una marca de pendiente.
4. **Bloque de autores**: donde el borrador tenía los marcadores de la
   plantilla, ahora están los nombres de las dos personas autoras de la tesis y
   la afiliación a la Universidad CENFOTEC. Correos, ORCID y orden quedan
   pendientes.

Las citas `[1]`–`[7]` pasaron a `\cite{}` y biblatex las numera en el mismo
orden del borrador.

## Pendientes para decidir

Ordenados por importancia.

1. **Faltan los hallazgos de equidad.** Resultados dice que el marco midió
   disparidades pero no cuáles: las 4 combinaciones de Aruba, las 29 del
   multi-hogar y el diagnóstico de `Cook` en `hh107`. Las cifras están como
   comentario en `contenido/03-resultados.tex`.
2. **Aruba y "adultas mayores".** Materiales y métodos dice que en ambos pilotos
   la población son personas adultas mayores. La documentación del conjunto
   describe a la residente de Aruba como "mujer adulta voluntaria".
3. **Declaración de uso de IA.** Menciona GitHub Copilot. La conversión a LaTeX
   y la verificación de referencias se hicieron con Claude.
4. **Versión de la ENIA.** El PDF usado en todo el proyecto se declara
   "versión simplificada" (p. 3) y remite a la completa en www.micitt.go.cr.
   Decidir cuál se cita; si es la completa, las páginas del repositorio (27, 32
   y 33) hay que volver a verificarlas.
5. **Referencias que faltan.** El depósito de Zenodo de la serie multi-hogar pide
   citar Cook et al. (2013); también están sin citar el datasheet, el model
   card, la igualdad de oportunidades, los bosques aleatorios y scikit-learn.
   Todas están en `referencias.bib`, verificadas, listas para `\cite`.
6. **Límites que declara el expediente y el artículo no**: la franja horaria
   sale de la hora, que es variable de entrada; la exactitud del multi-hogar es
   0,22–0,43 contra 0,70 en Aruba; no se midió robustez ni varianza entre
   semillas.
7. **Autores**: orden, correos, ORCID y si hay una tercera persona.
8. **Figura 1** es un marcador de texto y no se cita en el cuerpo, que la
   plantilla exige.
9. **Palabras clave**: la plantilla pide términos del tesauro de la UNESCO.
10. **Cita [1] en la Introducción**: el artículo de Aruba respalda el
    reconocimiento de actividades con sensores, no el apoyo a cuidadores.
11. **AI Act**: la referencia usa el título en inglés. EUR-Lex no se pudo
    consultar para verificar el título oficial en español.
12. **Páginas de Lundberg y Lee (2017)**: 4765–4774 vienen del borrador; la
    página oficial de NeurIPS no las muestra.

## Una referencia que no está, a propósito

Las fichas de caracterización de los expedientes citan **"Kim et al., 2022"**.
Ningún archivo del repositorio tiene la referencia completa y no se pudo
identificar el trabajo. No está en `referencias.bib`, y el artículo no la
cita.
