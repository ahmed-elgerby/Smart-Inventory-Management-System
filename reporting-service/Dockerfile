FROM python:3.10.20-alpine3.22

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    apk add --no-cache postgresql-client bash

COPY . .

EXPOSE 5002

# Run the Flask reporting microservice
CMD ["python", "reporting_services.py"]
