FROM python:3.12-slim

# ── Drivers ODBC de Microsoft (necesarios para conectar a SQL Server) ──────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg2 apt-transport-https ca-certificates unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependencias primero (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código
COPY . .

# Crea el directorio de datos por si no viene en la imagen
RUN mkdir -p hub_central/jsons

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
