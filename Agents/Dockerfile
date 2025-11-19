FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY Agents/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY Agents/ ./Agents/

# Python будет видеть пакет Agents
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8766

CMD ["python", "-m", "Agents.api.adapter_ws_server"]
