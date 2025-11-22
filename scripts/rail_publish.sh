#!/usr/bin/env bash
set -euo pipefail

# ==== 認証情報（~/.secrets_coreserver に以下を export 済み想定）====
# export FTP_HOST=...
# export FTP_USER=...
# export FTP_PASS=...
source ~/.secrets_coreserver
: "${FTP_HOST:?set FTP_HOST}"
: "${FTP_USER:?set FTP_USER}"
: "${FTP_PASS:?set FTP_PASS}"

# ==== パス設定 ====
PY="/home/masuday/projects/py313/bin/python"   # pyenvの絶対パスを使用
BASE_DIR="/home/masuday/projects/takao35"
PY_SCRIPT="$BASE_DIR/py_code/train/rail_status.py"   # ← 生成スクリプトの場所
OUT_DIR="$BASE_DIR/py_data/train"                  # rail_status.py の出力先
REMOTE_DIR="/train"                                # CoreServer 側の配置先

HTML_OUT="$OUT_DIR/takao_rail_info.html"
JSON_OUT="$OUT_DIR/takao_rail_info.json"

# ==== 1) 生成 ====
"$PY" "$PY_SCRIPT"

# ==== 2) 出力確認 ====
need_upload=false
[[ -f "$HTML_OUT" ]] && need_upload=true || echo "[warn] missing: $HTML_OUT"
[[ -f "$JSON_OUT" ]] && need_upload=true || echo "[warn] missing: $JSON_OUT"
[[ "$need_upload" == true ]] || { echo "No files to upload. exit."; exit 0; }

# ==== 3) アップロード（.part → mv で原子的に更新）====
lftp -e "
set ftp:ssl-force true
set ftp:ssl-protect-data true
set ssl:verify-certificate no
open -u ${FTP_USER},${FTP_PASS} ${FTP_HOST}
mkdir -p ${REMOTE_DIR}
cd ${REMOTE_DIR}
lcd ${OUT_DIR}

# HTML
put ${HTML_OUT##*/} -o takao_rail_info.html.part
mv  takao_rail_info.html.part takao_rail_info.html

# JSON
put ${JSON_OUT##*/} -o takao_rail_info.json.part
mv  takao_rail_info.json.part takao_rail_info.json

bye
"
echo "Uploaded: ${REMOTE_DIR}/takao_rail_info.(html|json)"