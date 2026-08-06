# 🚀 Streamlit Cloud 部署指南

> **5 分钟**把 C-UAS Ontology 反无人机演示应用部署到 https://share.streamlit.io，
> 拿到一个 **公开可访问的 URL** 给评审专家使用。

---

## ✅ 前置条件

| 项目 | 说明 |
|------|------|
| GitHub 账号 | 用于托管代码（免费） |
| Streamlit Cloud 账号 | 用 GitHub 登录 https://share.streamlit.io （免费） |
| 本机 Git | 推送代码到 GitHub |

不需要服务器、不需要域名、不需要备案。

---

## 📝 步骤 1：上传到 GitHub（2 分钟）

### 1.1 创建 GitHub 仓库
1. 登录 <https://github.com> → 点击右上角 `+` → `New repository`
2. 填写：
   - **Repository name**: `cuas-ontology-demo`
   - **Description**: `C-UAS Ontology · OSREDM 2026 · 反蜂群机场防护杀伤网`
   - **Public** ⚠️ 必须是 Public（否则 Streamlit Cloud 公共部署不可用）
   - 不要勾选 `Add a README file`（本地已有）
3. 点击 `Create repository`

### 1.2 推送代码
在 `streamlit_cloud_deploy/` 目录下执行：

```bash
cd streamlit_cloud_deploy

# 初始化 git 仓库
git init

# 添加所有文件
git add .

# 首次提交
git commit -m "Initial commit: C-UAS Ontology demo for OSREDM 2026"

# 切换到 main 分支
git branch -M main

# 关联到你的 GitHub 仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/cuas-ontology-demo.git

# 推送
git push -u origin main
```

> 💡 第一次推送会要求输入 GitHub 用户名和 Personal Access Token
> （Settings → Developer settings → Personal access tokens → Generate new token，勾选 `repo`）。

推送成功后，到 GitHub 仓库页面应该能看到所有文件，包括 `app.py`、`pages/`、`utils/`、`data/` 等。

---

## 🔗 步骤 2：连接 Streamlit Cloud（1 分钟）

1. 访问 <https://share.streamlit.io>
2. 用 GitHub 账号登录
3. 点击右上角 `Create app`（或 `New app`）
4. 填写部署信息：

| 字段 | 填写 |
|------|------|
| **Repository** | `YOUR_USERNAME/cuas-ontology-demo` |
| **Branch** | `main` |
| **Main file path** | `app.py` |
| **App URL**（可选） | `cuas-demo` → 最终 URL 为 `https://cuas-demo.streamlit.app` |

5. 展开 `Advanced settings`（可选但推荐）：

   - **Python version**: `3.11`
   - **Secrets**: 暂不需要（演示数据已打包在 `data/`）
   - **Requirements file**: `requirements.txt`（默认）

6. 点击 `Deploy!` 🎉

---

## ⏱ 步骤 3：等待部署完成（2-5 分钟）

Streamlit Cloud 会自动执行：

1. ✅ 拉取你的 GitHub 仓库代码
2. ✅ 安装 `runtime.txt` 指定的 Python 3.11
3. ✅ 安装 `packages.txt` 的系统依赖（graphviz、build-essential）
4. ✅ `pip install -r requirements.txt`
5. ✅ 启动 `streamlit run app.py`
6. ✅ 分配公开 URL

部署过程中你可以看到 **实时日志**，如果出错请翻到 `常见问题 Q1`。

**部署成功**的标志：
- 日志最后出现 `You can now view your Streamlit app in your browser.`
- 浏览器自动打开新窗口
- 看到 5 个页面（主页 / 本体浏览 / SPARQL / 贝叶斯 / 机场反无）

你的 URL 形如：
```
https://cuas-demo.streamlit.app
```
或系统自动分配：
```
https://YOUR_USERNAME-cuas-ontology-demo-app-XXXX.streamlit.app
```

---

## 📤 步骤 4：分享 URL

把这个 URL 发给评审专家：

- 📧 **邮件签名**：附在 OSREDM 2026 参赛邮件签名
- 💬 **微信群**：作为参赛材料附件
- 🎬 **抖音/小红书简介**："完整演示见 https://cuas-demo.streamlit.app"
- 📄 **项目方案封面**：附在 `技术方案.pdf` 首页
- 🎤 **答辩 PPT** 最后一页：放 URL + 二维码

> 💡 **建议**：同时把 URL 提交到 OSREDM 2026 比赛系统的 `在线演示` 字段。

---

## ❓ 常见问题

### Q1: 部署失败怎么办？
进入 App 详情页 → `Logs`，查看最后 50 行错误。常见原因：

| 错误信息 | 原因 | 修复 |
|----------|------|------|
| `ModuleNotFoundError: No module named 'xxx'` | `requirements.txt` 缺包 | 添加并 push |
| `Python version X not found` | `runtime.txt` 写了不支持的版本 | 改成 `python-3.11` |
| `FileNotFoundError: data/ontology.json` | data 目录没上传 | 检查 `.gitignore` 没误过滤 |
| `SyntaxError` | 代码有 bug | 本地先 `streamlit run app.py` 测试 |
| `MemoryError` | 数据太大 | 优化 `data/*.json` 大小 |

### Q2: 应用启动很慢怎么办？
Streamlit Cloud 免费版冷启动 30-60 秒（容器唤醒）。
**优化建议**：

1. 升级到 **Streamlit Cloud Pro**（无冷启动）
2. 给所有 `load_*` 函数加 `@st.cache_data`（已默认加了）
3. 把 `data/*.json` 控制在 < 5 MB
4. 减少 import 体积（如移除 `altair` 等非必要依赖）

### Q3: 访问受限怎么办？
- **公开应用**：Streamlit Cloud 公开仓库的 App **默认无访问限制**，任何人都能打开。
- **私密访问**：需要 Pro 账号 + 在 `secrets.toml` 配置邮箱白名单。

### Q4: 怎么更新代码？
```bash
# 修改本地文件后
git add .
git commit -m "Update Bayes AUC display"
git push
```
Streamlit Cloud 会**自动检测** push 事件，在 30 秒内开始重新部署。

### Q5: 应用休眠/下线？
- Streamlit Cloud **免费版** 长期无访问会休眠（资源回收）。
- **保持活跃**：在 `<https://streamlit.io/cloud>` 仪表盘 → App → `Settings` → 关闭 `Always rerun on save` 旁的省电选项。
- **或者**：自己用 cron 定时 ping 一次：
  ```bash
  */10 * * * * curl -s https://cuas-demo.streamlit.app/_stcore/health > /dev/null
  ```

### Q6: 国内访问慢？
Streamlit Cloud 节点在 AWS us-east-1，国内访问可能 1-3 秒延迟。
**解决方案**：
- 申请 OSREDM 2026 主办方用国内镜像分发
- 自建 Cloudflare Tunnel + 域名
- 用 Heroku / Render / Vercel 备用

### Q7: 二维码怎么做？
部署成功后访问 URL，用任意二维码生成器：
```bash
pip install qrcode
python -c "import qrcode; qrcode.make('https://cuas-demo.streamlit.app').save('qr.png')"
```
或在线：<https://www.qrcode-monkey.com/>

---

## ⚡ 性能优化建议

1. **大文件** → 用 [Git LFS](https://git-lfs.github.com/) 或 OSS 外链
2. **数据加载** → 全部加 `@st.cache_data` / `@st.cache_resource`
3. **首屏** → 用 `st.spinner` 包裹慢操作
4. **懒加载** → 在 pages 顶层不做重计算，延迟到用户操作
5. **依赖** → 精简 `requirements.txt`，删除 plotly 之外的 plot 库

---

## 🔧 高级配置

### 自定义主题
修改 `.streamlit/config.toml`：
```toml
[theme]
primaryColor = "#1F4E79"     # 主色（深蓝）
backgroundColor = "#FFFFFF"  # 背景（白）
textColor = "#262730"        # 文本（深灰）
```

### 私密部署（需要 Pro）
1. GitHub 仓库设为 Private
2. Streamlit Cloud Pro 账号
3. 在 App settings 添加合作者

### 绑定自定义域名（Pro）
App settings → `Custom subdomain` → 输入 `cuas-demo` → URL 变为
`https://cuas-demo.streamlit.app`

---

## 📊 部署后验收清单

- [ ] 公开 URL 可访问（无 502 / 404）
- [ ] 5 个页面都能打开
- [ ] 主页 3 大指标正确显示（AUC 0.9958 / OODA < 5s / 8+10+4）
- [ ] 本体浏览页 8 OT 卡片正常
- [ ] SPARQL 页 5 个模板都能跑出结果
- [ ] 贝叶斯实验页滑块可拖动
- [ ] 机场反无页地图正常渲染
- [ ] URL 已分享给评审专家

---

## 🆘 获取帮助

- **Streamlit 官方文档**：<https://docs.streamlit.io/streamlit-community-cloud>
- **OSREDM 2026 技术支持**：support@osredm.example.org
- **项目仓库 Issues**：<https://github.com/YOUR_USERNAME/cuas-ontology-demo/issues>

---

> 🎉 部署成功后，别忘了把 URL 填回 `README.md` 第 18 行！
