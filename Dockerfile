# netregator-config
FROM alpine:latest as netregator-config
WORKDIR /usr/src/app

RUN apk add --no-cache --update gcc libc-dev linux-headers git && rm -rf /var/cache/apk/*
COPY .git .
COPY .env.template .
RUN [ -e "/usr/src/app/.env" ] && echo "Env already exists" || mv .env.template .env
RUN sed -i "s/%VER%/$(git describe --abbrev)/" .env

# main container
FROM python:3-alpine
ENV PYTHONUNBUFFERED definitely
ENV TZ Europe/Vienna
WORKDIR /usr/src/app

RUN adduser -s /bin/bash -S netuser && chown netuser:root /usr/src/app
USER netuser
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY --from=0 /usr/src/app/.env .
COPY main.py ./
COPY src/ ./src

CMD ["python", "./main.py"]
