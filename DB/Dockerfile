FROM postgres:15-alpine

WORKDIR /app

ENV POSTGRES_USER=postgres

ENV POSTGRES_PASSWORD=postgres

ENV POSTGRES_DB=inventory

COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 5432 
