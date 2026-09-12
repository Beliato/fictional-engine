"""Pruebas del orquestador y los 6 pasos."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

RAIZ_REPO = Path(__file__).resolve().parents[1]

from src.procedimiento.evidencia import EvidenciaIncompleta
import json
import shutil

import yaml

from src.comun.utilidades import hash_archivo
from src.equidad.reporte import tabla_protocolo
from src.procedimiento.orquestador import ejecutar_marco
from src.procedimiento.requerimientos import (
    REQUERIMIENTOS,
    verificar_cobertura_requerimientos,
)
from src.procedimiento.pasos import (
    PASOS,
    PRECONDICIONES,
    BitacoraExistente,
    PrecondicionIncumplida,
    nuevo_contexto,
    paso_1_caracterizacion_sistema,
    paso_2_documentacion_datos,
    paso_3_declaracion_criterios,
    paso_4_ejecucion_pruebas,
    paso_5_generacion_artefactos,
    paso_6_verificacion_auditabilidad,
    precondicion_preparar_datos,
    precondicion_sellar_modelo,
)
from src.trazabilidad.registro import leer_registros


def test_hay_exactamente_seis_pasos():
    """El procedimiento tiene 6 pasos, en el orden de la Tabla 9."""
    assert len(PASOS) == 6
    assert [p.__name__ for p in PASOS] == [
        "paso_1_caracterizacion_sistema",
        "paso_2_documentacion_datos",
        "paso_3_declaracion_criterios",
        "paso_4_ejecucion_pruebas",
        "paso_5_generacion_artefactos",
        "paso_6_verificacion_auditabilidad",
    ]


def test_preparacion_y_modelo_no_son_pasos_del_marco():
    """El modelo es sujeto de prueba, no objeto de optimización (Tabla 10).

    Preparar los datos y sellar el modelo son precondiciones: si alguna
    apareciera en `PASOS`, el marco estaría auditando su propio insumo.
    """
    assert [p.__name__ for p in PRECONDICIONES] == [
        "precondicion_preparar_datos",
        "precondicion_sellar_modelo",
    ]
    assert not set(PRECONDICIONES) & set(PASOS)


def test_cada_paso_declara_su_producto_y_funcion_nist():
    """Cada paso documenta su producto (Tabla 9) y su función del NIST AI RMF.

    La trazabilidad hacia el documento no es decorativa: el criterio de éxito
    del piloto es haber ejecutado el procedimiento de la Tabla 9.
    """
    for paso in PASOS:
        doc = paso.__doc__ or ""
        assert "Producto:" in doc, f"{paso.__name__} no declara su producto"
        assert "Función NIST AI RMF:" in doc, f"{paso.__name__} no declara función"
        assert "Requerimientos:" in doc, f"{paso.__name__} no declara requerimientos"


# --- Precondiciones y pasos 1 y 2 ---------------------------------------------


@pytest.fixture
def config_piloto(config, tmp_path, crudo_sintetico):
    """Config con crudo sintético y artefactos en `tmp_path`.

    Bosque chico: lo que se prueba es el procedimiento, no el desempeño.
    """
    crudo = tmp_path / "crudo.txt"
    crudo.write_text(crudo_sintetico(dias=12, eventos_por_dia=150), encoding="utf-8")
    artefactos = tmp_path / "artefactos"
    rutas = dataclasses.replace(
        config.rutas,
        artefactos=artefactos,
        ficha_caracterizacion=artefactos / "ficha_caracterizacion.md",
        datasheet=artefactos / "datasheet.md",
        protocolo_evaluacion=artefactos / "protocolo_evaluacion.md",
        registro_inferencias=artefactos / "bitacora" / "inferencias.jsonl",
    )
    datos = dataclasses.replace(config.datos, archivo_crudo=crudo)
    modelo = dataclasses.replace(
        config.modelo,
        hiperparametros={**config.modelo.hiperparametros, "n_estimators": 8},
    )
    return dataclasses.replace(config, rutas=rutas, datos=datos, modelo=modelo)


@pytest.fixture
def ctx_preparado(config_piloto):
    ctx = nuevo_contexto(config_piloto, "prueba-001")
    return precondicion_sellar_modelo(precondicion_preparar_datos(ctx))


def test_las_precondiciones_sellan_datos_y_modelo(ctx_preparado):
    """Dejan en el contexto lo que los artefactos tendrán que declarar."""
    ctx = ctx_preparado

    assert ctx.particion is not None and ctx.modelo is not None
    assert ctx.n_eventos_crudos > 0
    assert len(ctx.caracteristicas) > 0
    # Dos hashes distintos: origen y preparación se auditan por separado.
    assert len(ctx.hash_datos_crudos) == 64 and len(ctx.hash_datos) == 64
    assert ctx.hash_datos_crudos != ctx.hash_datos
    assert [e["paso"] for e in ctx.eventos] == [
        "precondicion_preparar_datos",
        "precondicion_sellar_modelo",
    ]


def test_sellar_el_modelo_exige_los_datos_preparados(config_piloto):
    """Sin partición no hay con qué entrenar: es un error de ejecución."""
    with pytest.raises(PrecondicionIncumplida, match="partición"):
        precondicion_sellar_modelo(nuevo_contexto(config_piloto, "prueba-001"))


def test_paso_1_genera_la_ficha_de_caracterizacion(ctx_preparado):
    ctx = paso_1_caracterizacion_sistema(ctx_preparado)
    ruta = ctx.artefactos["ficha_caracterizacion"]
    texto = ruta.read_text(encoding="utf-8")

    assert "{{" not in texto
    assert ctx.config.sistema.finalidad in texto
    assert ctx.config.trazabilidad.responsable_por_defecto in texto
    assert ctx.marca_inicio in texto
    assert ctx.eventos[-1]["paso"] == "paso_1_caracterizacion_sistema"
    assert len(ctx.eventos[-1]["hash"]) == 64


def test_paso_1_exige_el_modelo_sellado(config_piloto):
    """La ficha declara la versión del modelo evaluado; sin modelo, no hay
    sistema que caracterizar."""
    ctx = precondicion_preparar_datos(nuevo_contexto(config_piloto, "prueba-001"))

    with pytest.raises(EvidenciaIncompleta, match="modelo sellado"):
        paso_1_caracterizacion_sistema(ctx)


def test_paso_2_genera_el_datasheet_con_la_composicion_real(ctx_preparado):
    ctx = paso_2_documentacion_datos(ctx_preparado)
    texto = ctx.artefactos["datasheet"].read_text(encoding="utf-8")

    assert "{{" not in texto
    assert ctx.hash_datos_crudos in texto and ctx.hash_datos in texto
    assert "| Actividad | Ventanas | % |" in texto
    assert ctx.config.datos.documentacion.licencia in texto
    # La clase de los eventos sin anotar tiene que aparecer en la tabla.
    assert ctx.config.datos.actividades.etiqueta_sin_actividad in texto


def test_paso_2_exige_los_datos_preparados(config_piloto):
    ctx = nuevo_contexto(config_piloto, "prueba-001")

    with pytest.raises(EvidenciaIncompleta, match="características"):
        paso_2_documentacion_datos(ctx)


def test_los_artefactos_de_los_pasos_1_y_2_son_deterministas(ctx_preparado):
    """Con el mismo contexto, dos corridas producen los mismos bytes: el
    manifiesto compara hashes entre ejecuciones."""
    primera = [
        paso.__wrapped__(ctx_preparado)  # type: ignore[attr-defined]
        if hasattr(paso, "__wrapped__")
        else paso(ctx_preparado)
        for paso in (paso_1_caracterizacion_sistema, paso_2_documentacion_datos)
    ]
    bytes_primera = [
        list(ctx.artefactos.values())[-1].read_bytes() for ctx in primera
    ]
    segunda = [
        paso(ctx_preparado)
        for paso in (paso_1_caracterizacion_sistema, paso_2_documentacion_datos)
    ]
    bytes_segunda = [list(ctx.artefactos.values())[-1].read_bytes() for ctx in segunda]

    assert bytes_primera == bytes_segunda
    assert all(b"\r\n" not in contenido for contenido in bytes_primera)




# --- Paso 3: declaración de criterios -----------------------------------------


def test_paso_3_sella_el_hash_del_archivo_de_configuracion(ctx_preparado):
    """El hash es del archivo, no de la configuración ya cargada: un auditor
    lo reproduce con sha256sum sin ejecutar el marco (D13, D47)."""
    ctx = paso_3_declaracion_criterios(ctx_preparado)
    texto = ctx.artefactos["protocolo_evaluacion"].read_text(encoding="utf-8")

    assert ctx.hash_protocolo == hash_archivo(ctx.config.ruta_archivo)
    assert "{{" not in texto
    assert ctx.hash_protocolo in texto
    assert ctx.config.equidad.justificacion_umbrales in texto


def test_el_protocolo_declara_los_mismos_umbrales_que_el_reporte(ctx_preparado):
    """Una sola fuente para la tabla de umbrales: si divergieran, el
    expediente afirmaría dos protocolos distintos para la misma corrida."""
    ctx = paso_3_declaracion_criterios(ctx_preparado)
    texto = ctx.artefactos["protocolo_evaluacion"].read_text(encoding="utf-8")

    assert tabla_protocolo(ctx.config) in texto


# --- Paso 4: ejecución de las pruebas -----------------------------------------


@pytest.fixture
def ctx_probado(ctx_preparado):
    """Los cuatro primeros pasos, en orden: el 6 exige la evidencia de todos."""
    ctx = paso_1_caracterizacion_sistema(ctx_preparado)
    ctx = paso_2_documentacion_datos(ctx)
    return paso_4_ejecucion_pruebas(paso_3_declaracion_criterios(ctx))


def test_paso_4_ejecuta_las_tres_pruebas(ctx_probado):
    """Explicabilidad, equidad y trazabilidad sobre el mismo conjunto."""
    ctx = ctx_probado
    n = len(ctx.particion.X_prueba)

    assert len(ctx.explicaciones) == n
    assert len(ctx.ids_prueba) == n
    assert ctx.explicacion_global.n_explicaciones == n
    assert ctx.desempeno_equidad and ctx.veredicto_equidad is not None
    assert ctx.informe_bitacora.valido, ctx.informe_bitacora.problemas
    assert ctx.informe_cobertura.valido, ctx.informe_cobertura.problemas
    assert ctx.informe_bitacora.n_registros == n
    assert {
        "bitacora",
        "metricas_equidad",
        "explicaciones_locales",
    } <= ctx.artefactos.keys()


def test_la_bitacora_referencia_la_explicacion_de_cada_inferencia(ctx_probado):
    """R5.1: cada decisión registrada apunta a su atribución local."""
    registros = list(leer_registros(ctx_probado.artefactos["bitacora"]))

    assert [r.id_evento for r in registros] == list(ctx_probado.ids_prueba)
    for registro in registros:
        archivo, _, fragmento = registro.referencia_explicacion.partition("#")
        assert fragmento == registro.id_evento
        assert archivo.endswith(".jsonl")
        # La bitácora guarda el hash de la entrada, nunca los eventos.
        assert len(registro.referencia_entrada) == 64


def test_paso_4_no_reabre_una_bitacora_de_otra_corrida(ctx_probado):
    """Append-only (D5): dos corridas en un mismo archivo producirían ids
    duplicados y una evidencia que no corresponde a ninguna de las dos."""
    with pytest.raises(BitacoraExistente, match="arch"):
        paso_4_ejecucion_pruebas(ctx_probado)


def test_paso_4_exige_las_precondiciones(config_piloto):
    ctx = nuevo_contexto(config_piloto, "prueba-001")

    with pytest.raises(PrecondicionIncumplida, match="modelo sellado"):
        paso_4_ejecucion_pruebas(ctx)


# --- Pasos 5 y 6 --------------------------------------------------------------


@pytest.fixture
def ctx_documentado(ctx_probado):
    return paso_5_generacion_artefactos(ctx_probado)


def test_paso_5_genera_los_tres_artefactos_documentales(ctx_documentado):
    """Tabla 9: reporte de explicabilidad, reporte de equidad y model card."""
    ctx = ctx_documentado
    assert {
        "reporte_explicabilidad",
        "reporte_equidad",
        "model_card",
    } <= ctx.artefactos.keys()

    model_card = ctx.artefactos["model_card"].read_text(encoding="utf-8")
    assert "{{" not in model_card
    assert ctx.config.trazabilidad.responsable_por_defecto in model_card
    assert ctx.modelo.hash_parametros in model_card


def test_paso_5_exige_los_resultados_del_paso_4(ctx_preparado):
    with pytest.raises(PrecondicionIncumplida, match="paso 4"):
        paso_5_generacion_artefactos(ctx_preparado)


def test_paso_6_verifica_y_sella(ctx_documentado):
    """Comprueba el protocolo y la bitácora, documenta y recién después sella."""
    ctx = paso_6_verificacion_auditabilidad(ctx_documentado)

    assert ctx.hash_protocolo_verificado is True
    assert ctx.informe_bitacora.valido and ctx.informe_cobertura.valido
    assert {
        "bitacora_ejecucion",
        "reporte_cumplimiento",
        "manifiesto",
    } <= ctx.artefactos.keys()
    assert all(fila.cubierto for fila in ctx.cobertura_requerimientos), [
        fila.requerimiento.codigo
        for fila in ctx.cobertura_requerimientos
        if not fila.cubierto
    ]

    manifiesto = json.loads(ctx.artefactos["manifiesto"].read_text(encoding="utf-8"))
    assert manifiesto["protocolo"]["hash_verificado_en_paso_6"] is True
    assert len(manifiesto["requerimientos"]) == 9
    # El manifiesto sella cada artefacto ya escrito, incluido él mismo salvo
    # por su propia escritura posterior.
    assert manifiesto["artefactos"]["datasheet"]["sha256"] == hash_archivo(
        ctx.artefactos["datasheet"]
    )


def test_paso_6_detecta_un_protocolo_alterado(ctx_documentado):
    """Si el config cambió entre el paso 3 y el 6, la evidencia lo dice."""
    ctx = paso_6_verificacion_auditabilidad(
        dataclasses.replace(ctx_documentado, hash_protocolo="0" * 64)
    )

    assert ctx.hash_protocolo_verificado is False
    texto = ctx.artefactos["reporte_cumplimiento"].read_text(encoding="utf-8")
    assert "NO CUMPLE" in texto or "EVIDENCIA INCOMPLETA" in texto


def test_el_reporte_de_cumplimiento_declara_los_nueve_requerimientos(
    ctx_documentado,
):
    ctx = paso_6_verificacion_auditabilidad(ctx_documentado)
    texto = ctx.artefactos["reporte_cumplimiento"].read_text(encoding="utf-8")

    assert "{{" not in texto
    for requerimiento in REQUERIMIENTOS:
        assert requerimiento.codigo in texto


# --- Requerimientos -----------------------------------------------------------


def test_la_matriz_declara_los_nueve_requerimientos():
    codigos = [r.codigo for r in REQUERIMIENTOS]
    assert codigos == [
        "R3.1",
        "R3.2",
        "R3.3",
        "R4.1",
        "R4.2",
        "R4.3",
        "R5.1",
        "R5.2",
        "R5.3",
    ]


def test_sin_artefactos_ningun_requerimiento_queda_cubierto(tmp_path):
    """Una ruta anotada sin archivo detrás no es evidencia."""
    cobertura = verificar_cobertura_requerimientos({})
    assert not any(fila.cubierto for fila in cobertura)

    inexistente = {clave: tmp_path / "no-existe.md" for clave in ("datasheet",)}
    cobertura = verificar_cobertura_requerimientos(inexistente)
    por_codigo = {f.requerimiento.codigo: f for f in cobertura}
    assert not por_codigo["R4.3"].cubierto


# --- Orquestador --------------------------------------------------------------


def _config_en_disco(tmp_path, crudo_sintetico, nombre):
    """Copia el marco a un directorio temporal con su propio config.yaml.

    Las rutas del config se resuelven contra el directorio que lo contiene,
    así que esto aísla por completo la corrida.
    """
    raiz = tmp_path / nombre
    (raiz / "datos" / "crudos").mkdir(parents=True)
    (raiz / "datos" / "crudos" / "crudo.txt").write_text(
        crudo_sintetico(dias=12, eventos_por_dia=150), encoding="utf-8"
    )
    shutil.copytree(RAIZ_REPO / "plantillas", raiz / "plantillas")

    crudo = yaml.safe_load((RAIZ_REPO / "config.yaml").read_text(encoding="utf-8"))
    crudo["datos"]["archivo_crudo"] = "datos/crudos/crudo.txt"
    crudo["modelo"]["hiperparametros"]["n_estimators"] = 8
    ruta = raiz / "config.yaml"
    ruta.write_text(yaml.safe_dump(crudo, allow_unicode=True), encoding="utf-8")
    return ruta


@pytest.mark.integracion
@pytest.mark.lento
def test_el_pipeline_completo_genera_el_expediente(tmp_path, crudo_sintetico):
    """Precondiciones y seis pasos de punta a punta, como los corre el CLI."""
    resultado = ejecutar_marco(_config_en_disco(tmp_path, crudo_sintetico, "uno"))

    assert resultado.completado
    assert resultado.requerimientos_cubiertos is True
    assert resultado.ruta_manifiesto.is_file()
    # 0 solo si además la equidad aprueba; un hallazgo sale con 2, nunca con 1.
    assert resultado.codigo_salida in (0, 2)

    manifiesto = json.loads(resultado.ruta_manifiesto.read_text(encoding="utf-8"))
    assert manifiesto["id_ejecucion"] == resultado.id_ejecucion
    assert manifiesto["bitacora"]["valida"] is True
    assert all(r["cubierto"] for r in manifiesto["requerimientos"].values())


@pytest.mark.integracion
@pytest.mark.lento
def test_dos_corridas_producen_los_mismos_hashes_de_datos_y_modelo(
    tmp_path, crudo_sintetico
):
    """Los artefactos que no llevan la marca de la corrida son idénticos."""
    # Mismo identificador en las dos: lo que debe repetirse es el contenido,
    # no la identidad de la corrida (D46).
    primera = ejecutar_marco(
        _config_en_disco(tmp_path, crudo_sintetico, "uno"), "corrida-fija"
    )
    segunda = ejecutar_marco(
        _config_en_disco(tmp_path, crudo_sintetico, "dos"), "corrida-fija"
    )

    uno = json.loads(primera.ruta_manifiesto.read_text(encoding="utf-8"))
    dos = json.loads(segunda.ruta_manifiesto.read_text(encoding="utf-8"))

    assert uno["datos"] == dos["datos"]
    assert uno["modelo"] == dos["modelo"]
    assert uno["equidad"]["estado"] == dos["equidad"]["estado"]
    assert (
        uno["artefactos"]["datasheet"]["sha256"]
        == dos["artefactos"]["datasheet"]["sha256"]
    )
