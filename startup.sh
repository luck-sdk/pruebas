#!/bin/bash
echo "🔧 Instalando ODBC Driver para SQL Server..."

set -e

# Actualizar paquetes
apt-get update -qq

# Dependencias básicas
apt-get install -y -qq unixodbc unixodbc-dev curl gnupg

# Agregar llave Microsoft (nuevo método seguro)
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg

# Repo Microsoft
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

apt-get update -qq

# Instalar ODBC DRIVER (recomendado 18)
ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18

echo "✅ Drivers instalados:"
odbcinst -q -d

echo "🚀 Iniciando Gunicorn..."

# IMPORTANTE: sin coma al final
gunicorn --bind=0.0.0.0:8000 --timeout 300 --workers 2 --threads 4 app:app
