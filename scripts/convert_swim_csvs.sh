#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 /path/to/FitCSVTool.jar /path/to/input_csv_dir /path/to/output_fit_dir"
  exit 1
fi

JAR="$1"
INPUT_DIR="$2"
OUTPUT_DIR="$3"

mkdir -p "$OUTPUT_DIR"

shopt -s nullglob
for csv in "$INPUT_DIR"/*.csv; do
  base="$(basename "$csv" .csv)"
  output="$OUTPUT_DIR/${base}.fit"
  "$(dirname "$0")/csv_to_fit.sh" "$JAR" "$csv" "$output"
done
