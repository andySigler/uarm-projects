#!/usr/bin/env bash

PORT="$1"

FIRMWARE_DIR="$(
  cd "$(dirname "$0")" || exit
  pwd -P
)"
AVRDUDE_PATH="/Applications/Arduino-1.8.11.app/Contents/Java/hardware/tools/avr/bin/avrdude"
CONFIG_PATH="$FIRMWARE_DIR/avrdude.conf"
HEX_PATH="$FIRMWARE_DIR/uArmPro_V4.5.0_release_20190924.hex"

$AVRDUDE_PATH -C"$CONFIG_PATH" -e -v -patmega2560 -cwiring -P"$PORT" -b115200
$AVRDUDE_PATH -C"$CONFIG_PATH" -v -patmega2560 -cwiring -P"$PORT" -b115200 -Uflash:w:"$HEX_PATH"
