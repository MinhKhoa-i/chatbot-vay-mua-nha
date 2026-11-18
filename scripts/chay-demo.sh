#!/usr/bin/env bash
# Chạy toàn bộ hệ thống demo bằng một lệnh (việc 17 tuần 3):
#   database (Docker) -> migration -> dịch vụ AI (8001) -> backend (8000) -> giao diện (5173, gọi backend thật)
# Cách dùng (Git Bash trên Windows, hoặc bash trên macOS/Linux), từ thư mục gốc repo:
#   bash scripts/chay-demo.sh             # chạy, tự mở trình duyệt; Ctrl + C để tắt hết
#   bash scripts/chay-demo.sh --giu-db    # khi tắt vẫn để database chạy (lần sau khởi động nhanh hơn)
#   bash scripts/chay-demo.sh --khong-mo  # không tự mở trình duyệt
# Log của từng dịch vụ nằm trong .demo-logs/ (đã git-ignore).

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$ROOT/.demo-logs"
GIU_DB=0
MO_TRINH_DUYET=1
for arg in "$@"; do
  case "$arg" in
    --giu-db) GIU_DB=1 ;;
    --khong-mo) MO_TRINH_DUYET=0 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Không hiểu tham số: $arg (xem: bash scripts/chay-demo.sh --help)"; exit 1 ;;
  esac
done

PIDS=()
DA_DON=0

buoc() { printf '\n==> %s\n' "$1"; }
loi() { printf '\n[LỖI] %s\n' "$1" >&2; }

# Tắt một tiến trình nền cùng các tiến trình con (uv -> uvicorn, npm -> node).
tat_tien_trinh() {
  local pid="$1"
  if [ -r "/proc/$pid/winpid" ] && command -v taskkill >/dev/null 2>&1; then
    taskkill //F //T //PID "$(cat "/proc/$pid/winpid")" >/dev/null 2>&1
  else
    pkill -TERM -P "$pid" 2>/dev/null
    kill -TERM "$pid" 2>/dev/null
  fi
}

don_dep() {
  [ "$DA_DON" = 1 ] && return
  DA_DON=1
  buoc "Đang tắt demo"
  for pid in "${PIDS[@]}"; do tat_tien_trinh "$pid"; done
  if [ "$GIU_DB" = 0 ]; then
    (cd "$ROOT/ai_service" && docker compose stop db >/dev/null 2>&1) && echo "Đã tắt database."
  else
    echo "Database vẫn chạy (--giu-db). Tắt bằng: cd ai_service && docker compose stop db"
  fi
  echo "Đã tắt dịch vụ AI, backend và giao diện."
}
trap don_dep EXIT
trap 'exit 130' INT TERM

# Chờ một địa chỉ trả về HTTP 200; quá thời gian thì in cuối log và dừng.
cho_san_sang() {
  local ten="$1" url="$2" log="$3" giay="${4:-120}" i
  for ((i = 0; i < giay; i += 2)); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "$url")" = "200" ]; then
      echo "$ten đã sẵn sàng: $url"
      return 0
    fi
    sleep 2
  done
  loi "$ten không khởi động được sau ${giay} giây. Cuối file log $log:"
  tail -n 25 "$log" >&2
  exit 1
}

cong_dang_dung() {
  curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1/" && return 0
  curl -s -o /dev/null --max-time 2 "http://localhost:$1/" && return 0
  return 1
}

# ---------- 1. Kiểm tra điều kiện ----------
buoc "Kiểm tra công cụ và cấu hình"
for cmd in docker uv npm curl; do
  command -v "$cmd" >/dev/null 2>&1 || { loi "Chưa cài '$cmd'. Xem mục 'Chạy demo' trong README.md."; exit 1; }
done
if [ ! -f "$ROOT/ai_service/.env" ]; then
  loi "Thiếu ai_service/.env. Tạo bằng: cp ai_service/.env.example ai_service/.env rồi điền khóa (xin trưởng nhóm, không commit)."
  exit 1
fi
for port in 8001 8000 5173; do
  if cong_dang_dung "$port"; then
    loi "Cổng $port đang có chương trình khác chạy (có thể là demo cũ chưa tắt). Tắt nó trước rồi chạy lại."
    exit 1
  fi
done
mkdir -p "$LOGS"
echo "Đủ điều kiện. Log nằm trong .demo-logs/"

# ---------- 2. Docker và database ----------
buoc "Bật database (PostgreSQL + pgvector)"
if ! docker info >/dev/null 2>&1; then
  DOCKER_EXE="/c/Program Files/Docker/Docker/Docker Desktop.exe"
  if [ -f "$DOCKER_EXE" ]; then
    echo "Docker Desktop chưa chạy, đang mở..."
    "$DOCKER_EXE" >/dev/null 2>&1 &
  else
    loi "Docker chưa chạy. Hãy mở Docker Desktop rồi chạy lại."
    exit 1
  fi
fi
DB_OK=0
for ((i = 0; i < 90; i++)); do
  if (cd "$ROOT/ai_service" && docker compose up -d db >"$LOGS/db.log" 2>&1); then DB_OK=1; break; fi
  sleep 2
done
[ "$DB_OK" = 1 ] || { loi "Không bật được database. Xem .demo-logs/db.log"; tail -n 10 "$LOGS/db.log" >&2; exit 1; }
for ((i = 0; i < 60; i++)); do
  (cd "$ROOT/ai_service" && docker compose ps db --format '{{.Status}}' 2>/dev/null | grep -q healthy) && break
  sleep 2
done
echo "Database đã chạy (cổng 5433)."

buoc "Cập nhật cấu trúc database (migration)"
if ! (cd "$ROOT/ai_service" && uv run --python 3.12 alembic upgrade head >"$LOGS/migration.log" 2>&1); then
  loi "Migration lỗi. Cuối file .demo-logs/migration.log:"
  tail -n 20 "$LOGS/migration.log" >&2
  exit 1
fi
echo "Migration xong."

# ---------- 3. Các dịch vụ ----------
buoc "Bật dịch vụ AI (cổng 8001)"
(cd "$ROOT/ai_service" && exec uv run --python 3.12 uvicorn app.main:app --host 127.0.0.1 --port 8001) >"$LOGS/ai_service.log" 2>&1 &
PIDS+=("$!")
cho_san_sang "Dịch vụ AI" "http://127.0.0.1:8001/docs" "$LOGS/ai_service.log" 180

buoc "Bật backend (cổng 8000, nối dịch vụ AI)"
(cd "$ROOT/backend" && AI_SERVICE_URL="http://127.0.0.1:8001" exec uv run --no-project --python 3.12 \
  --with-requirements requirements.txt uvicorn app.main:app --host 127.0.0.1 --port 8000) >"$LOGS/backend.log" 2>&1 &
PIDS+=("$!")
cho_san_sang "Backend" "http://127.0.0.1:8000/api/health" "$LOGS/backend.log" 180

buoc "Bật giao diện (cổng 5173, gọi backend thật)"
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "Lần đầu chạy: cài thư viện giao diện (npm install)..."
  (cd "$ROOT/frontend" && npm install >"$LOGS/npm-install.log" 2>&1) || { loi "npm install lỗi, xem .demo-logs/npm-install.log"; exit 1; }
fi
(cd "$ROOT/frontend" && exec npm run dev:backend -- --port 5173 --strictPort) >"$LOGS/frontend.log" 2>&1 &
PIDS+=("$!")
cho_san_sang "Giao diện" "http://localhost:5173/" "$LOGS/frontend.log" 120

# ---------- 4. Xong ----------
URL="http://localhost:5173/#/"
cat <<EOF

============================================================
 Demo đã chạy: $URL
   - Dịch vụ AI : http://127.0.0.1:8001/docs
   - Backend    : http://127.0.0.1:8000/api/health
 Cần Internet (LLM gọi qua mạng), mỗi câu trả lời khoảng 10-15 giây.
 Bấm Ctrl + C để tắt hết.
============================================================
EOF

if [ "$MO_TRINH_DUYET" = 1 ]; then
  if command -v cmd.exe >/dev/null 2>&1; then cmd.exe //c start "" "$URL" >/dev/null 2>&1
  elif command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1
  fi
fi

# Giữ script chạy; dịch vụ nào tự tắt thì báo và dừng cả demo
while true; do
  for pid in "${PIDS[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      loi "Một dịch vụ vừa dừng bất ngờ. Xem log trong .demo-logs/ (ai_service.log, backend.log, frontend.log)."
      exit 1
    fi
  done
  sleep 3
done
