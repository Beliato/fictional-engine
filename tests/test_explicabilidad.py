"""Pruebas de explicabilidad: atribución local y global, lenguaje llano y reporte."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import shap
import yaml

from src.comun import modelado as M
from src.comun.configuracion import ConfiguracionInvalida, cargar_configuracion
from src.comun.utilidades import PlantillaIncompleta, hash_archivo, rellenar_plantilla
from src.explicabilidad import atribucion_global as G
from src.explicabilidad import atribucion_local as L
from src.explicabilidad import reporte as R
from src.explicabilidad.lenguaje import describir_caracteristica, redactar_explicacion

RAIZ = Path(__file__).resolve().parents[1]
RESPONSABLE = "Miguel Méndez — Investigador responsable"


@pytest.fixture
def config_expl(config, tmp_path):
    """Config con artefactos en `tmp_path`, bosque chico y pocos puntos por
    gráfico: lo que se prueba es la mecánica, no el desempeño."""
    artefactos = tmp_path / "artefactos"
    rutas = dataclasses.replace(
        config.rutas,
        artefactos=artefactos,
        reporte_explicabilidad=artefactos / "reporte_explicabilidad.md",
    )
    modelo = dataclasses.replace(
        config.modelo,
        hiperparametros={**config.modelo.hiperparametros, "n_estimators": 8},
    )
    explicabilidad = dataclasses.replace(config.explicabilidad, muestras_graficos=40)
    return dataclasses.replace(
        config, rutas=rutas, modelo=modelo, explicabilidad=explicabilidad
    )


@pytest.fixture
def conjunto():
    """Tabla con los nombres de característica que produce `datos.py`."""
    rng = np.random.default_rng(0)
    n = 160
    X = pd.DataFrame(
        {
            "conteo_Kitchen": rng.integers(0, 12, n),
            "conteo_Bedroom": rng.integers(0, 12, n),
            "eventos_puerta": rng.integers(0, 3, n),
            "hora_del_dia": rng.integers(0, 24, n),
            "dia_semana": rng.integers(0, 7, n),
            "temp_T001": rng.normal(21, 1.5, n).round(1),
            "duracion_segundos": rng.uniform(30, 900, n).round(1),
        }
    )
    y = pd.Series(
        np.select(
            [
                X["conteo_Kitchen"] > X["conteo_Bedroom"] + 2,
                X["conteo_Bedroom"] > X["conteo_Kitchen"] + 2,
            ],
            ["Meal_Preparation", "Sleeping"],
            default="Relax",
        ),
        name="actividad",
    )
    ids = [f"evt-{i:04d}" for i in range(n)]
    return X, y, ids


@pytest.fixture
def entrenado(config_expl, conjunto):
    X, y, _ = conjunto
    modelo = M.entrenar(X, y, config_expl)
    return modelo, L.construir_explainer(modelo, config_expl)


@pytest.fixture
def explicaciones(config_expl, conjunto, entrenado):
    X, _, ids = conjunto
    modelo, explainer = entrenado
    return L.explicar_lote(explainer, modelo, X, ids, config_expl)


def _explicacion(contribuciones, valores=None, clase="Meal_Preparation", base=0.3):
    return L.ExplicacionLocal(
        id_evento="evt-x",
        clase_predicha=clase,
        valor_base=base,
        contribuciones=contribuciones,
        valores=valores or {k: 0.0 for k in contribuciones},
        ruta_artefacto=Path("no-importa.jsonl"),
    )


# --- Explainer ----------------------------------------------------------------


def test_construye_un_tree_explainer(entrenado):
    _, explainer = entrenado
    assert isinstance(explainer, shap.TreeExplainer)


def test_rechaza_un_explainer_distinto(config_expl, entrenado):
    modelo, _ = entrenado
    c = dataclasses.replace(
        config_expl,
        explicabilidad=dataclasses.replace(
            config_expl.explicabilidad, explainer="KernelExplainer"
        ),
    )
    with pytest.raises(ConfiguracionInvalida, match="TreeExplainer"):
        L.construir_explainer(modelo, c)


def test_la_perturbacion_intervencional_no_esta_implementada(config_expl, entrenado):
    """Declarada y aceptada por el cargador, pero rechazada explícitamente."""
    modelo, _ = entrenado
    c = dataclasses.replace(
        config_expl,
        explicabilidad=dataclasses.replace(
            config_expl.explicabilidad, perturbacion="interventional"
        ),
    )
    with pytest.raises(NotImplementedError, match="interventional"):
        L.construir_explainer(modelo, c)


# --- Atribución local (R3.1) --------------------------------------------------


def test_la_atribucion_reconstruye_la_probabilidad_predicha(
    conjunto, entrenado, explicaciones
):
    """base + Σ contribuciones = P(clase predicha): es la confianza registrada."""
    X, _, _ = conjunto
    modelo, _ = entrenado
    probabilidades = modelo.estimador.predict_proba(X)
    clases = [str(c) for c in modelo.estimador.classes_]
    for i, explicacion in enumerate(explicaciones):
        esperada = probabilidades[i][clases.index(explicacion.clase_predicha)]
        assert explicacion.salida_explicada == pytest.approx(esperada, abs=1e-9)


def test_la_clase_explicada_es_la_que_predice_el_modelo(
    conjunto, entrenado, explicaciones
):
    X, _, _ = conjunto
    modelo, _ = entrenado
    predichas = [str(p) for p in modelo.estimador.predict(X)]
    assert [e.clase_predicha for e in explicaciones] == predichas


def test_la_explicacion_es_determinista(config_expl, conjunto, entrenado):
    X, _, ids = conjunto
    modelo, explainer = entrenado
    a = L.calcular_explicaciones(explainer, modelo, X, ids, config_expl)
    b = L.calcular_explicaciones(explainer, modelo, X, ids, config_expl)
    assert a == b


def test_conserva_los_valores_observados(conjunto, explicaciones):
    X, _, _ = conjunto
    esperados = {c: float(v) for c, v in X.iloc[3].items()}
    assert explicaciones[3].valores == esperados


def test_top_ordena_por_magnitud_y_desempata_por_nombre():
    """Con contribuciones iguales, el orden no depende de las columnas."""
    explicacion = _explicacion({"b": 0.1, "a": -0.1, "c": 0.05})
    assert explicacion.caracteristicas_top(2) == [("a", -0.1), ("b", 0.1)]


@pytest.mark.parametrize("caso", ["duplicados", "longitud"])
def test_rechaza_ids_invalidos(config_expl, conjunto, entrenado, caso):
    X, _, ids = conjunto
    modelo, explainer = entrenado
    if caso == "duplicados":
        ids = ["evt-0000"] * len(ids)
        patron = "duplicados"
    else:
        ids = ids[:-1]
        patron = "filas"
    with pytest.raises(ValueError, match=patron):
        L.calcular_explicaciones(explainer, modelo, X, ids, config_expl)


# --- Artefacto consolidado ----------------------------------------------------


def test_escribe_una_linea_por_inferencia(conjunto, explicaciones):
    _, _, ids = conjunto
    ruta = explicaciones[0].ruta_artefacto
    lineas = ruta.read_text(encoding="utf-8").splitlines()

    assert [json.loads(linea)["id_evento"] for linea in lineas] == ids
    meta = json.loads(
        ruta.with_name("explicaciones.meta.json").read_text(encoding="utf-8")
    )
    assert meta["n_explicaciones"] == len(ids)
    assert meta["perturbacion"] == "tree_path_dependent"
    assert meta["version_shap"] == shap.__version__


def test_el_artefacto_es_identico_entre_corridas(
    config_expl, conjunto, entrenado, explicaciones
):
    X, _, ids = conjunto
    modelo, explainer = entrenado
    antes = hash_archivo(explicaciones[0].ruta_artefacto)
    L.explicar_lote(explainer, modelo, X, ids, config_expl)
    assert hash_archivo(explicaciones[0].ruta_artefacto) == antes


def test_referencia_y_lectura_ida_y_vuelta(config_expl, explicaciones):
    """El auditor parte de la bitácora y llega a la explicación (R5.3)."""
    explicacion = explicaciones[7]
    referencia = L.referencia_de(explicacion, config_expl)

    assert referencia == "artefactos/explicaciones/local/explicaciones.jsonl#evt-0007"
    assert L.leer_explicacion(referencia, config_expl) == explicacion


def test_leer_una_explicacion_inexistente(config_expl, explicaciones):
    referencia = L.referencia_de(explicaciones[0], config_expl).replace(
        "evt-0000", "evt-9999"
    )
    with pytest.raises(KeyError, match="evt-9999"):
        L.leer_explicacion(referencia, config_expl)


def test_leer_exige_la_forma_ruta_fragmento(config_expl):
    with pytest.raises(ValueError, match="ruta#id_evento"):
        L.leer_explicacion("artefactos/explicaciones/local/x.jsonl", config_expl)


# --- Integración con la trazabilidad ------------------------------------------


def _bitacora(config, explicaciones, referencia=None) -> Path:
    from src.trazabilidad.registro import RegistroEstructurado

    ruta = Path(config.rutas.artefactos) / "bitacora" / "inferencias.jsonl"
    RegistroEstructurado(ruta, config).registrar_lote(
        {
            "id_evento": e.id_evento,
            "referencia_entrada": "a" * 64,
            "salida_modelo": e.clase_predicha,
            "confianza": min(1.0, max(0.0, e.salida_explicada)),
            "referencia_explicacion": referencia or L.referencia_de(e, config),
            "responsable": RESPONSABLE,
        }
        for e in explicaciones
    )
    return ruta


def test_la_bitacora_verifica_contra_el_artefacto_consolidado(
    config_expl, explicaciones
):
    """Primera bitácora válida de extremo a extremo: sin explicaciones reales
    el verificador no podía aprobar ninguna."""
    from src.trazabilidad.verificacion import verificar_registro

    informe = verificar_registro(_bitacora(config_expl, explicaciones), config_expl)
    assert informe.valido, informe.problemas


def test_el_verificador_detecta_una_explicacion_ausente(config_expl, explicaciones):
    """Que el archivo exista no basta: el registro tiene que estar adentro."""
    from src.trazabilidad.verificacion import verificar_registro

    referencia = L.referencia_de(explicaciones[0], config_expl).replace(
        "evt-0000", "evt-9999"
    )
    bitacora = _bitacora(config_expl, explicaciones[:1], referencia=referencia)

    informe = verificar_registro(bitacora, config_expl)
    assert not informe.valido
    assert any("no está en" in p for p in informe.problemas)


def test_el_verificador_detecta_un_artefacto_ilegible(config_expl, explicaciones):
    from src.trazabilidad.verificacion import verificar_registro

    roto = Path(config_expl.rutas.artefactos) / "explicaciones" / "roto.jsonl"
    roto.write_text("esto no es json\n", encoding="utf-8")
    bitacora = _bitacora(
        config_expl,
        explicaciones[:1],
        referencia="artefactos/explicaciones/roto.jsonl#evt-0000",
    )

    informe = verificar_registro(bitacora, config_expl)
    assert not informe.valido
    assert any("no es un artefacto JSONL" in p for p in informe.problemas)


# --- Atribución global (R3.2) -------------------------------------------------


def test_la_importancia_global_es_la_media_de_las_locales(config_expl, explicaciones):
    """Coherencia por construcción: no hay un segundo cálculo SHAP."""
    global_ = G.calcular_importancia_global(explicaciones, config_expl)

    for nombre, valor in global_.importancia_media_abs.items():
        esperado = np.mean([abs(e.contribuciones[nombre]) for e in explicaciones])
        assert valor == pytest.approx(esperado)
    valores = list(global_.importancia_media_abs.values())
    assert valores == sorted(valores, reverse=True)
    assert global_.n_explicaciones == len(explicaciones)


def test_escribe_la_tabla_y_las_figuras(config_expl, explicaciones):
    global_ = G.calcular_importancia_global(explicaciones, config_expl)
    k = config_expl.explicabilidad.caracteristicas_destacadas

    tabla = json.loads(global_.ruta_tabla.read_text(encoding="utf-8"))
    assert [f["caracteristica"] for f in tabla["importancia"]] == list(
        global_.importancia_media_abs
    )
    assert list(global_.rutas_dependencias) == global_.top(k)
    for figura in [global_.ruta_figura_resumen, *global_.rutas_dependencias.values()]:
        assert figura.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_las_figuras_son_identicas_entre_corridas(config_expl, explicaciones):
    """El manifiesto las hashea: tienen que salir idénticas byte a byte."""
    primero = G.calcular_importancia_global(explicaciones, config_expl)
    figuras = [primero.ruta_figura_resumen, *primero.rutas_dependencias.values()]
    hashes = [hash_archivo(f) for f in figuras]

    G.calcular_importancia_global(explicaciones, config_expl)
    assert [hash_archivo(f) for f in figuras] == hashes


def test_el_muestreo_para_graficos_es_determinista_y_acotado(
    config_expl, explicaciones
):
    a = G.muestrear_para_graficos(explicaciones, config_expl)
    b = G.muestrear_para_graficos(explicaciones, config_expl)

    assert a == b
    assert len(a) == config_expl.explicabilidad.muestras_graficos
    ids = [e.id_evento for e in a]
    assert ids == sorted(ids)


def test_rechaza_agregar_sin_explicaciones(config_expl):
    with pytest.raises(ValueError, match="no hay explicaciones"):
        G.calcular_importancia_global([], config_expl)


# --- Lenguaje llano (R3.3) ----------------------------------------------------


def test_redacta_en_lenguaje_llano(config_expl):
    explicacion = _explicacion(
        {
            "conteo_Kitchen": 0.40,
            "hora_del_dia": 0.12,
            "conteo_Bedroom": -0.05,
            "eventos_puerta": 0.0,
        },
        {"conteo_Kitchen": 9, "hora_del_dia": 8, "conteo_Bedroom": 1, "eventos_puerta": 0},
    )
    texto = redactar_explicacion(explicacion, config_expl)

    assert "«Meal_Preparation»" in texto
    assert "77 %" in texto  # 0,30 + 0,40 + 0,12 − 0,05
    assert (
        "Pesó a favor: 9 activaciones de movimiento en la cocina y la hora "
        "del día (8 h)."
        in texto
    )
    assert "Pesó en contra: 1 activación de movimiento en el dormitorio." in texto
    assert "puerta" not in texto  # contribución nula, fuera de las destacadas


@pytest.mark.parametrize(
    ("nombre", "valor", "esperado"),
    [
        ("dia_semana", 5, "el día de la semana (sábado)"),
        ("duracion_segundos", 200, "una ventana de 3 min 20 s"),
        ("temp_T001", 21.46, "una temperatura de 21,5 °C en el sensor T001"),
        ("eventos_puerta", 1, "1 evento de puerta"),
    ],
)
def test_describe_cada_familia_de_caracteristicas(nombre, valor, esperado):
    assert describir_caracteristica(nombre, valor) == esperado


# --- Reporte ------------------------------------------------------------------


def test_el_reporte_rellena_toda_la_plantilla(config_expl, conjunto, explicaciones):
    _, y, ids = conjunto
    y_real = dict(zip(ids, y))
    global_ = G.calcular_importancia_global(explicaciones, config_expl)
    aciertos, errores = R.seleccionar_ejemplos(explicaciones, y_real, config_expl)

    ruta = R.generar_reporte_explicabilidad(
        global_, aciertos, errores, y_real, "prueba-001", config_expl
    )
    texto = ruta.read_text(encoding="utf-8")

    assert "{{" not in texto
    assert "prueba-001" in texto
    assert "| # | Característica |" in texto
    imagenes = re.findall(r"\]\(([^)]+\.png)\)", texto)
    assert imagenes
    for relativa in imagenes:
        assert (ruta.parent / relativa).is_file(), relativa


def test_la_seleccion_de_ejemplos_es_determinista(
    config_expl, conjunto, explicaciones
):
    _, y, ids = conjunto
    y_real = dict(zip(ids, y))
    n = config_expl.explicabilidad.ejemplos_por_tipo

    aciertos, errores = R.seleccionar_ejemplos(explicaciones, y_real, config_expl)
    assert (aciertos, errores) == R.seleccionar_ejemplos(
        explicaciones, y_real, config_expl
    )
    assert len(aciertos) <= n and len(errores) <= n
    assert all(y_real[e.id_evento] == e.clase_predicha for e in aciertos)
    assert all(y_real[e.id_evento] != e.clase_predicha for e in errores)


# --- Plantillas ---------------------------------------------------------------


def test_rellenar_plantilla_sustituye_los_marcadores():
    assert rellenar_plantilla("Hola {{ nombre }}", {"nombre": "Ana"}) == "Hola Ana"


def test_rellenar_plantilla_exige_todos_los_valores():
    with pytest.raises(PlantillaIncompleta, match="sin valor"):
        rellenar_plantilla("{{a}} y {{b}}", {"a": "1"})


def test_rellenar_plantilla_rechaza_valores_sobrantes():
    """Un valor que la plantilla no declara delata la plantilla equivocada."""
    with pytest.raises(PlantillaIncompleta, match="no declarados"):
        rellenar_plantilla("{{a}}", {"a": "1", "b": "2"})


def test_rellenar_plantilla_no_reexpande_los_valores():
    assert rellenar_plantilla("{{a}}", {"a": "{{b}}"}) == "{{b}}"


# --- Configuración ------------------------------------------------------------


def _config_con(tmp_path, **cambios):
    crudo = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    crudo["explicabilidad"].update(cambios)
    ruta = tmp_path / "config.yaml"
    ruta.write_text(yaml.safe_dump(crudo, allow_unicode=True), encoding="utf-8")
    return cargar_configuracion(ruta)


def test_la_config_del_repo_declara_tree_path_dependent(config):
    assert config.explicabilidad.perturbacion == "tree_path_dependent"


def test_rechaza_una_perturbacion_desconocida(tmp_path):
    with pytest.raises(ConfiguracionInvalida, match="perturbacion"):
        _config_con(tmp_path, perturbacion="aleatoria")


def test_rechaza_destacadas_no_positivas(tmp_path):
    with pytest.raises(ConfiguracionInvalida, match="caracteristicas_destacadas"):
        _config_con(tmp_path, caracteristicas_destacadas=0)


@pytest.mark.parametrize(
    ("nombre", "valor", "esperado"),
    [
        ("dia_semana", 3, "jueves"),
        ("hora_del_dia", 21, "21 h"),
        ("duracion_segundos", 286.1, "4 min 46 s"),
        ("temp_T001", 21.46, "21,5 °C"),
        ("conteo_Kitchen", 8, "8"),
    ],
)
def test_las_tablas_muestran_los_valores_en_sus_unidades(nombre, valor, esperado):
    """El R3.3 no se cumple a medias: si la frase dice «jueves», la tabla
    no puede decir «3»."""
    from src.explicabilidad.lenguaje import formatear_valor

    assert formatear_valor(nombre, valor) == esperado


def test_los_enunciados_no_filtran_identificadores_de_zona(config_expl):
    """La ENIA exige sistemas lingüísticamente apropiados (p. 32) y el R3.3,
    información comprensible: un identificador en inglés no lo es (D54)."""
    explicacion = _explicacion(
        {"conteo_Kitchen": 0.4, "conteo_Bedroom": -0.05},
        {"conteo_Kitchen": 9, "conteo_Bedroom": 1},
    )
    texto = redactar_explicacion(explicacion, config_expl)

    assert "Kitchen" not in texto and "Bedroom" not in texto


def test_una_zona_sin_traduccion_muestra_su_identificador():
    """Preferible a ocultar que falta: se ve en el reporte y se corrige."""
    from src.explicabilidad.lenguaje import etiqueta_caracteristica

    nombres = {"Kitchen": "la cocina"}
    assert etiqueta_caracteristica("conteo_Kitchen", nombres) == "Movimiento en la cocina"
    assert etiqueta_caracteristica("conteo_Attic", nombres) == "Movimiento en Attic"
    assert etiqueta_caracteristica("conteo_Kitchen") == "Movimiento en Kitchen"


def test_traducir_una_zona_inexistente_es_un_error(tmp_path):
    """Delata un nombre mal escrito; sin esto el reporte seguiría mostrando el
    identificador y nadie se enteraría."""
    import yaml

    from src.comun.configuracion import ConfiguracionInvalida, cargar_configuracion

    crudo = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    crudo["datos"]["nombres_zona"]["Altillo"] = "el altillo"
    ruta = tmp_path / "config.yaml"
    ruta.write_text(yaml.safe_dump(crudo, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ConfiguracionInvalida, match="Altillo"):
        cargar_configuracion(ruta)
