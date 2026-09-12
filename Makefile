# =============================================================================
# Comandos del marco operativo de cumplimiento.
# Ejecución determinista: PYTHONHASHSEED se fija de forma explícita.
# =============================================================================

VENV        ?= .venv
PY          := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
CONFIG      ?= config.yaml
DIAS        ?= 20
export PYTHONHASHSEED := 42

.DEFAULT_GOAL := help

.PHONY: help setup lock test pipeline demo clean clean-datos verificar-registro

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Crea el venv e instala las dependencias fijadas
	./scripts/setup.sh

lock: ## Congela el cierre transitivo de dependencias en requirements.lock
	$(PIP) freeze --exclude-editable > requirements.lock
	@echo "==> requirements.lock actualizado. Versiónelo en git."

test: ## Ejecuta la batería de pruebas
	$(PY) -m pytest

# El orquestador devuelve 2 cuando hay hallazgos (equidad que no aprueba o
# evidencia incompleta). Eso no es un fallo de ejecución, así que make no debe
# tratarlo como error; 1 sí lo es y hace fallar el target.
pipeline: ## Ejecuta el marco completo (6 pasos) usando $(CONFIG)
	@$(PY) -m src.procedimiento.orquestador --config $(CONFIG); \
	 codigo=$$?; \
	 echo "==> código de salida: $$codigo (2 = hallazgos; 1 = error)"; \
	 [ $$codigo -ne 1 ]

demo: ## Corrida de demostración: los 6 pasos sobre $(DIAS) días, en minutos
	$(PY) scripts/preparar_demo.py $(DIAS)
	@$(PY) -m src.procedimiento.orquestador --config config.demo.yaml --id demo; \
	 codigo=$$?; \
	 echo "==> código de salida: $$codigo (2 = hallazgos; 1 = error)"; \
	 echo "==> artefactos de la demo en artefactos/demo/"; \
	 [ $$codigo -ne 1 ]

verificar-registro: ## Verifica integridad y completitud de la bitácora de inferencias
	$(PY) -m src.trazabilidad.verificacion --config $(CONFIG)

clean: ## Elimina artefactos generados y caches (conserva datos)
	rm -rf artefactos/*
	mkdir -p artefactos/bitacora
	touch artefactos/.gitkeep artefactos/bitacora/.gitkeep
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

clean-datos: ## Elimina datos intermedios (NO toca datos/crudos)
	rm -rf datos/intermedios/*
	touch datos/intermedios/.gitkeep
