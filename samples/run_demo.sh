#!/bin/bash
# ECHOCRAFT demo: signal generation -> processing -> analysis -> visualization
#
# Prerequisites:
#   pip install numpy matplotlib
#
# Usage (Git Bash):
#   cd samples && bash run_demo.sh
#
# Output:
#   samples/output/
#     spectrum.ndjson    - Spectrum analysis result
#     bearing.ndjson     - Bearing level analysis result
#     signal.wav         - Multi-channel WAV
#     spectrum_log.png   - Spectrum plot (dB)
#     spectrum_linear.png - Spectrum plot (linear amplitude)
#     bl.png             - Bearing level plot
#     polar.png          - Polar bearing level plot
#     btr.png            - Bearing-Time Record
#     lofar.png          - LOFAR display

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# Build PYTHONPATH from all tool directories
PYTHONPATH="${ROOT_DIR}/lib"
for tool_dir in "${ROOT_DIR}"/tools/*/; do
    PYTHONPATH="${PYTHONPATH}:${tool_dir}"
done
export PYTHONPATH

# Config files
STREAM="${ROOT_DIR}/configs/stream.json"
ARRAY="${ROOT_DIR}/configs/array.json"
OCEAN="${ROOT_DIR}/configs/ocean.json"

# Signal parameters
#   Source 1: 1024 Hz, 0 dB, azimuth 0 deg  (broadside)
#   Source 2: 4096 Hz, -5 dB, azimuth 30 deg (off-axis)
FREQ="1024,4096"
SL="0,-5"
AZ="0,30"
EL="0,0"
NL="-40"
DURATION="1.0"

# Bearing sweep parameters
AZ_START="0"
AZ_END="180"
AZ_STEP="2"

mkdir -p "${OUTPUT_DIR}"
echo "=== ECHOCRAFT Demo ==="
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# --- 1. Spectrum analysis pipeline ---
echo "[1/5] Running spectrum analysis pipeline..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  | python3 -m ec_propagate --env "${OCEAN}" --model plane-wave \
  | python3 -m ec_array --array "${ARRAY}" \
  | python3 -m ec_sample --stream "${STREAM}" --duration ${DURATION} \
  | python3 -m ec_beamform --array "${ARRAY}" --stream "${STREAM}" \
  | python3 -m eca_spectrum --stream "${STREAM}" \
  > "${OUTPUT_DIR}/spectrum.ndjson"
echo "  -> spectrum.ndjson ($(wc -l < "${OUTPUT_DIR}/spectrum.ndjson") records)"

# --- 2. Bearing level analysis pipeline ---
echo "[2/5] Running bearing level analysis pipeline..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  | python3 -m ec_propagate --env "${OCEAN}" --model plane-wave \
  | python3 -m ec_array --array "${ARRAY}" \
  | python3 -m ec_sample --stream "${STREAM}" --duration ${DURATION} \
  | python3 -m eca_bearing_level --array "${ARRAY}" --stream "${STREAM}" \
      --az-start ${AZ_START} --az-end ${AZ_END} --az-step ${AZ_STEP} \
  > "${OUTPUT_DIR}/bearing.ndjson"
echo "  -> bearing.ndjson ($(wc -l < "${OUTPUT_DIR}/bearing.ndjson") records)"

# --- 3. WAV export ---
echo "[3/5] Exporting WAV file..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  | python3 -m ec_propagate --env "${OCEAN}" --model plane-wave \
  | python3 -m ec_array --array "${ARRAY}" \
  | python3 -m ec_sample --stream "${STREAM}" --duration ${DURATION} \
  | python3 -m ec_to_wav --stream "${STREAM}" --output "${OUTPUT_DIR}/signal.wav" --channels 10
echo "  -> signal.wav ($(stat -c%s "${OUTPUT_DIR}/signal.wav" 2>/dev/null || stat -f%z "${OUTPUT_DIR}/signal.wav") bytes)"

# --- 4. Visualization ---
echo "[4/5] Generating plots..."

python3 -m ecv_spectrum \
  --input "${OUTPUT_DIR}/spectrum.ndjson" \
  --output "${OUTPUT_DIR}/spectrum_log.png" \
  --scale log
echo "  -> spectrum_log.png"

python3 -m ecv_spectrum \
  --input "${OUTPUT_DIR}/spectrum.ndjson" \
  --output "${OUTPUT_DIR}/spectrum_linear.png" \
  --scale linear
echo "  -> spectrum_linear.png"

python3 -m ecv_bl \
  --input "${OUTPUT_DIR}/bearing.ndjson" \
  --output "${OUTPUT_DIR}/bl.png"
echo "  -> bl.png"

python3 -m ecv_polar \
  --input "${OUTPUT_DIR}/bearing.ndjson" \
  --output "${OUTPUT_DIR}/polar.png"
echo "  -> polar.png"

python3 -m ecv_btr \
  --input "${OUTPUT_DIR}/bearing.ndjson" \
  --output "${OUTPUT_DIR}/btr.png"
echo "  -> btr.png"

python3 -m ecv_lofar \
  --input "${OUTPUT_DIR}/spectrum.ndjson" \
  --output "${OUTPUT_DIR}/lofar.png"
echo "  -> lofar.png"

# --- 5. Summary ---
echo ""
echo "[5/5] Done. Output files:"
ls -lh "${OUTPUT_DIR}/"
