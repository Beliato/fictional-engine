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


# Estrategias de partición admitidas. `temporal_por_dia` reserva los últimos
# días para prueba; `aleatoria_estratificada` reparte filas al azar, lo que
# sobre eventos autocorrelacionados produce fuga temporal y exactitud
# optimista. Se admite la segunda solo para poder contrastar el efecto.
ESTRATEGIAS_PARTICION = ("temporal_por_dia", "aleatoria_estratificada")


@dataclass(frozen=True)
class ParticionDatos:
    estrategia: str
    test_size: float


@dataclass(frozen=True)
class FranjaHoraria:
    """Un tramo del día, por su hora de inicio inclusive."""

    desde: int
    nombre: str


@dataclass(frozen=True)
class ConfigVentana:
    n_eventos: int


@dataclass(frozen=True)
class ConfigActividades:
    etiqueta_sin_actividad: str
    excluidas: tuple[str, ...]


@dataclass(frozen=True)
class ConfigDatos:
    fuente: str
    archivo_crudo: Path
    formato: str
    columna_objetivo: str
    columnas_sensor_pir: tuple[str, ...]
    sensores_puerta: tuple[str, ...]
    sensores_temperatura: tuple[str, ...]
    zonas: dict[str, str]
    actividades: ConfigActividades
    franjas_horarias: tuple[FranjaHoraria, ...]
    ventana: ConfigVentana
    particion: ParticionDatos

    def zona_de(self, sensor: str) -> str | None:
        """Zona del hogar donde está `sensor`, o None si no está mapeado."""
        return self.zonas.get(sensor)

    @property
    def zonas_distintas(self) -> tuple[str, ...]:
        """Zonas presentes, en orden estable (define el orden de columnas)."""
        return tuple(sorted(set(self.zonas.values())))


@dataclass(frozen=True)
class ConfigModelo:
    tipo: str
    version: str
    hiperparametros: dict[str, Any]


# Cómo simula SHAP la ausencia de una característica. Ambos métodos los define
# Lundberg et al. (2020); ver `explicabilidad.perturbacion` en config.yaml.
PERTURBACIONES = ("tree_path_dependent", "interventional")


@dataclass(frozen=True)
class ConfigExplicabilidad:
    explainer: str
    perturbacion: str
    guardar_local_por_inferencia: bool
    muestras_graficos: int
    caracteristicas_destacadas: int
    ejemplos_por_tipo: int


@dataclass(frozen=True)
class Subgrupo:
    nombre: str
    columna: str
    categorias: tuple[str, ...]


# Métricas de equidad que el marco sabe calcular, con el sentido en que se
# cumplen. El catálogo dice qué se PUEDE medir; `config.yaml` decide qué se
# mide y qué decide el veredicto. Un nombre fuera del catálogo es un error: si
# no, una métrica mal escrita no se calcularía y el veredicto aprobaría sin
# haberla medido (D44).
#   diferencia: cumple si valor <= umbral; el umbral va en [0, 1].
#   cociente:   cumple si valor >= umbral; el umbral va en (0, 1].
METRICAS_EQUIDAD = {
    "true_positive_rate_difference": "diferencia",
    "false_positive_rate_difference": "diferencia",
    "equalized_odds_difference": "diferencia",
    "demographic_parity_difference": "diferencia",
    "selection_rate_ratio": "cociente",
}


@dataclass(frozen=True)
class ConfigEquidad:
    subgrupos: tuple[Subgrupo, ...]
    # Casos mínimos en el denominador de una tasa para compararla (D43).
    soporte_minimo: int
    # Métrica -> umbral. Solo estas deciden el veredicto (D42).
    umbrales: dict[str, float]
    # Se calculan y se reportan, sin umbral ni peso en el veredicto.
    descriptivas: tuple[str, ...]


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
    reporte_explicabilidad: Path
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
        "reporte_explicabilidad",
        "reporte_cumplimiento",
    }
    _claves(bloque, campos, "rutas")
    return Rutas(
        **{c: _ruta(bloque[c], raiz, f"rutas.{c}") for c in campos}
    )


def _leer_franjas(crudo: Any) -> tuple[FranjaHoraria, ...]:
    """Lee y valida los cortes horarios que definen `franja_horaria`.

    Se exige que cubran el día entero empezando en 0 y que los cortes sean
    estrictamente ascendentes. Un hueco dejaría horas sin franja, y una fila
    sin subgrupo desaparecería del análisis desagregado sin que nadie lo note.
    """
    elementos = _tipo(crudo, list, "datos.franjas_horarias")
    if not elementos:
        raise ConfiguracionInvalida(
            "datos.franjas_horarias: debe declararse al menos una franja"
        )

    franjas: list[FranjaHoraria] = []
    nombres: set[str] = set()
    for i, elemento in enumerate(elementos):
        contexto = f"datos.franjas_horarias[{i}]"
        mapa = _exigir_mapa(elemento, contexto)
        _claves(mapa, {"desde", "nombre"}, contexto)
        desde = _tipo(mapa["desde"], int, f"{contexto}.desde")
        if not 0 <= desde <= 23:
            raise ConfiguracionInvalida(
                f"{contexto}.desde: debe estar en [0, 23], se recibió {desde}"
            )
        nombre = _texto_no_vacio(mapa["nombre"], f"{contexto}.nombre")
        if nombre in nombres:
            raise ConfiguracionInvalida(
                f"{contexto}.nombre: {nombre!r} está duplicado"
            )
        if franjas and desde <= franjas[-1].desde:
            raise ConfiguracionInvalida(
                f"{contexto}.desde: los cortes deben ser ascendentes; "
                f"{desde} no es mayor que {franjas[-1].desde}"
            )
        nombres.add(nombre)
        franjas.append(FranjaHoraria(desde=desde, nombre=nombre))

    if franjas[0].desde != 0:
        raise ConfiguracionInvalida(
            f"datos.franjas_horarias: la primera franja debe empezar en 0, "
            f"empieza en {franjas[0].desde}; las horas anteriores quedarían "
            "sin franja"
        )
    return tuple(franjas)


def _leer_datos(crudo: dict[str, Any], raiz: Path) -> ConfigDatos:
    bloque = _exigir_mapa(crudo, "datos")
    _claves(
        bloque,
        {
            "fuente",
            "archivo_crudo",
            "formato",
            "columna_objetivo",
            "columnas_sensor_pir",
            "sensores_puerta",
            "sensores_temperatura",
            "zonas",
            "actividades",
            "franjas_horarias",
            "ventana",
            "particion",
        },
        "datos",
    )

    franjas = _leer_franjas(bloque["franjas_horarias"])

    particion = _exigir_mapa(bloque["particion"], "datos.particion")
    _claves(particion, {"estrategia", "test_size"}, "datos.particion")
    estrategia = _texto_no_vacio(
        particion["estrategia"], "datos.particion.estrategia"
    )
    if estrategia not in ESTRATEGIAS_PARTICION:
        raise ConfiguracionInvalida(
            f"datos.particion.estrategia: {estrategia!r} no es una estrategia "
            f"conocida; use una de {list(ESTRATEGIAS_PARTICION)}"
        )
    test_size = _tipo(particion["test_size"], float, "datos.particion.test_size")
    if not 0.0 < test_size < 1.0:
        raise ConfiguracionInvalida(
            f"datos.particion.test_size: debe estar en (0, 1), se recibió "
            f"{test_size}"
        )

    ventana = _exigir_mapa(bloque["ventana"], "datos.ventana")
    _claves(ventana, {"n_eventos"}, "datos.ventana")
    n_eventos = _tipo(ventana["n_eventos"], int, "datos.ventana.n_eventos")
    if n_eventos < 2:
        raise ConfiguracionInvalida(
            f"datos.ventana.n_eventos: debe ser >= 2, se recibió {n_eventos}"
        )

    actividades = _exigir_mapa(bloque["actividades"], "datos.actividades")
    _claves(
        actividades,
        {"etiqueta_sin_actividad", "excluidas"},
        "datos.actividades",
    )

    zonas_crudas = _exigir_mapa(bloque["zonas"], "datos.zonas")
    if not zonas_crudas:
        raise ConfiguracionInvalida(
            "datos.zonas: el mapeo sensor -> zona no puede estar vacío; sin él "
            "las explicaciones nombran sensores en vez de lugares (R3.3)"
        )
    zonas = {
        _texto_no_vacio(s, "datos.zonas (clave)"): _texto_no_vacio(
            z, f"datos.zonas.{s}"
        )
        for s, z in zonas_crudas.items()
    }

    pir = _lista_de_textos(
        bloque["columnas_sensor_pir"], "datos.columnas_sensor_pir"
    )
    # Un sensor PIR sin zona produciría una característica anónima en el
    # reporte de explicabilidad, que es justo lo que el R3.3 quiere evitar.
    sin_zona = [s for s in pir if s not in zonas]
    if sin_zona:
        raise ConfiguracionInvalida(
            f"datos.zonas: faltan zonas para los sensores PIR {sin_zona}"
        )

    return ConfigDatos(
        fuente=_texto_no_vacio(bloque["fuente"], "datos.fuente"),
        archivo_crudo=_ruta(bloque["archivo_crudo"], raiz, "datos.archivo_crudo"),
        formato=_texto_no_vacio(bloque["formato"], "datos.formato"),
        columna_objetivo=_texto_no_vacio(
            bloque["columna_objetivo"], "datos.columna_objetivo"
        ),
        franjas_horarias=franjas,
        columnas_sensor_pir=pir,
        sensores_puerta=_lista_de_textos(
            bloque["sensores_puerta"], "datos.sensores_puerta"
        ),
        sensores_temperatura=_lista_de_textos(
            bloque["sensores_temperatura"], "datos.sensores_temperatura"
        ),
        zonas=zonas,
        actividades=ConfigActividades(
            etiqueta_sin_actividad=_texto_no_vacio(
                actividades["etiqueta_sin_actividad"],
                "datos.actividades.etiqueta_sin_actividad",
            ),
            excluidas=_lista_de_textos(
                actividades["excluidas"], "datos.actividades.excluidas"
            ),
        ),
        ventana=ConfigVentana(n_eventos=n_eventos),
        particion=ParticionDatos(estrategia=estrategia, test_size=test_size),
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
        {
            "explainer",
            "perturbacion",
            "guardar_local_por_inferencia",
            "muestras_graficos",
            "caracteristicas_destacadas",
            "ejemplos_por_tipo",
        },
        "explicabilidad",
    )
    perturbacion = _texto_no_vacio(
        bloque["perturbacion"], "explicabilidad.perturbacion"
    )
    if perturbacion not in PERTURBACIONES:
        raise ConfiguracionInvalida(
            f"explicabilidad.perturbacion: {perturbacion!r} no es un método "
            f"conocido; use uno de {list(PERTURBACIONES)}"
        )

    def _positivo(clave: str) -> int:
        valor = _tipo(bloque[clave], int, f"explicabilidad.{clave}")
        if valor <= 0:
            raise ConfiguracionInvalida(
                f"explicabilidad.{clave}: debe ser > 0, se recibió {valor}"
            )
        return valor

    return ConfigExplicabilidad(
        explainer=_texto_no_vacio(bloque["explainer"], "explicabilidad.explainer"),
        perturbacion=perturbacion,
        guardar_local_por_inferencia=_tipo(
            bloque["guardar_local_por_inferencia"],
            bool,
            "explicabilidad.guardar_local_por_inferencia",
        ),
        muestras_graficos=_positivo("muestras_graficos"),
        caracteristicas_destacadas=_positivo("caracteristicas_destacadas"),
        ejemplos_por_tipo=_positivo("ejemplos_por_tipo"),
    )


def _sentido_metrica(nombre: Any, contexto: str) -> str:
    """Sentido de cumplimiento de una métrica del catálogo (D44)."""
    if nombre not in METRICAS_EQUIDAD:
        raise ConfiguracionInvalida(
            f"{contexto}: {nombre!r} no es una métrica de equidad conocida; use "
            f"una de {sorted(METRICAS_EQUIDAD)}"
        )
    return METRICAS_EQUIDAD[nombre]


def _leer_equidad(crudo: dict[str, Any]) -> ConfigEquidad:
    bloque = _exigir_mapa(crudo, "equidad")
    _claves(
        bloque,
        {"subgrupos", "soporte_minimo", "umbrales", "descriptivas"},
        "equidad",
    )

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

    soporte_minimo = _tipo(bloque["soporte_minimo"], int, "equidad.soporte_minimo")
    if soporte_minimo <= 0:
        raise ConfiguracionInvalida(
            f"equidad.soporte_minimo: debe ser > 0, se recibió {soporte_minimo}"
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
        sentido = _sentido_metrica(nombre, contexto)
        umbral = _tipo(valor, float, contexto)
        if sentido == "cociente":
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

    descriptivas = _lista_de_textos(bloque["descriptivas"], "equidad.descriptivas")
    for i, nombre in enumerate(descriptivas):
        contexto = f"equidad.descriptivas[{i}]"
        _sentido_metrica(nombre, contexto)
        if nombre in umbrales:
            raise ConfiguracionInvalida(
                f"{contexto}: {nombre!r} ya tiene umbral en equidad.umbrales; "
                "una métrica decide el veredicto o se reporta como descriptiva, "
                "no ambas"
            )
    repetidas = sorted({n for n in descriptivas if descriptivas.count(n) > 1})
    if repetidas:
        raise ConfiguracionInvalida(
            f"equidad.descriptivas: {repetidas} aparece(n) repetida(s)"
        )

    return ConfigEquidad(
        subgrupos=tuple(subgrupos),
        soporte_minimo=soporte_minimo,
        umbrales=umbrales,
        descriptivas=descriptivas,
    )


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

    config = Configuracion(
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
    _verificar_coherencia_entre_bloques(config)
    return config


def _verificar_coherencia_entre_bloques(config: "Configuracion") -> None:
    """Comprueba acuerdos que cruzan más de un bloque del YAML.

    Cada bloque puede ser válido por separado y el conjunto ser incoherente.
    Estas discrepancias no rompen nada al cargar: reaparecen como una tabla
    vacía o una categoría ausente en el reporte de equidad, ya tarde.
    """
    nombres_franja = {f.nombre for f in config.datos.franjas_horarias}
    for subgrupo in config.equidad.subgrupos:
        if subgrupo.columna != "franja_horaria" or not subgrupo.categorias:
            continue
        declaradas = set(subgrupo.categorias)
        if declaradas != nombres_franja:
            raise ConfiguracionInvalida(
                f"equidad.subgrupos[{subgrupo.nombre}].categorias "
                f"{sorted(declaradas)} no coincide con los nombres de "
                f"datos.franjas_horarias {sorted(nombres_franja)}"
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
