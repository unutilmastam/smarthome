FROM python:3.12-slim
WORKDIR /app
COPY services/hub/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/hub/gateway /app/gateway
COPY services/hub/simulator /app/simulator
COPY packages/contracts /app/contracts
ENV CONTRACTS_DIR=/app/contracts PYTHONUNBUFFERED=1
RUN useradd -r -u 10001 hub && mkdir -p /data && chown hub /data
USER hub
CMD ["python", "-m", "gateway"]
