#!/bin/bash

# === CONFIGURATION example can be found in example_configure.sh ===
# export MQTT_BROKER="webbot-mqtt-broker.linodeusercontent.com"
# export MQTT_USERNAME="webbot_mqtt_user"
# export MQTT_PASSWORD="mqtt_password"
# export MQTT_PORT=1883

source ./watchdog_configure.sh || {
  echo "Failed to source watchdog_configure.sh"
  exit 1
}


MQTT_TOPIC="webbot/status"
PUBLISH_TOPIC="restart/notice"
GRACE_PERIOD=360  # 6 minutes

DOCKER_IMAGE_NAME="webbot:latest"
DOCKER_CONTAINER_NAME="webbot_container"
DOCKER_FILE="Dockerfile.freeze"
MQTT_LOG_FILE="/tmp/webbot_status.log"

# === FUNCTIONS ===

timestamp() {
  date +"[%Y-%m-%d %H:%M:%S]"
}


log() {
  echo "$(timestamp) $1"
}
wait_for_x11() {
  local container="$1"
  local retries=20
  local delay=1

  log "Waiting for container's X11 Server"
  for i in $(seq 1 $retries); do
    if docker exec "$container" sh -c "xdpyinfo -display :0" >/dev/null 2>&1; then
      log "X11 server is ready"
      return 0
    fi
    sleep $delay
  done

  log "Timeout waiting for X11 server"
  return 1
}

ensure_image_exists() {
  if docker image inspect "$DOCKER_IMAGE_NAME" >/dev/null 2>&1; then
      log "Image $DOCKER_IMAGE_NAME already exists — skipping build."
  else
      log "Image $DOCKER_IMAGE_NAME not found — building... (with Dockerfile $DOCKER_FILE)"
      docker build -f "$DOCKER_FILE" -t "$DOCKER_IMAGE_NAME" .
      if [ $? -ne 0 ]; then
          log "ERROR: Docker image build failed!"
          return 1
      fi
      log "Docker image built successfully."
  fi
}


start_container() {
    local referrer="$1"

    # Ensure environment variables are set
    if [ -z "$VH_DEVICE" ] || [ -z "$VH_PORT" ] || [ -z "$VH_HOST" ] || [ -z "$VNC_PASSWORD" ]; then
        log "WARNING: One or more required environment variables (VH_DEVICE, VH_PORT, VH_HOST, VNC_PASSWORD) are not set. - No vhclient will run."
    fi

    log "Starting Docker container $DOCKER_CONTAINER_NAME... referrer: $referrer"
    log "Using VH_HOST=$VH_HOST VH_PORT=$VH_PORT VH_DEVICE=$VH_DEVICE VNC_PASSWORD=$VNC_PASSWORD"

    CONTAINER_ID=$(docker run -d \
        --name "$DOCKER_CONTAINER_NAME" \
        -p 5901:5900 -p 6080:6080 \
        --device /dev/bus/usb:/dev/bus/usb \
        --privileged \
        -e referrer="$referrer" \
        -e VH_DEVICE="$VH_DEVICE" \
        -e VH_PORT="$VH_PORT" \
        -e VH_HOST="$VH_HOST" \
        -e VNC_PASSWORD="$VNC_PASSWORD" \
        "$DOCKER_IMAGE_NAME")

    # Wait for X11 (if you have this function defined)
    wait_for_x11 "$DOCKER_CONTAINER_NAME"

    # Start the webbot script in a detached xterm
    docker exec -d "$DOCKER_CONTAINER_NAME" bash -c "cd /app && xterm -hold -e ./webbot.sh"

    echo "Container for $DOCKER_IMAGE_NAME created. Container ID is $CONTAINER_ID"
}

stop_container() {
  log "Stopping Docker container..."
  docker stop "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1
  docker rm "$DOCKER_CONTAINER_NAME" >/dev/null 2>&1
}

is_running() {
  local name="$1"
  docker ps --filter "name=^${name}$" --format '{{.Names}}' | grep -q "^${name}$"
}

container_exists() {
  local name="$1"
  docker ps -a --filter "name=^${name}$" --format '{{.Names}}' | grep -q "^${name}$"
}

start_mqtt_listener() {
  webbot_status_topic="$MQTT_TOPIC/$CONTAINER_HOSTNAME"
  log "Starting MQTT listener on topic $webbot_status_topic"
  rm -f "$MQTT_LOG_FILE"
  touch "$MQTT_LOG_FILE"
  mosquitto_sub -h "$MQTT_BROKER" -p "$MQTT_PORT" \
    -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" \
    -t "$webbot_status_topic" -v >> "$MQTT_LOG_FILE" 2>/dev/null &
  MQTT_PID=$!
}


stop_mqtt_listener() {
  if [ -n "$MQTT_PID" ]; then
    if kill -0 "$MQTT_PID" 2>/dev/null; then
      log "Stopping MQTT listener (PID $MQTT_PID)..."
      kill "$MQTT_PID" 2>/dev/null
      sleep 2

      if kill -0 "$MQTT_PID" 2>/dev/null; then
        log "Force killing MQTT listener (PID $MQTT_PID)..."
        kill -9 "$MQTT_PID" 2>/dev/null
      fi

      wait "$MQTT_PID" 2>/dev/null
    else
      log "MQTT listener PID $MQTT_PID is not running."
    fi
    unset MQTT_PID
  fi
}

stop_mqtt_listener_deprecated() {
  if [ -n "$MQTT_PID" ]; then
    log "Stopping MQTT listener (PID $MQTT_PID)..."
    kill "$MQTT_PID" 2>/dev/null
    wait "$MQTT_PID" 2>/dev/null
    unset MQTT_PID
  fi
}


has_arg() {
  local keyword="$1"
  shift
  for arg in "$@"; do
    if [[ "$arg" == "$keyword" ]]; then
      return 0  # true
    fi
  done
  return 1  # false
}

print_usage() {
  echo "Usage: $0 [--join] [--help]"
  echo
  echo "Options:"
  echo "  --join     Start the container only if it is not already running."
  echo "  --help     Show this help message and exit."
}

# Determine correct stat command for modification time
if stat --version >/dev/null 2>&1; then
  # GNU stat (Linux)
  STAT_MOD_TIME() {
    stat -c %Y "$1"
  }
else
  # BSD stat (macOS, *BSD)
  STAT_MOD_TIME() {
    stat -f %m "$1"
  }
fi

# === MAIN ===

HOSTNAME=$(hostname)

log "Starting Docker watchdog for $DOCKER_IMAGE_NAME... on host $HOSTNAME"

log "MQTT Broker $MQTT_BROKER:$MQTT_PORT"

ensure_image_exists || {
  log "Image build failed — aborting watchdog."
  exit 1
}

if has_arg --help "$@" || has_arg -h "$@"; then
  print_usage
  exit 0
fi

if ! has_arg --join "$@"; then
  log "No --join flag — doing full stop/start"
  if container_exists "$DOCKER_CONTAINER_NAME"; then
    stop_container
  else
    log "Container does not exist — skipping stop"
  fi
  start_container "$HOSTNAME"
else
  log "--join flag detected — checking container status"
  if ! is_running "$DOCKER_CONTAINER_NAME"; then
    log "Container '$DOCKER_CONTAINER_NAME' not running — starting it"
    start_container "$HOSTNAME"
  else
    log "Container '$DOCKER_CONTAINER_NAME' already running — doing nothing"
  fi
fi



CONTAINER_HOSTNAME=$(docker exec "$DOCKER_CONTAINER_NAME" hostname 2>/dev/null || echo "unknown")
log "hostname for container $DOCKER_CONTAINER_NAME is $CONTAINER_HOSTNAME"

start_mqtt_listener 

LAST_MSG_TIME=$(STAT_MOD_TIME "$MQTT_LOG_FILE" 2>/dev/null || echo 0)

while true; do
  log "Monitoring health of container '$DOCKER_CONTAINER_NAME'..."

  START_TIME=$(date +%s)
  MESSAGE_RECEIVED=false

  while true; do
    # Check if container is still running
    if ! is_running "$DOCKER_CONTAINER_NAME"; then
      log "Docker container has stopped unexpectedly."
      break
    fi

    # Check for new MQTT message by log file modification time
    if [ -f "$MQTT_LOG_FILE" ]; then
      MSG_TIME=$(STAT_MOD_TIME "$MQTT_LOG_FILE")
      if (( MSG_TIME > LAST_MSG_TIME )); then
        log "MQTT message received. Container is healthy."
        LAST_MSG_TIME=$MSG_TIME
        MESSAGE_RECEIVED=true
        break
      fi
    fi

    # Check timeout
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    if (( ELAPSED >= GRACE_PERIOD )); then
      log "Grace period exceeded without MQTT message."
      break
    fi

    sleep 1
  done

  if [ "$MESSAGE_RECEIVED" = false ]; then
    log "Restarting container due to missing MQTT heartbeat..."
    stop_mqtt_listener
    stop_container
    start_container "$HOSTNAME"
    CONTAINER_HOSTNAME=$(docker exec "$DOCKER_CONTAINER_NAME" hostname 2>/dev/null || echo "unknown")
    echo "$CONTAINER_HOSTNAME"
    MESSAGE="Container $DOCKER_CONTAINER_NAME (host: $HOSTNAME, container host: $CONTAINER_HOSTNAME) was restarted by watchdog."
    #MESSAGE="Restarting"
    HOST_TOPIC="$PUBLISH_TOPIC/$HOSTNAME"
    log "Publishing restart message to MQTT topic: $HOST_TOPIC"

    mosquitto_pub -h "$MQTT_BROKER" -p "$MQTT_PORT" \
      -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" \
      -t "$HOST_TOPIC" -m "$MESSAGE"
    log "Published restart message completed."
    start_mqtt_listener
    LAST_MSG_TIME=$(STAT_MOD_TIME "$MQTT_LOG_FILE" 2>/dev/null || echo 0)
  fi

  sleep 5
done
