# Apache Jena Fuseki 部署指南 (C-UAS Ontology)

> 一键启动 Apache Jena Fuseki 并预加载 [cuas-ontology.ttl](./cuas-ontology.ttl)
> 版本: V1.0 (配套《反无人机体系本体模型技术方案》第 4 章)

---

## 📋 目录

- [环境要求](#环境要求)
- [一键启动](#一键启动)
- [访问端点](#访问端点)
- [SPARQL 示例查询](#sparql-示例查询)
- [认证与授权](#认证与授权)
- [常用命令](#常用命令)
- [配置自定义](#配置自定义)
- [数据持久化](#数据持久化)
- [故障排查](#故障排查)

---

## 🛠️ 环境要求

| 组件 | 最低版本 | 推荐版本 | 备注 |
|---|---|---|---|
| Docker | 20.10+ | 24.0+ | 容器引擎 |
| Docker Compose | v2.0+ | v2.20+ | 编排工具（v2 插件） |
| 可用内存 | 1 GB | 2 GB+ | JVM 堆通过 `JAVA_OPTIONS` 配置 |
| 可用磁盘 | 500 MB | 2 GB+ | 镜像 + TDB2 数据库 |

> 验证环境：
> ```bash
> docker --version        # Docker 版本
> docker compose version  # Compose v2 版本（注意是空格，非连字符）
> ```

---

## 🚀 一键启动

```bash
# 1. 进入工作目录
cd /sandbox/workspace

# 2. (可选) 设置 admin 密码，生产环境务必修改
export ADMIN_PASSWORD="YourStrongPassword"

# 3. 一键启动 (后台运行)
docker compose up -d

# 4. 查看启动日志
docker compose logs -f fuseki
```

启动成功后日志会显示：

```
===============================================
Apache Jena Fuseki (C-UAS) is ready!
  Web UI:           http://localhost:3030
  SPARQL Query:     http://localhost:3030/cuas/query
  SPARQL Update:    http://localhost:3030/cuas/update
  Admin user:       admin
  Admin password:   ********
===============================================
```

> 💡 **首次启动**会自动：
> 1. 初始化 `shiro.ini` 并注入 `ADMIN_PASSWORD`
> 2. 启动 Fuseki 主进程
> 3. 创建 TDB2 dataset `/cuas`
> 4. 上传 `cuas-ontology.ttl` 到默认图

---

## 🌐 访问端点

启动后可通过浏览器或 curl 访问以下端点：

| 端点 | URL | 认证 | 说明 |
|---|---|---|---|
| **Web UI** | <http://localhost:3030> | 匿名 | Fuseki 主控制台 |
| **数据浏览** | <http://localhost:3030/#/dataset/cuas/query> | 匿名 | 可视化查询 `/cuas` |
| **SPARQL Query** | <http://localhost:3030/cuas/query> | 匿名 | SPARQL 1.1 Query |
| **SPARQL Update** | <http://localhost:3030/cuas/update> | admin | SPARQL 1.1 Update |
| **数据 GSP** | <http://localhost:3030/cuas/data> | admin | 直接读写 RDF |
| **管理 API** | <http://localhost:3030/$/datasets> | admin | dataset 管理 |
| **健康检查** | <http://localhost:3030/$/ping> | 匿名 | 返回 `OK` |
| **服务器状态** | <http://localhost:3030/$/stats> | 匿名 | 运行时指标 |

> ⚠️ 默认密码：`admin123`（生产环境请通过 `ADMIN_PASSWORD` 环境变量覆盖！）

---

## 🔍 SPARQL 示例查询

以下查询示例从 [cuas-ontology-README.md](./cuas-ontology-README.md) 复制并扩展，均已通过 `/cuas/query` 端点验证。

### 示例 1：列出所有 Mission

```bash
curl "http://localhost:3030/cuas/query" \
  --data-urlencode "query=
PREFIX cuas: <http://cuas-ontology.org/cuas#>
SELECT ?m ?id WHERE { 
  ?m a cuas:Mission ; 
     cuas:missionId ?id 
} ORDER BY ?id"
```

### 示例 2：发现识别准确率低于 0.85 的 Mission（触发 SWRL R2）

```bash
curl "http://localhost:3030/cuas/query" \
  --data-urlencode "query=
PREFIX cuas: <http://cuas-ontology.org/cuas#>
SELECT ?m ?acc WHERE {
  ?m a cuas:Mission ; cuas:measuredBy ?em .
  ?em cuas:metricName \"IdentificationAccuracy\" ;
      cuas:metricValue ?acc .
  FILTER (?acc < 0.85)
}"
```

### 示例 3：枚举 8 个核心 Object Type (类层次)

```bash
curl "http://localhost:3030/cuas/query" \
  --data-urlencode "query=
PREFIX cuas: <http://cuas-ontology.org/cuas#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
SELECT ?class ?label WHERE {
  ?class rdfs:subClassOf+ cuas:DomainEntity ;
         a owl:Class ;
         rdfs:label ?label .
  FILTER (lang(?label) = 'zh')
} ORDER BY ?class"
```

### 示例 4：枚举 10 个核心 Link Type (ObjectProperty)

```bash
curl "http://localhost:3030/cuas/query" \
  --data-urlencode "query=
PREFIX cuas: <http://cuas-ontology.org/cuas#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
SELECT ?prop ?label ?domain ?range WHERE {
  ?prop a owl:ObjectProperty ;
        rdfs:label ?label ;
        rdfs:domain ?domain ;
        rdfs:range ?range .
  FILTER (lang(?label) = 'zh')
} ORDER BY ?prop"
```

### 示例 5：统计当前知识库三元组数与 8 个核心类实例数

```bash
curl "http://localhost:3030/cuas/query" \
  --data-urlencode "query=
PREFIX cuas: <http://cuas-ontology.org/cuas#>
SELECT 
  (COUNT(*) AS ?totalTriples)
  (SUM(IF(?s IN (cuas:Mission, cuas:Scenario, cuas:TechnicalCapability, 
                cuas:Equipment, cuas:EffectMetric, cuas:Threat, 
                cuas:Asset, cuas:Operator), 1, 0)) AS ?coreObjectInstances)
WHERE { ?s ?p ?o }"
```

> 💡 **性能基准**（配套主报告 5.1 节）：
> - P50 查询延迟 ≤ 50 ms
> - P95 查询延迟 ≤ 200 ms
> - 启动到就绪时间 < 60 s

---

## 🔐 认证与授权

| 用户名 | 密码来源 | 角色 |
|---|---|---|
| `admin` | `$ADMIN_PASSWORD` 环境变量（默认 `admin123`） | 全部管理权限 |

**默认授权规则**（见 [`shiro.ini`](./shiro.ini)）：

- ✅ **匿名**：`/$/ping`、`/$/stats/**`、`/cuas/query`、`/cuas`（只读）
- 🔒 **需要 admin**：`/cuas/update`、`/cuas/data`、`/cuas/upload`、`/$/datasets/**`、`/$/admin/**`

**修改默认密码**：

```bash
# 方法 1: 环境变量（推荐）
export ADMIN_PASSWORD="MyStr0ng!Pass"
docker compose up -d

# 方法 2: 在 docker-compose.yml 中硬编码（不推荐用于生产）
# environment:
#   ADMIN_PASSWORD: MyStr0ng!Pass

# 方法 3: 使用 .env 文件
echo "ADMIN_PASSWORD=MyStr0ng!Pass" > .env
docker compose up -d
```

> 💡 **注意**：修改密码后**必须删除旧数据卷**才能生效（旧 shiro.ini 已固化在卷中）：
> ```bash
> docker compose down
> docker volume rm cuas-fuseki-data
> docker compose up -d
> ```

---

## 🛑 常用命令

| 用途 | 命令 |
|---|---|
| **一键启动** | `docker compose up -d` |
| **查看实时日志** | `docker compose logs -f fuseki` |
| **查看最近 100 行日志** | `docker compose logs --tail=100 fuseki` |
| **停止（保留数据卷）** | `docker compose down` |
| **停止并删除数据卷** ⚠️ | `docker compose down -v` |
| **重启** | `docker compose restart fuseki` |
| **进入容器调试** | `docker compose exec fuseki bash` |
| **查看健康状态** | `docker compose ps` |
| **重新构建镜像** | `docker compose build --no-cache` |
| **查看资源占用** | `docker stats cuas-fuseki` |

---

## ⚙️ 配置自定义

### 调整 JVM 内存

编辑 `docker-compose.yml`：

```yaml
environment:
  JAVA_OPTIONS: "-Xmx4g -Xms2g -Dfile.encoding=UTF-8"
```

### 暴露到非默认端口

```yaml
ports:
  - "13030:3030"   # 主机 13030 -> 容器 3030
```

### 挂载额外数据卷（用于导入大型数据集）

```yaml
volumes:
  - fuseki-data:/fuseki
  - ./my-extras:/fuseki-extra   # 自动出现在 $FUSEKI_BASE/extra
```

> 💡 `/fuseki-extra` 是 stain 镜像的约定目录，启动时会自动软链接到 `$FUSEKI_BASE/extra`。

### 使用绝对路径挂载

```yaml
volumes:
  - /var/fuseki/databases:/fuseki
  - /var/fuseki/config:/fuseki-extra
```

---

## 💾 数据持久化

- **命名卷** `cuas-fuseki-data` 挂载到容器 `/fuseki` 目录
- 持久化内容：
  - TDB2 数据库文件 (`/fuseki/databases/cuas/`)
  - `shiro.ini`（含已注入的密码）
  - Fuseki 运行时配置 (`config.ttl`)

**查看数据卷**：

```bash
docker volume inspect cuas-fuseki-data
```

**手动备份**：

```bash
# 备份
docker run --rm -v cuas-fuseki-data:/source -v $(pwd):/backup \
    alpine tar czf /backup/fuseki-backup-$(date +%Y%m%d).tar.gz -C /source .

# 恢复
docker run --rm -v cuas-fuseki-data:/target -v $(pwd):/backup \
    alpine tar xzf /backup/fuseki-backup-20260805.tar.gz -C /target
```

---

## 🩺 故障排查

### 问题 1：端口 3030 被占用

```
Error response from daemon: driver failed programming external connectivity 
on endpoint cuas-fuseki: bind: address already in use
```

**解决方法**：

```bash
# 查看占用 3030 的进程
sudo lsof -i :3030 || netstat -tlnp | grep 3030

# 方案 A: 杀掉占用进程
sudo kill -9 <PID>

# 方案 B: 修改 docker-compose.yml 端口映射
#   ports:
#     - "13030:3030"
```

### 问题 2：访问 Web UI 显示 404

**可能原因**：Fuseki 启动中或健康检查未通过。

```bash
# 查看容器状态
docker compose ps

# 预期输出:
# NAME          STATUS                   PORTS
# cuas-fuseki   Up X minutes (healthy)   0.0.0.0:3030->3030/tcp

# 查看启动日志
docker compose logs fuseki | tail -50
```

### 问题 3：登录提示 401 Unauthorized

**可能原因**：`ADMIN_PASSWORD` 修改后未清理旧数据卷。

```bash
# 重新初始化（⚠️ 会清空所有数据！先备份）
docker compose down
docker volume rm cuas-fuseki-data
ADMIN_PASSWORD="NewPassword" docker compose up -d
```

### 问题 4：上传 ontology 失败

查看详细日志：

```bash
docker compose logs fuseki 2>&1 | grep -E "Uploading|HTTP|ERROR"
```

可能原因：
1. **TTL 文件语法错误** → 用 Protégé 5.6 验证
2. **dataset 名称冲突** → 清理数据卷后重启
3. **认证失败** → 检查 `ADMIN_PASSWORD`

### 问题 5：容器启动后立即退出

```bash
# 查看完整日志
docker compose logs --no-color fuseki

# 常见原因: FUSEKI_BASE 权限问题
docker compose exec fuseki ls -la /fuseki

# 修复: 重置数据卷
docker compose down
docker volume rm cuas-fuseki-data
docker compose up -d
```

### 问题 6：内存溢出 (OOM)

调整 JVM 堆：

```yaml
environment:
  JAVA_OPTIONS: "-Xmx1g -Xms512m"
```

### 问题 7：健康检查一直显示 unhealthy

查看容器内 Fuseki 进程：

```bash
docker compose exec fuseki ps aux | grep fuseki
docker compose exec fuseki curl -v http://localhost:3030/\$/ping
```

如果 `/$/ping` 返回 200 但 docker 显示 unhealthy，检查 `HEALTHCHECK` 中的 `$$` 转义是否正确。

### 问题 8：使用 Apache Jena 6.x 的 API

当前部署使用 **Jena 5.1.0**。如需 6.x：

1. 修改 `Dockerfile.fuseki`：`FROM stain/jena-fuseki:5.1.0` → 等待 stain 发布 6.x 标签
2. 或自行构建（参考 [jena-docker 文档](https://github.com/stain/jena-docker)）

---

## 📚 参考资料

- **Apache Jena 官方文档**：<https://jena.apache.org/documentation/fuseki2/>
- **stain/jena-fuseki 仓库**：<https://github.com/stain/jena-docker/tree/master/jena-fuseki>
- **SPARQL 1.1 规范**：<https://www.w3.org/TR/sparql11-query/>
- **C-UAS Ontology README**：[cuas-ontology-README.md](./cuas-ontology-README.md)
- **主报告**：《反无人机体系本体模型技术方案》第 4 章

---

## 📝 镜像版本说明

| 组件 | 版本 | 备注 |
|---|---|---|
| Apache Jena Fuseki | 5.1.0 | stain/jena-fuseki 镜像内嵌 |
| Java (JRE) | 21 LTS | eclipse-temurin:21-jre-alpine |
| 基础镜像 | `stain/jena-fuseki:5.1.0` | Apache Jena PMC 维护 |
| 启动到就绪 | ~30-60 秒 | 取决于主机性能 |

> ℹ️ **关于 `apache/jena-fuseki` 镜像**：截至 2026 年 8 月，Docker Hub 上 `apache/jena-fuseki` 命名空间未发布官方镜像。本部署使用 `stain/jena-fuseki:5.1.0`，由 Apache Jena PMC 成员 Stian Soiland-Reyes 维护，**直接下载官方 Apache 二进制并验证 SHA512**，未做任何修改。仓库：<https://github.com/stain/jena-docker>。
