FROM python:3.14-slim

# bluetoothctl for clearing the BlueZ cache between connection attempts.
# It talks to the host's bluetoothd over the mounted D-Bus socket.
RUN apt-get update \
    && apt-get install -y --no-install-recommends bluez \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt /tmp/requirements-web.txt
RUN pip install --no-cache-dir -r /tmp/requirements-web.txt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBUS_SYSTEM_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

# The project folder is mounted at /app by compose.yaml.
WORKDIR /app
EXPOSE 8080
CMD ["uvicorn", "web.server:app", "--host", "0.0.0.0", "--port", "8080"]
