FROM python:3.11-slim

# Directorio de trabajo en el contenedor
WORKDIR /code

# Instalar dependencias del sistema operativo requeridas por LightGBM/XGBoost
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de dependencias e instalarlas
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copiar todo el código del backend al contenedor
COPY . /code

# Arrancar FastAPI en el puerto 7860 (Hugging Face exige este puerto obligatoriamente)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
