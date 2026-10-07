#!/bin/sh
# Builds mosquitto/passwd from .env. Run once on the hub (or after adding devices):
#   sh mosquitto/make-passwd.sh garden_lights main_meter ...
# Gateway password: MQTT_PASSWORD. Device passwords: DEVICE_PASSWORD_<KEY> or, for the
# simulator only, SIM_DEVICE_PASSWORD. Never commit the generated passwd file.
set -eu
cd "$(dirname "$0")"
[ -f ../.env ] && . ../.env
: "${MQTT_PASSWORD:?MQTT_PASSWORD is required}"
rm -f passwd && touch passwd && chmod 600 passwd
mosquitto_passwd -b passwd gateway "$MQTT_PASSWORD"
for key in "$@"; do
  var="DEVICE_PASSWORD_$(echo "$key" | tr 'a-z' 'A-Z')"
  pw=$(eval "echo \${$var:-}")
  [ -z "$pw" ] && pw="${SIM_DEVICE_PASSWORD:?no password for $key}"
  mosquitto_passwd -b passwd "$key" "$pw"
done
echo "wrote $(wc -l < passwd) users"
