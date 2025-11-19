FROM golang:alpine


RUN apk add --no-cache git

WORKDIR /app


COPY . .


RUN go mod init main && \
    go mod tidy





RUN touch databaseLogs.log tokenLogs.log MainHTTP.log

# Порт
EXPOSE 3110


CMD ["go", "run", "main.go"]
