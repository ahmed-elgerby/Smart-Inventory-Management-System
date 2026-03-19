FROM python:3.10.20-alpine3.22

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    apk add --no-cache postgresql-client bash

COPY . .

EXPOSE 5001

# Run the Flask alert microservice
CMD ["python", "alert_microservice.py"]
