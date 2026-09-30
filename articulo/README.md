# Artículo — Tecnología en Marcha

Versión LaTeX del borrador de Laura Segura
([`articulo_tecnologia_en_marcha.md`](../articulo_tecnologia_en_marcha.md)),
con el formato de la plantilla de **Tecnología en Marcha** (TEC).

## Compilar en la computadora (MiKTeX y TeXworks)

**Todo el artículo, con bibliografía:** doble clic en `compilar.bat`. Corre
pdfLaTeX → Biber → pdfLaTeX → pdfLaTeX y deja `tecnologia-en-marcha.pdf` en
esta carpeta. Si algo falla, muestra el error y la línea: `l.20` es la línea
20 del archivo de sección que se estaba leyendo.

Al abrirlo desde `\\wsl$\...`, la consola puede avisar que "no admite rutas
UNC". Es un aviso inofensivo: el script entra a la carpeta con `pushd`.

**Mientras se edita texto:** en TeXworks, el botón de compilar con
**pdfLaTeX** alcanza, desde cualquier archivo de `contenido/`. La primera
línea de cada uno (`% !TEX root`) le dice a TeXworks que compile el archivo
principal. Hace falta `compilar.bat` solo cuando cambian las citas o
`referencias.bib`, porque Biber no corre desde el botón.

Todos los `.tex` declaran `% !TEX encoding = UTF-8 Unicode`, para que las
tildes no se rompan aunque TeXworks tenga otra codificación por defecto.

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
| `compilar.bat` | Compilación completa con bibliografía, en Windows |
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

Después de la conversión, las personas autoras quitaron la sección
"Declaración sobre el uso de inteligencia artificial" (ver pendiente 3).

## Pendientes para decidir

Ordenados por importancia.

1. **Fuente de "hh107 tiene dos residentes".** D52 explica el caso de `Cook`
   con ese dato, pero no consta en el expediente ni en el crudo del
   repositorio. Resultados presenta el caso sin esa explicación hasta tener la
   fuente. Tampoco tiene cita la relevancia clínica de Bed\_to\_Toilet.
2. **Aruba y "adultas mayores".** Materiales y métodos dice que en ambos pilotos
   la población son personas adultas mayores. La documentación del conjunto
   describe a la residente de Aruba como "mujer adulta voluntaria".
3. **Declaración de uso de IA.** Las personas autoras la quitaron por ahora.
   Antes del envío, revisar si la política de la revista la exige: GitHub
   Copilot armó el borrador inicial, y Claude hizo la conversión a LaTeX y la
   verificación de referencias.
4. **Versión de la ENIA.** El PDF usado en todo el proyecto se declara
   "versión simplificada" (p. 3) y remite a la completa en www.micitt.go.cr.
   Decidir cuál se cita; si es la completa, las páginas del repositorio (27, 32
   y 33) hay que volver a verificarlas.
7. **Autores**: orden, correos, ORCID y si hay una tercera persona.
8. **Figura 1** es un marcador de texto y no se cita en el cuerpo, que la
   plantilla exige.
9. **Palabras clave**: la plantilla pide términos del tesauro de la UNESCO.
11. **AI Act**: la referencia usa el título en inglés. EUR-Lex no se pudo
    consultar para verificar el título oficial en español.
12. **Páginas de Lundberg y Lee (2017)**: 4765–4774 vienen del borrador; la
    página oficial de NeurIPS no las muestra.

## Una referencia que no está, a propósito

Las fichas de caracterización de los expedientes citan **"Kim et al., 2022"**.
Ningún archivo del repositorio tiene la referencia completa y no se pudo
identificar el trabajo. No está en `referencias.bib`, y el artículo no la
cita.
