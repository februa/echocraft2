#!/bin/bash
# ECHOCRAFT demo: signal generation -> processing -> analysis -> visualization
#
# Windows/Git Bash version — runs the upstream pipeline three times
# (once per consumer). This avoids concurrent process startup issues
# on Windows. For Linux, use run_demo.sh (ec-pub/ec-sub fan-out).
#
# Prerequisites:
#   pip install numpy matplotlib
#
# Usage (Git Bash):
#   cd samples && bash run_demo_win.sh
#
# Output:
#   samples/output/
#     spectrum.ndjson    - Spectrum analysis result
#     bearing.ndjson     - Bearing level analysis result
#     signal.wav         - Multi-channel WAV
#     sources.ndjson     - Source/noise parameter records
#     spectrum_log.png   - Spectrum plot (dB)
#     spectrum_linear.png - Spectrum plot (linear amplitude)
#     bl.png             - Bearing level plot
#     polar.png          - Polar bearing level plot
#     btr.png            - Bearing-Time Record
#     lofar.png          - LOFAR display
#     scene.png          - Scene overview (array + signal directions)

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

# --- Parameter design rationale ---
#
# Sampling frequency (stream.json):
#   fs = 32768 Hz
#   Nyquist = fs/2 = 16384 Hz
#
# Array (array.json):
#   d = 0.058 m (sensor spacing), N = 12 sensors
#   f_grating = c / (2d) = 1500 / (2 * 0.058) = 12931 Hz
#   Nyquist (16384 Hz) > f_grating (12931 Hz) ... satisfied
#
# Signal frequencies:
#   10240 Hz < f_grating (12931 Hz) ... no grating lobe
#   5120 Hz  < f_grating (12931 Hz) ... no grating lobe
#
# Frequency resolution (stream.json):
#   rate = 32 Hz = Δf (frequency resolution)
#   block_size = fs / rate = 32768 / 32 = 1024 samples
#   T_frame = block_size / fs = 1024 / 32768 = 31.25 ms
#   Both 10240 and 5120 are integer multiples of Δf=32,
#   so signal peaks fall exactly on FFT bins (no scalloping loss).
#
# Signal parameters (VESSEL_BODY: az=0 is bow, az=90 is starboard)
#   Source 1: 10240 Hz, 0 dB, azimuth 60 deg
#   Source 2: 5120 Hz, -5 dB, azimuth 150 deg
FREQ="10240"
SL="0"
AZ="60"
EL="0"
NL="-40"
DURATION="1.0"

# Bearing sweep parameters
AZ_START="0"
AZ_END="180"
AZ_STEP="0.5"

# Vessel heading (true north = 0, clockwise)
HEADING="0"

MODEL="lossless"

mkdir -p "${OUTPUT_DIR}"
echo "=== ECHOCRAFT Demo (Windows) ==="
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# --- 0. Save source/noise parameters for scene plot ---
echo "[0/6] Saving source parameters..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  > "${OUTPUT_DIR}/sources.ndjson"
echo "  -> sources.ndjson ($(wc -l < "${OUTPUT_DIR}/sources.ndjson") records)"

# --- 1. Spectrum analysis pipeline ---
echo "[1/6] Running spectrum analysis pipeline..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  | python3 -m ec_propagate --env "${OCEAN}" --model ${MODEL} \
  | python3 -m ec_array --array "${ARRAY}" \
  | python3 -m ec_sample --stream "${STREAM}" --duration ${DURATION} \
  | python3 -m ec_beamform --array "${ARRAY}" --stream "${STREAM}" \
  | python3 -m eca_spectrum --stream "${STREAM}" \
  > "${OUTPUT_DIR}/spectrum.ndjson"
echo "  -> spectrum.ndjson ($(wc -l < "${OUTPUT_DIR}/spectrum.ndjson") records)"

# --- 2. Bearing level analysis pipeline ---
echo "[2/6] Running bearing level analysis pipeline..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  | python3 -m ec_propagate --env "${OCEAN}" --model ${MODEL} \
  | python3 -m ec_array --array "${ARRAY}" \
  | python3 -m ec_sample --stream "${STREAM}" --duration ${DURATION} \
  | python3 -m eca_bearing_level --array "${ARRAY}" --stream "${STREAM}" \
      --az-start ${AZ_START} --az-end ${AZ_END} --az-step ${AZ_STEP} \
  > "${OUTPUT_DIR}/bearing.ndjson"
echo "  -> bearing.ndjson ($(wc -l < "${OUTPUT_DIR}/bearing.ndjson") records)"

# --- 3. WAV export ---
echo "[3/6] Exporting WAV file..."
python3 -m ec_source_nb --freq ${FREQ} --sl ${SL} --az ${AZ} --el ${EL} \
  | python3 -m ec_noise --nl ${NL} \
  | python3 -m ec_propagate --env "${OCEAN}" --model ${MODEL} \
  | python3 -m ec_array --array "${ARRAY}" \
  | python3 -m ec_sample --stream "${STREAM}" --duration ${DURATION} \
  | python3 -m ec_to_wav --stream "${STREAM}" --array "${ARRAY}" --output "${OUTPUT_DIR}/signal.wav"
echo "  -> signal.wav ($(stat -c%s "${OUTPUT_DIR}/signal.wav" 2>/dev/null || stat -f%z "${OUTPUT_DIR}/signal.wav") bytes)"

# --- 4. Visualization ---
echo "[4/6] Generating plots..."

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

# --- 5. Scene overview ---
echo "[5/6] Generating scene overview..."
python3 -m ecv_scene \
  --array "${ARRAY}" \
  --input "${OUTPUT_DIR}/sources.ndjson" \
  --output "${OUTPUT_DIR}/scene.png" \
  --heading ${HEADING}
echo "  -> scene.png"

# --- 6. Summary ---
echo ""
echo "[6/6] Done. Output files:"
ls -lh "${OUTPUT_DIR}/"
