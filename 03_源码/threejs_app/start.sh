#!/usr/bin/env bash
# ===========================================================
#  C-UAS Ontology 3D · 一键启动脚本
#  用法: ./start.sh [port]
#  默认端口: 8000
# ===========================================================
set -e

PORT="${1:-${PORT:-8000}}"
HOST="${HOST:-0.0.0.0}"

# 切到脚本所在目录
cd "$(dirname "$0")"

echo "╔══════════════════════════════════════════════╗"
echo "║   🛡️  C-UAS Ontology · 沉浸式 3D 启动器     ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "📁 工作目录 : $(pwd)"
echo "🌐 监听地址 : http://${HOST}:${PORT}/"
echo "🚀 启动中..."
echo ""

# 选择可用的 HTTP 服务器
if command -v python3 >/dev/null 2>&1; then
  echo "✅ 使用 Python 3 内置 HTTP 服务器"
  echo ""
  echo "👉 在浏览器打开: http://localhost:${PORT}/"
  echo "👉 或扫描二维码体验 (VR 头显/手机同局域网):"
  # 打印本机 IP
  if [[ "$OSTYPE" == "darwin"* ]]; then
    IP=$(ifconfig | grep -E "inet [0-9]" | grep -v "127.0.0.1" | awk '{print $2}' | head -1)
  else
    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
  fi
  if [ -n "$IP" ]; then
    echo "   http://${IP}:${PORT}/"
  fi
  echo ""
  echo "⏹️  按 Ctrl+C 停止"
  echo ""
  exec python3 -m http.server "${PORT}" --bind "${HOST}"
elif command -v python >/dev/null 2>&1; then
  echo "✅ 使用 Python 2 内置 HTTP 服务器"
  echo "👉 在浏览器打开: http://localhost:${PORT}/"
  echo "⏹️  按 Ctrl+C 停止"
  echo ""
  exec python -m SimpleHTTPServer "${PORT}"
elif command -v npx >/dev/null 2>&1; then
  echo "✅ 使用 npx http-server"
  echo "👉 在浏览器打开: http://localhost:${PORT}/"
  echo "⏹️  按 Ctrl+C 停止"
  echo ""
  exec npx --yes http-server -p "${PORT}" -a "${HOST}" -c-1
elif command -v php >/dev/null 2>&1; then
  echo "✅ 使用 PHP 内置服务器"
  echo "👉 在浏览器打开: http://localhost:${PORT}/"
  echo "⏹️  按 Ctrl+C 停止"
  echo ""
  exec php -S "${HOST}:${PORT}"
elif command -v ruby >/dev/null 2>&1; then
  echo "✅ 使用 Ruby WEBrick"
  echo "👉 在浏览器打开: http://localhost:${PORT}/"
  echo "⏹️  按 Ctrl+C 停止"
  echo ""
  exec ruby -run -e httpd . -p "${PORT}" -b "${HOST}"
else
  echo "❌ 未找到 Python / Node.js / PHP / Ruby 中的任何一个"
  echo "   请安装其中之一，或直接双击 index.html 打开"
  exit 1
fi