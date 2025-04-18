# Use a imagem base do Python
FROM python:3.10-slim

# Configurar o diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar os arquivos do projeto
COPY . .

# Instalar o Poetry
RUN pip install poetry

# Configurar o Poetry para instalar dependências no ambiente global
RUN poetry config virtualenvs.create false && poetry install --only main --no-root

# Instalar o psycopg2
RUN pip install psycopg2-binary

# Expor a porta do Django
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]