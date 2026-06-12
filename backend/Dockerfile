FROM python:3.10-slim

# Directorio de trabajo en el contenedor
WORKDIR /code

# Copiar el archivo de dependencias e instalarlas
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copiar todo el código del backend al contenedor
COPY . /code

# Arrancar FastAPI en el puerto 7860 (Hugging Face exige este puerto obligatoriamente)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
