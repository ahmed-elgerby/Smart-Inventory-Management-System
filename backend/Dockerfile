FROM python:3.10.20-alpine3.22

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt && \
    apk add --no-cache postgresql-client bash

COPY . .

RUN chmod +x wait-for-db.sh

EXPOSE 5000

ENTRYPOINT ["./wait-for-db.sh"]
