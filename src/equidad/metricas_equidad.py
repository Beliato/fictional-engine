"""Métricas de equidad y contraste contra umbrales PRE-DECLARADOS (R4.2).

Los umbrales, el soporte mínimo y el papel de cada métrica —decide o
describe— provienen exclusivamente de `config.equidad`, que el paso 3 sella
antes de calcular nada. Este módulo no expone ninguna forma de ajustarlos.

Protocolo (D42, D43):

- Cada actividad se evalúa contra el resto.
- Una tasa entra en la comparación solo si su denominador en la categoría
  llega a `soporte_minimo`.
- La disparidad es la diferencia entre la tasa máxima y la mínima de las
  categorías que entran (el cociente mínima/máxima, para
  `selection_rate_ratio`). Con menos de dos categorías, la combinación es no
  evaluable: se reporta como tal y nunca cuenta como aprobada.

Las tasas se calculan aquí, con conteos explícitos, y no con `fairlearn`, que
con etiquetas multiclase devuelve 0,0 en silencio para la paridad
demográfica (D43). Cada tasa conserva su numerador y su denominador para que
un auditor pueda rehacer la cuenta, y el contraste con el umbral se hace en
aritmética exacta (D45).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

import numpy as np

from src.comun.configuracion import METRICAS_EQUIDAD
from src.comun.utilidades import escribir_json
from src.equidad.desempeno_desagregado import DIRECTORIO
from src.equidad.entradas import categorias_de, validar_entradas

if TYPE_CHECKING:
    import pandas as pd

    from src.comun.configuracion import Configuracion, Subgrupo

ESTADOS_VEREDICTO = ("aprueba", "no_aprueba", "no_evaluable")
_ARCHIVO = "metricas_equidad.json"

# Tasas por categoría en que se apoya cada métrica, para una actividad `a`:
#   tvp:       ventanas cuya actividad real es `a`; cuenta si se predijo `a`.
#   tfp:       ventanas con otra actividad real; cuenta si se predijo `a`.
#   seleccion: todas las ventanas; cuenta si se predijo `a`.
TASAS_DE_METRICA = {
    "true_positive_rate_difference": ("tvp",),
    "false_positive_rate_difference": ("tfp",),
    "equalized_odds_difference": ("tvp", "tfp"),
    "demographic_parity_difference": ("seleccion",),
    "selection_rate_ratio": ("seleccion",),
}


@dataclass(frozen=True)
class TasaCategoria:
    """Una tasa de una categoría, con los conteos que la producen."""

    tasa: str
    categoria: str
    numerador: int
    denominador: int
    # False si el denominador no llega al soporte mínimo: la tasa se reporta,
    # pero no entra en la comparación.
    en_comparacion: bool

    @property
    def valor(self) -> float | None:
        return self.numerador / self.denominador if self.denominador else None


@dataclass(frozen=True)
class ResultadoMetrica:
    """Una métrica de equidad para una actividad (contra el resto) en un
    subgrupo."""

    metrica: str
    subgrupo: str
    actividad: str
    # "diferencia" o "cociente", según `METRICAS_EQUIDAD`.
    sentido: str
    # None: la métrica es descriptiva y no decide el veredicto.
    umbral: float | None
    # None: no evaluable; `motivo` dice por qué.
    valor_observado: float | None
    # None si la métrica no decide o no es evaluable.
    cumple: bool | None
    tasas: tuple[TasaCategoria, ...]
    motivo: str

    @property
    def decide(self) -> bool:
        return self.umbral is not None

    @property
    def evaluable(self) -> bool:
        return self.valor_observado is not None

    @property
    def estado(self) -> str:
        if not self.evaluable:
            return "no evaluable"
        if not self.decide:
            return "descriptiva"
        return "cumple" if self.cumple else "incumple"

    def a_diccionario(self) -> dict[str, Any]:
        return {**dataclasses.asdict(self), "estado": self.estado}


@dataclass(frozen=True)
class VeredictoEquidad:
    """Veredicto agregado del principio de equidad."""

    # Uno de `ESTADOS_VEREDICTO`.
    estado: str
    resultados: tuple[ResultadoMetrica, ...]

    @property
    def aprueba(self) -> bool:
        """Solo "aprueba" aprueba: un veredicto no evaluable no es un aprobado."""
        return self.estado == "aprueba"

    def que_deciden(self) -> list[ResultadoMetrica]:
        return [r for r in self.resultados if r.decide]

    def metricas_incumplidas(self) -> list[ResultadoMetrica]:
        return [r for r in self.resultados if r.cumple is False]

    def no_evaluables(self) -> list[ResultadoMetrica]:
        """Combinaciones que deciden y no llegaron a evaluarse."""
        return [r for r in self.que_deciden() if not r.evaluable]

    def descriptivas(self) -> list[ResultadoMetrica]:
        return [r for r in self.resultados if not r.decide]

    @property
    def cobertura(self) -> tuple[int, int]:
        """(evaluadas, posibles) entre las combinaciones que deciden."""
        deciden = self.que_deciden()
        return sum(r.evaluable for r in deciden), len(deciden)


def _tasas(
    tasa: str,
    actividad: str,
    reales: np.ndarray,
    predichas: np.ndarray,
    columna: np.ndarray,
    categorias: tuple[str, ...],
    soporte: int,
) -> tuple[TasaCategoria, ...]:
    predicha = predichas == actividad
    if tasa == "tvp":
        base = reales == actividad
    elif tasa == "tfp":
        base = reales != actividad
    else:
        base = np.ones(len(reales), dtype=bool)

    resultado = []
    for categoria in categorias:
        en_base = base & (columna == categoria)
        denominador = int(en_base.sum())
        resultado.append(
            TasaCategoria(
                tasa=tasa,
                categoria=categoria,
                numerador=int((en_base & predicha).sum()),
                denominador=denominador,
                en_comparacion=denominador >= soporte,
            )
        )
    return tuple(resultado)


def _disparidad(
    tasas: tuple[TasaCategoria, ...], sentido: str, soporte: int
) -> tuple[Fraction | None, str]:
    """Disparidad exacta entre las categorías que entran en la comparación,
    o None y el motivo por el que no se puede calcular."""
    comparables = [
        Fraction(t.numerador, t.denominador) for t in tasas if t.en_comparacion
    ]
    if len(comparables) < 2:
        return None, (
            f"menos de dos categorías con al menos {soporte} casos en el "
            "denominador"
        )
    if sentido == "diferencia":
        return max(comparables) - min(comparables), ""
    mayor = max(comparables)
    if mayor == 0:
        return None, "ninguna categoría comparable tiene predicciones de la actividad"
    return min(comparables) / mayor, ""


def _cumple(valor: Fraction, umbral: float, sentido: str) -> bool:
    # `Fraction(str(0.1))` es exactamente 1/10; `Fraction(0.1)` no lo es.
    limite = Fraction(str(umbral))
    return valor <= limite if sentido == "diferencia" else valor >= limite


def calcular_metricas_equidad(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    subgrupo: "Subgrupo",
    config: "Configuracion",
) -> list[ResultadoMetrica]:
    """Calcula para un subgrupo las métricas declaradas en `config.equidad`,
    una por actividad, y contrasta con su umbral las que deciden.

    Se evalúan las actividades que aparecen en las etiquetas reales o en las
    predicciones: una actividad que el modelo predice y nunca ocurre no tiene
    tasa de verdaderos positivos, pero sí de falsos positivos (D45).

    Raises:
        EntradasDesalineadas: si etiquetas, predicciones y sensibles no
            describen las mismas ventanas.
        CategoriaNoDeclarada: si los datos traen una categoría no declarada.
    """
    validar_entradas(y_verdadero, y_predicho, sensibles, subgrupo)
    reales = y_verdadero.astype(str).to_numpy()
    predichas = y_predicho.astype(str).to_numpy()
    columna_texto = sensibles[subgrupo.columna].astype(str)
    categorias = categorias_de(subgrupo, columna_texto)
    columna = columna_texto.to_numpy()
    soporte = config.equidad.soporte_minimo
    metricas: list[tuple[str, float | None]] = [
        *config.equidad.umbrales.items(),
        *((m, None) for m in config.equidad.descriptivas),
    ]

    resultados = []
    for actividad in sorted(set(reales) | set(predichas)):
        por_tasa: dict[str, tuple[TasaCategoria, ...]] = {}
        for metrica, umbral in metricas:
            sentido = METRICAS_EQUIDAD[metrica]
            componentes = []
            for tasa in TASAS_DE_METRICA[metrica]:
                if tasa not in por_tasa:
                    por_tasa[tasa] = _tasas(
                        tasa, actividad, reales, predichas, columna, categorias,
                        soporte,
                    )
                componentes.append(_disparidad(por_tasa[tasa], sentido, soporte))

            motivos = [motivo for valor, motivo in componentes if valor is None]
            valor = None if motivos else max(v for v, _ in componentes)
            resultados.append(
                ResultadoMetrica(
                    metrica=metrica,
                    subgrupo=subgrupo.nombre,
                    actividad=actividad,
                    sentido=sentido,
                    umbral=umbral,
                    valor_observado=None if valor is None else float(valor),
                    cumple=(
                        None
                        if valor is None or umbral is None
                        else _cumple(valor, umbral, sentido)
                    ),
                    tasas=tuple(
                        t for tasa in TASAS_DE_METRICA[metrica] for t in por_tasa[tasa]
                    ),
                    motivo=motivos[0] if motivos else "",
                )
            )
    return resultados


def emitir_veredicto(resultados: Sequence[ResultadoMetrica]) -> VeredictoEquidad:
    """Combina los resultados en un veredicto único (D43).

    - `aprueba`: toda combinación evaluable que decide respeta su umbral.
    - `no_aprueba`: alguna la excede.
    - `no_evaluable`: ninguna combinación que decide fue evaluable.

    No hay ponderaciones ni excepciones: las descriptivas no intervienen y las
    no evaluables no cuentan como aprobadas.
    """
    evaluables = [r for r in resultados if r.decide and r.evaluable]
    if not evaluables:
        estado = "no_evaluable"
    elif all(r.cumple for r in evaluables):
        estado = "aprueba"
    else:
        estado = "no_aprueba"
    return VeredictoEquidad(estado=estado, resultados=tuple(resultados))


def evaluar_equidad(
    y_verdadero: "pd.Series",
    y_predicho: "pd.Series",
    sensibles: "pd.DataFrame",
    config: "Configuracion",
) -> VeredictoEquidad:
    """Métricas de todos los subgrupos de `config.equidad` y su veredicto."""
    resultados = []
    for subgrupo in config.equidad.subgrupos:
        resultados += calcular_metricas_equidad(
            y_verdadero, y_predicho, sensibles, subgrupo, config
        )
    return emitir_veredicto(resultados)


def guardar_metricas(veredicto: VeredictoEquidad, config: "Configuracion") -> Path:
    """Escribe el veredicto y cada resultado, con sus conteos, en
    `artefactos/equidad/metricas_equidad.json` (JSON determinista)."""
    destino = Path(config.rutas.artefactos) / DIRECTORIO / _ARCHIVO
    evaluadas, posibles = veredicto.cobertura
    escribir_json(
        destino,
        {
            "estado": veredicto.estado,
            "soporte_minimo": config.equidad.soporte_minimo,
            "cobertura": {"evaluadas": evaluadas, "posibles": posibles},
            "resultados": [r.a_diccionario() for r in veredicto.resultados],
        },
    )
    return destino
