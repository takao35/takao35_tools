#!/usr/bin/env bash
set -euo pipefail
source ~/.secrets_coreserver

: "${FTP_HOST:?set FTP_HOST}"
: "${FTP_USER:?set FTP_USER}"
: "${FTP_PASS:?set FTP_PASS}"

BASE_DIR="/home/masuday/projects/takao35"
PY_SCRIPT1="$BASE_DIR/py_code/weather/open_meteo.py"
PY_SCRIPT2="$BASE_DIR/py_code/weather/jma.py"
PUB_DIR="$BASE_DIR/py_data/weather"
REMOTE_DIR="/weather"

# 1) 生成
/home/masuday/projects/pyenv/py309/bin/python "$PY_SCRIPT1"
/home/masuday/projects/pyenv/py309/bin/python "$PY_SCRIPT2"

# 2) 生成物
CUR_HTML="$PUB_DIR/takao_current.html"
D2_HTML="$PUB_DIR/takao_2days.html"
TODAY_HTML="$PUB_DIR/takao_today.html"

CUR_JSON="$PUB_DIR/takao_current.json"
D2_JSON="$PUB_DIR/takao_2days.json"
TODAY_JSON="$PUB_DIR/takao_today.json"

need_upload=false
for f in "$CUR_HTML" "$D2_HTML" "$TODAY_HTML" "$CUR_JSON" "$D2_JSON" "$TODAY_JSON"; do
  if [[ -f "$f" ]]; then need_upload=true; else echo "[warn] missing: $f"; fi
done
[[ "$need_upload" == true ]] || { echo "No files to upload. exit."; exit 0; }

# 3) アップロード（.part → mv）
lftp -e "
set ftp:ssl-force true
set ftp:ssl-protect-data true
set ssl:verify-certificate no
open -u ${FTP_USER},${FTP_PASS} ${FTP_HOST}
mkdir -p ${REMOTE_DIR}
cd ${REMOTE_DIR}
lcd ${PUB_DIR}

# HTML
$( [[ -f "$CUR_HTML"   ]] && echo "put ${CUR_HTML##*/}   -o takao_current.html.part;  mv takao_current.html.part  takao_current.html" )
$( [[ -f "$D2_HTML"    ]] && echo "put ${D2_HTML##*/}    -o takao_2days.html.part;   mv takao_2days.html.part   takao_2days.html" )
$( [[ -f "$TODAY_HTML" ]] && echo "put ${TODAY_HTML##*/} -o takao_today.html.part;   mv takao_today.html.part   takao_today.html" )

# JSON
$( [[ -f "$CUR_JSON"   ]] && echo "put ${CUR_JSON##*/}   -o takao_current.json.part; mv takao_current.json.part  takao_current.json" )
$( [[ -f "$D2_JSON"    ]] && echo "put ${D2_JSON##*/}    -o takao_2days.json.part;   mv takao_2days.json.part   takao_2days.json" )
$( [[ -f "$TODAY_JSON" ]] && echo "put ${TODAY_JSON##*/} -o takao_today.json.part;   mv takao_today.json.part   takao_today.json" )

bye
"
echo "Uploaded to ${REMOTE_DIR} (done)."