# =============================================================================
# Comandos del marco operativo de cumplimiento.
# Ejecución determinista: PYTHONHASHSEED se fija de forma explícita.
# =============================================================================

VENV        ?= .venv
PY          := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
CONFIG      ?= config.yaml
export PYTHONHASHSEED := 42

.DEFAULT_GOAL := help

.PHONY: help setup lock test pipeline clean clean-datos verificar-registro

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

pipeline: ## Ejecuta el marco completo (6 pasos) usando $(CONFIG)
	$(PY) -m src.procedimiento.orquestador --config $(CONFIG)

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
