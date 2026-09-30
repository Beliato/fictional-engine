@echo off
rem ===========================================================================
rem Compila el articulo completo: pdfLaTeX -> Biber -> pdfLaTeX -> pdfLaTeX.
rem
rem Uso: doble clic desde el Explorador de archivos, o "compilar.bat" en una
rem terminal. Con /nopause no espera una tecla al final (para usarlo desde otro
rem script). Devuelve 0 si compila y 1 si hay un error.
rem
rem Los mensajes van sin tildes a proposito: la consola de Windows no usa UTF-8
rem y las mostraria rotas.
rem ===========================================================================
setlocal
set "DOC=tecnologia-en-marcha"
set "RC=1"

rem cmd.exe no puede trabajar sobre una ruta de red como \\wsl$\...: pushd le
rem asigna una letra de unidad temporal, y popd la libera al final.
pushd "%~dp0" || (echo No se pudo entrar a la carpeta del articulo. & goto :fin)

echo [1/4] pdfLaTeX
pdflatex -interaction=nonstopmode -halt-on-error "%DOC%.tex" >nul || goto :error_latex
echo [2/4] Biber
biber "%DOC%" >nul || goto :error_biber
echo [3/4] pdfLaTeX
pdflatex -interaction=nonstopmode -halt-on-error "%DOC%.tex" >nul || goto :error_latex
echo [4/4] pdfLaTeX
pdflatex -interaction=nonstopmode -halt-on-error "%DOC%.tex" >nul || goto :error_latex

echo.
echo Listo: %DOC%.pdf
findstr /C:"Output written on" "%DOC%.log"
set "RC=0"
goto :salir

:error_latex
echo.
echo ERROR de LaTeX. El problema, segun %DOC%.log:
echo   (la linea que empieza con "!" es el error; "l." es la linea del .tex)
findstr /R /B /C:"!" /C:"l\.[0-9]" "%DOC%.log"
goto :salir

:error_biber
echo.
echo ERROR de Biber, el programa de la bibliografia. Detalle en %DOC%.blg:
findstr /C:"ERROR" "%DOC%.blg"
goto :salir

:salir
popd
:fin
if /i not "%~1"=="/nopause" pause
endlocal & exit /b %RC%
