#!/bin/bash
echo "🔧 Instalando ODBC Driver para SQL Server..."

# Actualizar repositorios
apt-get update -qq

# Instalar dependencias
apt-get install -y -qq unixodbc unixodbc-dev odbcinst curl

# Instalar ODBC Driver 17
curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update -qq
ACCEPT_EULA=Y apt-get install -y -qq msodbcsql17

echo "✅ Drivers instalados:"
odbcinst -q -d

echo "🚀 Iniciando Gunicorn..."
# ✅ Apuntando directamente a app:app (sin wsgi.py)
gunicorn --bind=0.0.0.0 --timeout=300 --workers=2 --threads=4 app:app
