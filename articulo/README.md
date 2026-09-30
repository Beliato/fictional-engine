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

## Historia del texto

### La conversión del borrador

La primera versión en LaTeX conservó la redacción de Laura palabra por
palabra. Se comprobó comparando las palabras del borrador con las de los
`.tex`, sin acentos ni comandos. Cambiaron cuatro cosas:

1. **Acentos restaurados.** El .md y el .docx venían sin tildes.
2. **La referencia de CRISP-ML(Q) estaba mal.** Los autores 5 a 7 son
   Winkler, Peters y Müller, verificados en Crossref y arXiv. "Ludwig,
   Lauber-Rönsberg, Klöpper" venía de `docs/crisp-ml-q.md`, donde se escribió
   de memoria.
3. **La segunda frase de Agradecimientos** era una nota para las personas
   autoras y pasó a marca de pendiente.
4. **Bloque de autores**: los nombres de las dos personas autoras de la tesis
   y la afiliación a la Universidad CENFOTEC, donde había marcadores.

Después, las personas autoras quitaron la sección "Declaración sobre el uso
de inteligencia artificial" (ver pendiente 3).

### La alineación con la investigación (PIA02)

Una revisión contra el documento de investigación y contra los expedientes de
los pilotos encontró tres desvíos. Se corrigieron en cuatro cambios, y desde
entonces el texto ya no es solo el del borrador:

1. **Hallazgos.** Resultados reporta lo que encontró el marco —las variables
   dominantes, el desempeño como contexto, las 4 combinaciones de Aruba
   (Cuadro 3) y las 29 del multi-hogar, con el caso de Cook—, y la Discusión,
   los cuatro límites que declara el expediente. Todas las cifras salen de los
   expedientes.
2. **Diseño metodológico.** Design Science Research, enfoque mixto y tres
   fases, y una subsección nueva sobre cómo se derivaron los requerimientos
   (PIA02, capítulos 3 y 4). Las tres citas textuales de la ENIA se cotejaron
   con el PDF.
3. **Literatura.** De 7 a 21 referencias, cada una donde PIA02 la usa, todas
   verificadas.
4. **Título y figura.** El título nombra la ENIA y a las personas adultas
   mayores. La Figura 1 redibuja la arquitectura de PIA02 (Figura 2), que en
   Word está hecha con formas y no se puede extraer como imagen; pasó a
   Materiales y métodos, donde el texto la cita.

## Pendientes para decidir

Ordenados por importancia.

1. **Fuente de "hh107 tiene dos residentes".** D52 explica el caso de Cook con
   ese dato, pero no consta en el expediente ni en el crudo del repositorio.
   Resultados presenta el caso sin esa explicación hasta tener la fuente.
   Tampoco tiene cita la relevancia clínica de Bed\_to\_Toilet.
2. **Aruba y "adultas mayores".** Materiales y métodos dice que en ambos pilotos
   la población son personas adultas mayores. La documentación del conjunto
   describe a la residente de Aruba como "mujer adulta voluntaria".
3. **Declaración de uso de IA.** Las personas autoras la quitaron por ahora.
   Antes del envío, revisar si la política de la revista la exige: GitHub
   Copilot armó el borrador inicial, y Claude hizo la conversión a LaTeX, la
   verificación de referencias y la alineación con PIA02.
4. **Dos puntos de la revisión que no entraron en los cuatro cambios:** los
   *refinamientos* que el piloto introdujo respecto de PIA02 (métricas que
   deciden, descarte de Fairlearn, piloto multi-hogar, nombres de zona), que
   el objetivo específico 3 pide documentar; y la *contribución dual
   ENIA–AI Act* para el sector healthtech, central en PIA02 y ausente en el
   artículo.
5. **Título.** Es una propuesta; la traducción al inglés también, y la
   plantilla pide evitar traductores automáticos.
6. **Figura 1.** Es un redibujo. Si se prefiere la original, exportarla desde
   Word como PNG a 300 dpi y reemplazar `contenido/figura-arquitectura.tex`.
7. **Versión de la ENIA.** La página de créditos dice *Versión 1.0, 24 de
   octubre de 2024*, con ISBN 978-9968-732-94-9; PIA02 la cita como "Versión
   2.6", que el documento no menciona. El mismo PDF se declara "versión
   simplificada" (p. 3) y remite a la completa en www.micitt.go.cr.
8. **Autores**: orden, correos, ORCID y si hay una tercera persona.
9. **Palabras clave**: la plantilla pide términos del tesauro de la UNESCO.
10. **AI Act**: la referencia usa el título en inglés. EUR-Lex no se pudo
    consultar para verificar el título oficial en español.
11. **Páginas de Lundberg y Lee (2017)**: 4765–4774 vienen del borrador y de
    PIA02; la página oficial de NeurIPS no las muestra.

## Correcciones para PIA02

La revisión encontró en el documento de investigación cosas que no deberían
pasar al artículo:

- La ENIA como "Versión 2.6": es la 1.0 (ver pendiente 7).
- "La ENIA reconoce textualmente la edad como variable protegida" (1.4, 2.5,
  4.1.2, 5.4 y Tabla 5). El texto dice "respetando las diferencias de edad,
  etnia, género…", en el contexto de la accesibilidad (p. 32). "Variable
  protegida" es una interpretación, no una cita textual.
- La cita "realizar auditorías y pruebas continuas para identificar y corregir
  cualquier sesgo potencial" está en la p. 33, no en la 32 (4.1.2).
- El principio 3 se cita en "pp. 31-32"; está en la p. 32.
- Mitchell et al. (2019) como "FAccT '19": en 2019 el congreso se llamaba
  FAT\*.

Kim et al. (2022), que citan las fichas de caracterización de los
expedientes, sí existe: es una de las revisiones de alcance de PIA02, y el
artículo la cita.
