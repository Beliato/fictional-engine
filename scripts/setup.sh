#!/usr/bin/env bash
# =============================================================================
# Crea el entorno virtual reproducible e instala las dependencias fijadas.
#
# Uso:
#   ./scripts/setup.sh
#
# Variables de entorno opcionales:
#   PYTHON_BIN   intérprete base a usar (por defecto: python3.11)
#   VENV_DIR     directorio del venv (por defecto: .venv)
# =============================================================================
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV_DIR="${VENV_DIR:-.venv}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

echo "==> Repositorio:        $RAIZ"
echo "==> Intérprete base:    $PYTHON_BIN"
echo "==> Directorio de venv: $VENV_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: no se encontró '$PYTHON_BIN'." >&2
  echo "       En WSL2/Ubuntu: sudo apt install python3.11 python3.11-venv" >&2
  exit 1
fi

# Comprobación de versión (se espera 3.11.x, ver .python-version).
"$PYTHON_BIN" - <<'PY'
import sys
major, minor = sys.version_info[:2]
assert (major, minor) == (3, 11), f"Se espera Python 3.11.x, se encontró {major}.{minor}"
print(f"==> Versión de Python OK: {sys.version.split()[0]}")
PY

echo "==> Creando entorno virtual..."
"$PYTHON_BIN" -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Fijando herramientas de empaquetado..."
python -m pip install --upgrade "pip==24.0" "setuptools==69.5.1" "wheel==0.43.0"

if [[ -f requirements.lock ]]; then
  echo "==> Instalando desde requirements.lock (cierre transitivo exacto)..."
  pip install --no-deps -r requirements.lock
else
  echo "==> requirements.lock no existe; instalando desde requirements.txt..."
  pip install -r requirements.txt
  echo "==> Recuerde ejecutar 'make lock' para congelar el cierre transitivo."
fi

echo "==> Verificando coherencia de dependencias..."
python -m pip check

cat <<'EOF'

==> Entorno listo.

    Activar:   source .venv/bin/activate
    Probar:    make test
    Pipeline:  make pipeline
EOF
