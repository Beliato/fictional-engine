"""Atribución local (R3.1): por qué el modelo produjo cada salida concreta.

Calcula, para cada inferencia del conjunto de evaluación, la contribución SHAP
de cada característica a la probabilidad de la clase predicha, y la guarda en
un único artefacto consolidado que la bitácora referencia por `id_evento`.

Propiedad que se aprovecha
--------------------------
En un bosque de scikit-learn, `TreeExplainer` explica la probabilidad de cada
clase, y la atribución es **exactamente aditiva**:

    valor_base(clase) + Σ contribuciones(clase) = P(clase | x)

Para la clase predicha, el lado derecho es la confianza que registra la
bitácora. Cada explicación trae así su propia prueba de coherencia: si no
suma, no corresponde a la inferencia que dice explicar. `calcular_explicaciones`
lo comprueba para todas antes de devolverlas.

Artefacto consolidado
---------------------
Una explicación por archivo serían tantos archivos como inferencias: más de
once mil en el piloto.
Se escribe un JSONL con una línea por inferencia, y la bitácora referencia
`<ruta>#<id_evento>`. El verificador de trazabilidad comprueba no solo que el
archivo exista, sino que el registro concreto esté adentro.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import numpy as np
import shap

from src.comun.configuracion import ConfiguracionInvalida
from src.comun.utilidades import asegurar_directorio, escribir_json

if TYPE_CHECKING:
    import pandas as pd

    from src.comun.configuracion import Configuracion
    from src.comun.modelado import ModeloSellado

_NOMBRE_ARTEFACTO = "explicaciones.jsonl"
_NOMBRE_METADATOS = "explicaciones.meta.json"

# Margen de la comprobación de aditividad: redondeo de coma flotante sobre una
# probabilidad. Es seis órdenes de magnitud menor que cualquier diferencia que
# el reporte llegue a mostrar, así que no es un parámetro de evaluación.
_TOLERANCIA_ADITIVIDAD = 1e-6


@dataclass(frozen=True)
class ExplicacionLocal:
    """Atribución SHAP de una única inferencia, para su clase predicha."""

    id_evento: str
    clase_predicha: str
    valor_base: float
    contribuciones: dict[str, float]  # característica -> contribución SHAP
    valores: dict[str, float]  # característica -> valor observado
    ruta_artefacto: Path

    @property
    def salida_explicada(self) -> float:
        """Probabilidad que reconstruye la atribución: base + Σ contribuciones.

        Por aditividad coincide con la confianza de la clase predicha, que es
        lo que la bitácora registra para esta inferencia.
        """
        return self.valor_base + sum(self.contribuciones.values())

    def caracteristicas_top(self, k: int = 5) -> list[tuple[str, float]]:
        """Las `k` características de mayor contribución absoluta.

        El desempate es por nombre: con contribuciones iguales, el orden no
        puede depender del orden de las columnas, o dos corridas equivalentes
        redactarían explicaciones distintas.
        """
        ordenadas = sorted(
            self.contribuciones.items(), key=lambda kv: (-abs(kv[1]), kv[0])
        )
        return ordenadas[:k]

    def a_diccionario(self) -> dict:
        """Forma serializable, sin la ruta (la da el propio artefacto)."""
        return {
            "id_evento": self.id_evento,
            "clase_predicha": self.clase_predicha,
            "valor_base": self.valor_base,
            "contribuciones": self.contribuciones,
            "valores": self.valores,
        }


def construir_explainer(
    modelo: "ModeloSellado", config: "Configuracion"
) -> "shap.TreeExplainer":
    """Crea el explainer declarado en `config.explicabilidad`.

    No pide datos de fondo: con `tree_path_dependent`, SHAP simula la ausencia
    de una característica siguiendo la cobertura de los propios árboles.

    Raises:
        ConfiguracionInvalida: si el explainer declarado no es TreeExplainer.
        NotImplementedError: si la perturbación declarada es `interventional`.
    """
    ajustes = config.explicabilidad
    if ajustes.explainer != "TreeExplainer":
        raise ConfiguracionInvalida(
            f"explicabilidad.explainer: {ajustes.explainer!r} no está "
            "soportado. El marco usa TreeExplainer, y es lo que justifica que "
            "modelado solo admita modelos de árbol."
        )
    if ajustes.perturbacion != "tree_path_dependent":
        raise NotImplementedError(
            f"explicabilidad.perturbacion {ajustes.perturbacion!r} todavía no "
            "está implementada: con un fondo de 100 filas cuesta unas 8 veces "
            "más que tree_path_dependent (unas 2,3 h sobre una prueba de once "
            "mil inferencias) y "
            "exige justificar el fondo elegido."
        )
    return shap.TreeExplainer(
        modelo.estimador, feature_perturbation="tree_path_dependent"
    )


def _matriz_shap(valores: object, n_clases: int) -> np.ndarray:
    """Normaliza la salida de shap a la forma (filas, características, clases).

    Según la versión y el número de clases, shap devuelve una lista con una
    matriz por clase o un único arreglo tridimensional.
    """
    if isinstance(valores, list):
        matriz = np.stack([np.asarray(v, dtype=float) for v in valores], axis=-1)
    else:
        matriz = np.asarray(valores, dtype=float)
    if matriz.ndim == 2:
        matriz = matriz[:, :, np.newaxis]
    if matriz.shape[-1] != n_clases:
        raise AtribucionIncoherente(
            f"shap devolvió {matriz.shape[-1]} salidas para un modelo de "
            f"{n_clases} clases"
        )
    return matriz


def _ruta_artefacto(config: "Configuracion") -> Path:
    return (
        Path(config.rutas.artefactos) / "explicaciones" / "local" / _NOMBRE_ARTEFACTO
    )


def calcular_explicaciones(
    explainer: "shap.TreeExplainer",
    modelo: "ModeloSellado",
    X: "pd.DataFrame",
    ids_evento: Iterable[str],
    config: "Configuracion",
) -> list[ExplicacionLocal]:
    """Calcula la atribución local de cada fila de `X`, sin escribir nada.

    Vectorizado: SHAP se calcula una sola vez sobre toda la matriz y luego se
    desglosa por fila. Cada explicación se comprueba contra la probabilidad
    que el modelo asigna a su clase predicha.

    Raises:
        ValueError: si `ids_evento` no aporta un id único por fila.
        AtribucionIncoherente: si alguna explicación no reconstruye la
            probabilidad de su clase predicha.
    """
    ids = [str(i) for i in ids_evento]
    if len(ids) != len(X):
        raise ValueError(f"hay {len(ids)} ids_evento para {len(X)} filas")
    if len(set(ids)) != len(ids):
        raise ValueError(
            "ids_evento contiene duplicados: cada inferencia debe poder "
            "referenciarse de forma inequívoca desde la bitácora"
        )
    if X.empty:
        return []

    estimador = modelo.estimador
    clases = [str(c) for c in estimador.classes_]
    probabilidades = estimador.predict_proba(X)
    predichas = probabilidades.argmax(axis=1)
    filas = np.arange(len(X))

    atribuciones = _matriz_shap(
        explainer.shap_values(X, check_additivity=True), len(clases)
    )
    base = np.atleast_1d(np.asarray(explainer.expected_value, dtype=float))
    # Contribuciones y valor base de la clase predicha de cada fila: (n, f).
    contribuciones = atribuciones[filas, :, predichas]
    base_predicha = base[predichas]

    reconstruida = base_predicha + contribuciones.sum(axis=1)
    esperada = probabilidades[filas, predichas]
    desvio = np.abs(reconstruida - esperada)
    if desvio.max() > _TOLERANCIA_ADITIVIDAD:
        peor = int(desvio.argmax())
        raise AtribucionIncoherente(
            f"la explicación de {ids[peor]!r} reconstruye "
            f"{reconstruida[peor]:.6f}, pero el modelo asigna "
            f"{esperada[peor]:.6f} a {clases[predichas[peor]]!r}"
        )

    columnas = [str(c) for c in X.columns]
    valores = X.to_numpy(dtype=float)
    ruta = _ruta_artefacto(config)
    return [
        ExplicacionLocal(
            id_evento=ids[i],
            clase_predicha=clases[predichas[i]],
            valor_base=float(base_predicha[i]),
            contribuciones=dict(zip(columnas, map(float, contribuciones[i]))),
            valores=dict(zip(columnas, map(float, valores[i]))),
            ruta_artefacto=ruta,
        )
        for i in range(len(X))
    ]


def guardar_explicaciones(
    explicaciones: list[ExplicacionLocal],
    modelo: "ModeloSellado",
    config: "Configuracion",
) -> Path:
    """Escribe el artefacto consolidado y sus metadatos. Sobrescribe.

    A diferencia de la bitácora, este artefacto no se acumula: es el de esta
    corrida. Una línea por inferencia, claves ordenadas y fin de línea LF,
    para que dos corridas equivalentes produzcan archivos idénticos byte a
    byte y el manifiesto pueda compararlos por hash.
    """
    ruta = _ruta_artefacto(config)
    asegurar_directorio(ruta.parent)
    with ruta.open("w", encoding="utf-8", newline="\n") as f:
        for explicacion in explicaciones:
            f.write(
                json.dumps(
                    explicacion.a_diccionario(), ensure_ascii=False, sort_keys=True
                )
            )
            f.write("\n")
    escribir_json(
        ruta.with_name(_NOMBRE_METADATOS),
        {
            "explainer": config.explicabilidad.explainer,
            "perturbacion": config.explicabilidad.perturbacion,
            "version_shap": shap.__version__,
            "version_modelo": modelo.version,
            "hash_parametros_modelo": modelo.hash_parametros,
            "n_explicaciones": len(explicaciones),
            "salida_explicada": "probabilidad de la clase predicha",
        },
    )
    return ruta


def explicar_lote(
    explainer: "shap.TreeExplainer",
    modelo: "ModeloSellado",
    X: "pd.DataFrame",
    ids_evento: Iterable[str],
    config: "Configuracion",
) -> list[ExplicacionLocal]:
    """Calcula las explicaciones de `X` y escribe el artefacto consolidado."""
    explicaciones = calcular_explicaciones(explainer, modelo, X, ids_evento, config)
    guardar_explicaciones(explicaciones, modelo, config)
    return explicaciones


def referencia_de(explicacion: ExplicacionLocal, config: "Configuracion") -> str:
    """Referencia `ruta#id_evento` que la bitácora registra (Tabla 8).

    Relativa a la raíz del repositorio y con separadores POSIX, para que la
    bitácora siga siendo verificable al moverla de máquina o de sistema.
    """
    raiz = Path(config.rutas.artefactos).parent
    relativa = explicacion.ruta_artefacto.relative_to(raiz).as_posix()
    return f"{relativa}#{explicacion.id_evento}"


def leer_explicacion(referencia: str, config: "Configuracion") -> ExplicacionLocal:
    """Recupera una explicación a partir de su referencia `ruta#id_evento`.

    Es la operación que necesita un auditor para el R5.3: tomar una línea de
    la bitácora y reconstruir por qué el sistema decidió lo que decidió.

    Raises:
        ValueError: si la referencia no tiene la forma `ruta#id_evento`.
        FileNotFoundError: si el artefacto no existe.
        KeyError: si el artefacto no contiene ese `id_evento`.
    """
    archivo, separador, id_evento = referencia.partition("#")
    if not separador or not id_evento:
        raise ValueError(
            f"la referencia {referencia!r} no tiene la forma ruta#id_evento"
        )
    ruta = Path(archivo)
    if not ruta.is_absolute():
        ruta = Path(config.rutas.artefactos).parent / ruta

    with ruta.open("r", encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            datos = json.loads(linea)
            if datos.get("id_evento") == id_evento:
                return ExplicacionLocal(
                    id_evento=datos["id_evento"],
                    clase_predicha=datos["clase_predicha"],
                    valor_base=datos["valor_base"],
                    contribuciones=datos["contribuciones"],
                    valores=datos["valores"],
                    ruta_artefacto=ruta,
                )
    raise KeyError(f"{ruta.name} no contiene la explicación {id_evento!r}")


class AtribucionIncoherente(RuntimeError):
    """Una atribución no reconstruye la salida del modelo que dice explicar."""
