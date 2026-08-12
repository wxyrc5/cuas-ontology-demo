#!/bin/bash
# =============================================================================
# init-fuseki.sh - Apache Jena Fuseki 自定义启动脚本 (C-UAS Ontology 专用)
# =============================================================================
# 职责:
#   1. 首次启动时初始化 shiro.ini 并注入 ${ADMIN_PASSWORD}
#   2. 后台启动 fuseki-server,前台用 wait 保活容器
#   3. 等待 Fuseki 就绪
#   4. 创建 FUSEKI_DATASET_* 指定的 dataset (例如 /cuas)
#   5. 加载 cuas-ontology.ttl 到 /cuas dataset (仅在 dataset 为空时执行, 幂等)
# =============================================================================
# v1.1 (2026-08-06) 改进:
#   - 修复 exec "$@" & 的写进程错误 (改为标准 "$@" & + wait 模式)
#   - 增加更多调试日志
#   - 增加错误捕获
#   - 增加 fuseki-server 进程意外退出检测
# =============================================================================
set -e

# ----- 颜色日志 -----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')]${NC} $*"; }
err()  { echo -e "${RED}[$(date +'%H:%M:%S')]${NC} $*" >&2; }

# ----- 全局错误捕获 -----
trap 'err "init-fuseki.sh 在第 $LINENO 行失败, 退出码 $?"; exit 1' ERR

# =============================================================================
# Step 1: 初始化 $FUSEKI_BASE/shiro.ini (从 $FUSEKI_HOME/shiro.ini 模板复制)
# =============================================================================
if [ ! -f "$FUSEKI_BASE/shiro.ini" ] ; then
    log "###################################"
    log "Initializing Apache Jena Fuseki (C-UAS)"
    log "###################################"

    if [ ! -f "$FUSEKI_HOME/shiro.ini" ] ; then
        err "FATAL: $FUSEKI_HOME/shiro.ini 不存在, 无法初始化"
        exit 1
    fi

    cp "$FUSEKI_HOME/shiro.ini" "$FUSEKI_BASE/shiro.ini"
    log "  ✓ 复制 $FUSEKI_HOME/shiro.ini -> $FUSEKI_BASE/shiro.ini"

    if [ -z "$ADMIN_PASSWORD" ] ; then
        ADMIN_PASSWORD=$(pwgen -s 15 2>/dev/null || head -c 12 /dev/urandom | base64)
        warn "  ADMIN_PASSWORD 未设置, 随机生成:"
        warn "    admin=$ADMIN_PASSWORD"
        warn "    >>> 请保存此密码! <<<"
    fi
fi

# =============================================================================
# Step 2: 用 envsubst 替换 ${ADMIN_PASSWORD} 占位符
# =============================================================================
if [ -n "$ADMIN_PASSWORD" ] ; then
    log "注入 ADMIN_PASSWORD 到 shiro.ini ..."
    export ADMIN_PASSWORD
    envsubst '${ADMIN_PASSWORD}' < "$FUSEKI_BASE/shiro.ini" > "$FUSEKI_BASE/shiro.ini.$$" \
        && mv "$FUSEKI_BASE/shiro.ini.$$" "$FUSEKI_BASE/shiro.ini"
    log "  ✓ 密码已注入"
fi

# 验证 shiro.ini 内容
log "shiro.ini 头部预览:"
head -25 "$FUSEKI_BASE/shiro.ini" | sed 's/^/    /'

# =============================================================================
# Step 3: 后台启动 fuseki-server
# =============================================================================
log "启动 fuseki-server ..."
"$@" &
FUSEKI_PID=$!
log "  ✓ fuseki-server PID: $FUSEKI_PID"

# 注册 SIGTERM 处理: 容器停止时优雅关闭 fuseki
trap 'log "收到 SIGTERM, 关闭 fuseki-server (PID $FUSEKI_PID) ..."; kill -TERM $FUSEKI_PID 2>/dev/null; wait $FUSEKI_PID 2>/dev/null; exit 0' TERM INT

# =============================================================================
# Step 4: 等待 Fuseki 启动完成
# =============================================================================
log "等待 Fuseki 就绪 ..."
WAIT_TIMEOUT=120
for i in $(seq 1 $WAIT_TIMEOUT); do
    if curl --output /dev/null --silent --head --fail http://localhost:3030/ 2>/dev/null; then
        log "  ✓ Fuseki 已就绪 (${i}s)"
        break
    fi
    if ! kill -0 $FUSEKI_PID 2>/dev/null; then
        err "ERROR: fuseki-server 进程在启动期间退出, 请检查日志"
        exit 1
    fi
    sleep 1
done

# 二次确认: 验证 $/ping
if ! curl --silent --fail "http://localhost:3030/\$/ping" >/dev/null 2>&1; then
    err "ERROR: Fuseki 启动 ${WAIT_TIMEOUT}s 后仍未响应 ping"
    exit 1
fi
log "  ✓ /\$/ping OK"

# =============================================================================
# Step 5: 创建 FUSEKI_DATASET_* 环境变量指定的 dataset
# =============================================================================
TDB_VERSION='tdb'
if [ -n "${TDB+x}" ] && [ "${TDB}" = "2" ] ; then
    TDB_VERSION='tdb2'
fi
log "TDB 版本: $TDB_VERSION"

DATASETS_CREATED=0
printenv | grep -E "^FUSEKI_DATASET_" | while read env_var ; do
    dataset=$(echo "$env_var" | grep -oE "=.*$" | sed 's/^=//')
    if [ -z "$dataset" ] ; then
        continue
    fi
    log "确保 dataset '$dataset' (类型=$TDB_VERSION) 存在 ..."

    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "admin:${ADMIN_PASSWORD}" \
        "http://localhost:3030/\$/datasets/${dataset}")
    if [ "$HTTP_CODE" = "200" ]; then
        log "  -> dataset '$dataset' 已存在, 跳过创建"
    else
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -u "admin:${ADMIN_PASSWORD}" \
            -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' \
            --data "dbName=${dataset}&dbType=${TDB_VERSION}" \
            "http://localhost:3030/\$/datasets")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
            log "  -> dataset '$dataset' 创建成功 (HTTP $HTTP_CODE)"
        else
            warn "  -> dataset '$dataset' 创建返回 HTTP $HTTP_CODE"
        fi
    fi
done

# 给 dataset 配置加载一点时间
sleep 2

# =============================================================================
# Step 6: 加载 cuas-ontology.ttl 到 /cuas dataset (仅空 dataset 时执行)
# =============================================================================
TTL_FILE="/opt/cuas-ontology.ttl"
TARGET_DATASET="${FUSEKI_ONTOLOGY_DATASET:-cuas}"

if [ -f "$TTL_FILE" ]; then
    log "检查 dataset '$TARGET_DATASET' 是否为空 ..."
    TRIPLES=$(curl -sf -u "admin:${ADMIN_PASSWORD}" \
        "http://localhost:3030/${TARGET_DATASET}/query" \
        --data-urlencode 'query=SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }' \
        -H 'Accept: application/sparql-results+json' 2>/dev/null | \
        grep -oE '"value":"[0-9]+"' | head -1 | grep -oE '[0-9]+' || echo "0")

    if [ "$TRIPLES" = "0" ] || [ -z "$TRIPLES" ]; then
        log "  dataset 为空, 加载 $TTL_FILE ..."
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -u "admin:${ADMIN_PASSWORD}" \
            -H 'Content-Type: text/turtle; charset=utf-8' \
            --data-binary "@$TTL_FILE" \
            "http://localhost:3030/${TARGET_DATASET}/data?default")
        if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "204" ]; then
            log "  ✓ 加载成功 (HTTP $HTTP_CODE)"
        else
            err "ERROR: 本体加载失败 (HTTP $HTTP_CODE)"
            exit 1
        fi
    else
        log "  dataset 已有 $TRIPLES 个三元组, 跳过加载"
    fi
else
    warn "$TTL_FILE 不存在, 跳过本体加载"
fi

# =============================================================================
# Step 7: 打印访问信息
# =============================================================================
log "═══════════════════════════════════════════════════════════════"
log "  ✅ Fuseki 启动完成"
log "═══════════════════════════════════════════════════════════════"
log "  Web UI       : http://localhost:3030"
log "  SPARQL Query : http://localhost:3030/${TARGET_DATASET}/query"
log "  SPARQL Update: http://localhost:3030/${TARGET_DATASET}/update"
log "  Username     : admin"
log "  Password     : ${ADMIN_PASSWORD}"
log "═══════════════════════════════════════════════════════════════"

# =============================================================================
# Step 8: 前台保活, 等待 fuseki-server
# =============================================================================
log "前台保活, 等待 fuseki-server (PID $FUSEKI_PID) ..."

# 持续监控 fuseki-server 进程, 异常退出则容器也退出
while kill -0 $FUSEKI_PID 2>/dev/null; do
    sleep 5
done

err "fuseki-server (PID $FUSEKI_PID) 已退出, 容器终止"
exit 1
