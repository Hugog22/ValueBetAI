#!/bin/bash
# Script para desplegar el backend directamente a Hugging Face sin consumir Git LFS de GitHub
# y evitando errores de historial de archivos grandes.

echo "🚀 Iniciando despliegue limpio del backend a Hugging Face..."

# Preguntar el método de conexión
echo "Selecciona el método de conexión a Hugging Face:"
echo "1) SSH (Recomendado si ya tienes configurada tu clave SSH en Hugging Face)"
echo "2) HTTPS con Token (Usa tu HF_TOKEN)"
read -p "Opción [1 o 2]: " metodo

if [ "$metodo" = "1" ]; then
    REMOTE_URL="git@hf.co:spaces/hugog22/quantstake-api"
    echo "Using SSH remote: $REMOTE_URL"
elif [ "$metodo" = "2" ]; then
    read -sp "Introduce tu token de Hugging Face (HF_TOKEN): " token
    echo ""
    if [ -z "$token" ]; then
        echo "❌ Error: El token no puede estar vacío."
        exit 1
    fi
    REMOTE_URL="https://hugog22:$token@huggingface.co/spaces/hugog22/quantstake-api"
    echo "Using HTTPS remote with token."
else
    echo "❌ Opción no válida."
    exit 1
fi

# Definir directorios
PROJECT_DIR="/Users/hugo/Documents/UPV/ANTIGRAVITY/ProyectoPrueba"
BACKEND_DIR="$PROJECT_DIR/backend"
TEMP_DIR="/tmp/quantstake_backend_deploy"

# Limpieza inicial por si acaso
rm -rf "$TEMP_DIR"

echo "📂 Creando copia temporal limpia del backend..."
mkdir -p "$TEMP_DIR"
cp -R "$BACKEND_DIR/" "$TEMP_DIR/"

# Entrar al directorio temporal
cd "$TEMP_DIR" || exit 1

# Eliminar posibles carpetas de git o entornos virtuales locales copiados por error
rm -rf .git
rm -rf venv
rm -rf .venv

echo "⚙️ Inicializando repositorio git temporal..."
git init
git branch -M main
git config user.name "Local Auto-Deploy"
git config user.email "deploy@quantstake.ai"

echo "📦 Configurando Git LFS para archivos .pkl..."
git lfs install
git lfs track "*.pkl"
# Asegurar el archivo .gitattributes
if [ -f "$BACKEND_DIR/.gitattributes" ]; then
    cp "$BACKEND_DIR/.gitattributes" .
else
    echo "*.pkl filter=lfs diff=lfs merge=lfs -text" > .gitattributes
fi

echo "➕ Añadiendo archivos..."
git add .

echo "💾 Creando commit..."
git commit -m "Local clean deploy"

echo "📤 Subiendo a Hugging Face Spaces..."
if git push -f "$REMOTE_URL" main; then
    echo "✅ ¡Despliegue completado con éxito!"
else
    echo "❌ Error al subir a Hugging Face."
    cd "$PROJECT_DIR" || exit
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Limpieza final
cd "$PROJECT_DIR" || exit
rm -rf "$TEMP_DIR"
echo "🎉 ¡Todo limpio!"
