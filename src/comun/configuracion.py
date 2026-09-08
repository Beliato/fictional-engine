"""Carga y validación de la configuración central (`config.yaml`).

Principio: sin estado oculto. Toda la parametrización vive en `config.yaml`.
El cargador convierte ese YAML en dataclasses inmutables y falla de forma
explícita si falta una clave obligatoria o si un valor es incoherente.

Dos reglas gobiernan este módulo:

1. **Nunca hay valores por defecto.** Si una clave falta, se lanza
   `ConfiguracionInvalida`. Un default silencioso convertiría el código en una
   segunda fuente de verdad, y entonces el `config.yaml` volcado al manifiesto
   de evidencia dejaría de describir la ejecución real.
2. **Las claves desconocidas también fallan.** Un umbral mal escrito no debe
   desaparecer en silencio: desaparecería junto con la prueba que gobierna.
   Es el mismo criterio que aplica `trazabilidad.esquema`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# --- Estructura tipada de la configuración -----------------------------------
# Las dataclasses son `frozen=True` para impedir mutaciones en tiempo de
# ejecución (el estado de configuración no debe cambiar tras la carga).


@dataclass(frozen=True)
class ParticionDatos:
    test_size: float
    estratificar: bool


@dataclass(frozen=True)
class ConfigDatos:
    fuente: str
    archivo_crudo: Path
    columna_objetivo: str
    columnas_sensor_pir: tuple[str, ...]
    particion: ParticionDatos


@dataclass(frozen=True)
class ConfigModelo:
    tipo: str
    version: str
    hiperparametros: dict[str, Any]


@dataclass(frozen=True)
class ConfigExplicabilidad:
    explainer: str
    muestras_globales: int
    guardar_local_por_inferencia: bool


@dataclass(frozen=True)
class Subgrupo:
    nombre: str
    columna: str
    categorias: tuple[str, ...]


@dataclass(frozen=True)
class ConfigEquidad:
    subgrupos: tuple[Subgrupo, ...]
    umbrales: dict[str, float]


@dataclass(frozen=True)
class ConfigTrazabilidad:
    version_esquema: str
    formato: str
    responsable_por_defecto: str


@dataclass(frozen=True)
class Rutas:
    datos_crudos: Path
    datos_intermedios: Path
    artefactos: Path
    plantillas: Path
    registro_inferencias: Path
    manifiesto: Path
    ficha_caracterizacion: Path
    protocolo_evaluacion: Path
    datasheet: Path
    model_card: Path
    reporte_cumplimiento: Path


@dataclass(frozen=True)
class Configuracion:
    """Configuración completa y validada del marco."""

    version_marco: str
    semilla: int
    pythonhashseed: int
    n_jobs: int
    rutas: Rutas
    datos: ConfigDatos
    modelo: ConfigModelo
    explicabilidad: ConfigExplicabilidad
    equidad: ConfigEquidad
    trazabilidad: ConfigTrazabilidad
    articulacion_normativa: dict[str, dict[str, str]]
    # Copia cruda del YAML, útil para volcarla en el manifiesto de evidencia.
    crudo: dict[str, Any]


# --- Ayudantes de validación -------------------------------------------------
# Se usan claves anidadas con notación de punto (`equidad.umbrales`) en los
# mensajes de error: quien lo lea tiene que poder abrir el YAML e ir directo.


def _exigir_mapa(valor: Any, contexto: str) -> dict[str, Any]:
    """Comprueba que `valor` es un bloque de claves y lo devuelve."""
    if not isinstance(valor, dict):
        raise ConfiguracionInvalida(
            f"{contexto}: se esperaba un bloque de claves, se recibió "
            f"{type(valor).__name__}"
        )
    return valor


def _claves(mapa: dict[str, Any], esperadas: set[str], contexto: str) -> None:
    """Exige que `mapa` tenga exactamente las claves `esperadas`."""
    faltantes = esperadas - mapa.keys()
    desconocidas = mapa.keys() - esperadas
    if faltantes or desconocidas:
        partes = []
        if faltantes:
            partes.append(f"faltan {sorted(faltantes)}")
        if desconocidas:
            partes.append(f"no se reconocen {sorted(desconocidas)}")
        raise ConfiguracionInvalida(f"{contexto}: " + "; ".join(partes))


def _tipo(valor: Any, esperado: type | tuple[type, ...], contexto: str) -> Any:
    """Exige que `valor` sea de `esperado` y lo devuelve.

    `bool` es subclase de `int` en Python, así que se rechaza explícitamente
    cuando se pide un número: `n_jobs: true` no debe pasar por un 1.
    """
    if esperado in (int, float) and isinstance(valor, bool):
        raise ConfiguracionInvalida(
            f"{contexto}: se esperaba {esperado.__name__}, se recibió bool"
        )
    if esperado is float and isinstance(valor, int):
        return float(valor)
    if not isinstance(valor, esperado):
        nombres = (
            esperado.__name__
            if isinstance(esperado, type)
            else "/".join(t.__name__ for t in esperado)
        )
        raise ConfiguracionInvalida(
            f"{contexto}: se esperaba {nombres}, se recibió "
            f"{type(valor).__name__}"
        )
    return valor


def _texto_no_vacio(valor: Any, contexto: str) -> str:
    """Exige una cadena con contenido real (no vacía ni solo espacios)."""
    texto = _tipo(valor, str, contexto)
    if not texto.strip():
        raise ConfiguracionInvalida(f"{contexto}: no puede estar vacío")
    return texto


def _lista_de_textos(valor: Any, contexto: str) -> tuple[str, ...]:
    """Convierte una lista YAML de cadenas en una tupla inmutable."""
    elementos = _tipo(valor, list, contexto)
    return tuple(
        _texto_no_vacio(e, f"{contexto}[{i}]") for i, e in enumerate(elementos)
    )


def _ruta(valor: Any, raiz: Path, contexto: str) -> Path:
    """Resuelve una ruta del YAML contra la raíz del repositorio.

    Las rutas del `config.yaml` se declaran relativas a la raíz. Se rechazan
    las absolutas: harían la configuración dependiente de la máquina y
    romperían la reproducibilidad entre equipos.
    """
    texto = _texto_no_vacio(valor, contexto)
    ruta = Path(texto)
    if ruta.is_absolute():
        raise ConfiguracionInvalida(
            f"{contexto}: la ruta debe ser relativa a la raíz del repositorio, "
            f"se recibió la absoluta {texto!r}"
        )
    return (raiz / ruta).resolve()


# --- Bloques -----------------------------------------------------------------


def _leer_rutas(crudo: dict[str, Any], raiz: Path) -> Rutas:
    bloque = _exigir_mapa(crudo, "rutas")
    campos = {
        "datos_crudos",
        "datos_intermedios",
        "artefactos",
        "plantillas",
        "registro_inferencias",
        "manifiesto",
        "ficha_caracterizacion",
        "protocolo_evaluacion",
        "datasheet",
        "model_card",
        "reporte_cumplimiento",
    }
    _claves(bloque, campos, "rutas")
    return Rutas(
        **{c: _ruta(bloque[c], raiz, f"rutas.{c}") for c in campos}
    )


def _leer_datos(crudo: dict[str, Any], raiz: Path) -> ConfigDatos:
    bloque = _exigir_mapa(crudo, "datos")
    _claves(
        bloque,
        {
            "fuente",
            "archivo_crudo",
            "columna_objetivo",
            "columnas_sensor_pir",
            "particion",
        },
        "datos",
    )
    particion = _exigir_mapa(bloque["particion"], "datos.particion")
    _claves(particion, {"test_size", "estratificar"}, "datos.particion")

    test_size = _tipo(particion["test_size"], float, "datos.particion.test_size")
    if not 0.0 < test_size < 1.0:
        raise ConfiguracionInvalida(
            f"datos.particion.test_size: debe estar en (0, 1), se recibió "
            f"{test_size}"
        )

    # `columnas_sensor_pir` puede venir vacía: solo se puede completar tras
    # inspeccionar el dataset concreto. Quien consuma los datos es responsable
    # de exigirla no vacía; aquí sería prematuro.
    return ConfigDatos(
        fuente=_texto_no_vacio(bloque["fuente"], "datos.fuente"),
        archivo_crudo=_ruta(bloque["archivo_crudo"], raiz, "datos.archivo_crudo"),
        columna_objetivo=_texto_no_vacio(
            bloque["columna_objetivo"], "datos.columna_objetivo"
        ),
        columnas_sensor_pir=_lista_de_textos(
            bloque["columnas_sensor_pir"], "datos.columnas_sensor_pir"
        ),
        particion=ParticionDatos(
            test_size=test_size,
            estratificar=_tipo(
                particion["estratificar"], bool, "datos.particion.estratificar"
            ),
        ),
    )


def _leer_modelo(crudo: dict[str, Any]) -> ConfigModelo:
    bloque = _exigir_mapa(crudo, "modelo")
    _claves(bloque, {"tipo", "version", "hiperparametros"}, "modelo")
    return ConfigModelo(
        tipo=_texto_no_vacio(bloque["tipo"], "modelo.tipo"),
        version=_texto_no_vacio(bloque["version"], "modelo.version"),
        hiperparametros=dict(
            _exigir_mapa(bloque["hiperparametros"], "modelo.hiperparametros")
        ),
    )


def _leer_explicabilidad(crudo: dict[str, Any]) -> ConfigExplicabilidad:
    bloque = _exigir_mapa(crudo, "explicabilidad")
    _claves(
        bloque,
        {"explainer", "muestras_globales", "guardar_local_por_inferencia"},
        "explicabilidad",
    )
    muestras = _tipo(
        bloque["muestras_globales"], int, "explicabilidad.muestras_globales"
    )
    if muestras <= 0:
        raise ConfiguracionInvalida(
            f"explicabilidad.muestras_globales: debe ser > 0, se recibió "
            f"{muestras}"
        )
    return ConfigExplicabilidad(
        explainer=_texto_no_vacio(bloque["explainer"], "explicabilidad.explainer"),
        muestras_globales=muestras,
        guardar_local_por_inferencia=_tipo(
            bloque["guardar_local_por_inferencia"],
            bool,
            "explicabilidad.guardar_local_por_inferencia",
        ),
    )


def _leer_equidad(crudo: dict[str, Any]) -> ConfigEquidad:
    bloque = _exigir_mapa(crudo, "equidad")
    _claves(bloque, {"subgrupos", "umbrales"}, "equidad")

    crudos_subgrupos = _tipo(bloque["subgrupos"], list, "equidad.subgrupos")
    if not crudos_subgrupos:
        raise ConfiguracionInvalida(
            "equidad.subgrupos: debe declararse al menos un subgrupo de "
            "comparación; sin subgrupos no hay evaluación desagregada (R4.1)"
        )
    subgrupos = []
    vistos: set[str] = set()
    for i, s in enumerate(crudos_subgrupos):
        contexto = f"equidad.subgrupos[{i}]"
        mapa = _exigir_mapa(s, contexto)
        _claves(mapa, {"nombre", "columna", "categorias"}, contexto)
        nombre = _texto_no_vacio(mapa["nombre"], f"{contexto}.nombre")
        if nombre in vistos:
            raise ConfiguracionInvalida(
                f"{contexto}.nombre: {nombre!r} está duplicado; los nombres de "
                "subgrupo titulan las tablas del reporte de equidad"
            )
        vistos.add(nombre)
        subgrupos.append(
            Subgrupo(
                nombre=nombre,
                columna=_texto_no_vacio(mapa["columna"], f"{contexto}.columna"),
                # Lista vacía => las categorías se infieren de los datos.
                categorias=_lista_de_textos(
                    mapa["categorias"], f"{contexto}.categorias"
                ),
            )
        )

    umbrales_crudos = _exigir_mapa(bloque["umbrales"], "equidad.umbrales")
    if not umbrales_crudos:
        raise ConfiguracionInvalida(
            "equidad.umbrales: debe declararse al menos un umbral; el veredicto "
            "de equidad se emite contra umbrales pre-declarados (R4.2)"
        )
    umbrales: dict[str, float] = {}
    for nombre, valor in umbrales_crudos.items():
        contexto = f"equidad.umbrales.{nombre}"
        umbral = _tipo(valor, float, contexto)
        # La convención de nombres fija el rango válido, en vez de una lista de
        # métricas incrustada en el código: `_min` es un cociente, el resto son
        # diferencias absolutas.
        if nombre.endswith("_min"):
            if not 0.0 < umbral <= 1.0:
                raise ConfiguracionInvalida(
                    f"{contexto}: un cociente mínimo debe estar en (0, 1], se "
                    f"recibió {umbral}"
                )
        elif not 0.0 <= umbral <= 1.0:
            raise ConfiguracionInvalida(
                f"{contexto}: una diferencia debe estar en [0, 1], se recibió "
                f"{umbral}"
            )
        umbrales[nombre] = umbral

    return ConfigEquidad(subgrupos=tuple(subgrupos), umbrales=umbrales)


def _leer_trazabilidad(crudo: dict[str, Any]) -> ConfigTrazabilidad:
    bloque = _exigir_mapa(crudo, "trazabilidad")
    _claves(
        bloque,
        {"version_esquema", "formato", "responsable_por_defecto"},
        "trazabilidad",
    )
    return ConfigTrazabilidad(
        version_esquema=_texto_no_vacio(
            bloque["version_esquema"], "trazabilidad.version_esquema"
        ),
        formato=_texto_no_vacio(bloque["formato"], "trazabilidad.formato"),
        responsable_por_defecto=_texto_no_vacio(
            bloque["responsable_por_defecto"],
            "trazabilidad.responsable_por_defecto",
        ),
    )


# --- API pública ------------------------------------------------------------


def cargar_configuracion(ruta: str | Path = "config.yaml") -> Configuracion:
    """Lee y valida `config.yaml`, devolviendo una `Configuracion` inmutable.

    Las rutas declaradas en el YAML se resuelven contra el directorio que
    contiene el propio archivo, que es la raíz del repositorio. Así el
    resultado no depende del directorio de trabajo desde el que se invoque.

    Args:
        ruta: ubicación del archivo YAML de configuración.

    Returns:
        La configuración validada.

    Raises:
        FileNotFoundError: si `ruta` no existe.
        ConfiguracionInvalida: si falta una clave obligatoria, sobra una
            desconocida, o un valor es incoherente (p. ej. `test_size` fuera
            de (0, 1), umbral fuera de rango, subgrupo sin columna).
    """
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"no existe el archivo de configuración: {ruta}")

    texto = ruta.read_text(encoding="utf-8")
    try:
        crudo = yaml.safe_load(texto)
    except yaml.YAMLError as exc:
        raise ConfiguracionInvalida(f"{ruta}: YAML mal formado: {exc}") from exc

    crudo = _exigir_mapa(crudo, str(ruta))
    _claves(
        crudo,
        {
            "version_marco",
            "semilla",
            "determinismo",
            "rutas",
            "datos",
            "modelo",
            "explicabilidad",
            "equidad",
            "trazabilidad",
            "articulacion_normativa",
        },
        str(ruta),
    )

    raiz = ruta.resolve().parent

    semilla = _tipo(crudo["semilla"], int, "semilla")
    if semilla < 0:
        raise ConfiguracionInvalida(f"semilla: debe ser >= 0, se recibió {semilla}")

    determinismo = _exigir_mapa(crudo["determinismo"], "determinismo")
    _claves(determinismo, {"pythonhashseed", "n_jobs"}, "determinismo")
    n_jobs = _tipo(determinismo["n_jobs"], int, "determinismo.n_jobs")
    if n_jobs < 1:
        raise ConfiguracionInvalida(
            f"determinismo.n_jobs: debe ser >= 1, se recibió {n_jobs}"
        )

    articulacion_cruda = _exigir_mapa(
        crudo["articulacion_normativa"], "articulacion_normativa"
    )
    articulacion = {
        principio: {
            k: _texto_no_vacio(v, f"articulacion_normativa.{principio}.{k}")
            for k, v in _exigir_mapa(
                mapa, f"articulacion_normativa.{principio}"
            ).items()
        }
        for principio, mapa in articulacion_cruda.items()
    }

    return Configuracion(
        version_marco=_texto_no_vacio(crudo["version_marco"], "version_marco"),
        semilla=semilla,
        pythonhashseed=_tipo(
            determinismo["pythonhashseed"], int, "determinismo.pythonhashseed"
        ),
        n_jobs=n_jobs,
        rutas=_leer_rutas(crudo["rutas"], raiz),
        datos=_leer_datos(crudo["datos"], raiz),
        modelo=_leer_modelo(crudo["modelo"]),
        explicabilidad=_leer_explicabilidad(crudo["explicabilidad"]),
        equidad=_leer_equidad(crudo["equidad"]),
        trazabilidad=_leer_trazabilidad(crudo["trazabilidad"]),
        articulacion_normativa=articulacion,
        crudo=crudo,
    )


# Claves de hiperparámetro que fijan aleatoriedad. No es configuración del
# proyecto sino vocabulario de las librerías (scikit-learn, numpy), por eso
# vive en el código y no en `config.yaml`.
_CLAVES_ALEATORIEDAD = ("random_state", "random_seed", "seed")


def verificar_coherencia_semillas(config: Configuracion) -> None:
    """Comprueba que la semilla global coincide con todos los `random_state`
    declarados en la configuración (modelo, partición, etc.).

    Una semilla divergente es especialmente insidiosa: no rompe nada, solo
    hace que la corrida deje de ser reproducible en silencio, y eso invalida
    el manifiesto de evidencia sin que nadie se entere.

    Args:
        config: configuración ya cargada.

    Raises:
        ConfiguracionInvalida: si hay una discrepancia.
    """
    discrepancias = []
    for clave, valor in config.modelo.hiperparametros.items():
        if clave in _CLAVES_ALEATORIEDAD and valor != config.semilla:
            discrepancias.append(
                f"modelo.hiperparametros.{clave} = {valor!r}"
            )
    if config.pythonhashseed != config.semilla:
        discrepancias.append(
            f"determinismo.pythonhashseed = {config.pythonhashseed!r}"
        )
    if discrepancias:
        raise ConfiguracionInvalida(
            f"la semilla global es {config.semilla}, pero no coincide con: "
            + ", ".join(sorted(discrepancias))
        )


class ConfiguracionInvalida(ValueError):
    """La configuración existe pero es incompleta o incoherente."""
