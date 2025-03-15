FROM python:3.12-slim

# Set the working directory
WORKDIR /app

COPY YandexInternalRootCA.crt .

# Copy and install dependencies
COPY requirements.txt .
COPY requirements_api.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_api.txt

# Copy the source code
COPY src/ /app/src

ENV PYTHONPATH="/app/src"

# Expose port 8000
EXPOSE 8000

# Run the API
CMD ["sh", "-c", "uvicorn src.api.api:app --host 0.0.0.0 --port 8000"]
