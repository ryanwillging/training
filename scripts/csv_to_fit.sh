#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 /path/to/FitCSVTool.jar input.csv output.fit"
  exit 1
fi

JAR="$1"
CSV="$2"
FIT="$3"

java -jar "$JAR" -c "$CSV" "$FIT"
echo "Wrote: $FIT"
