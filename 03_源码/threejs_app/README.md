# Three.js 三维辅助演示

本目录提供三个浏览器三维场景：机场反无、本体关系和概率闭环飞轮。它是答辩中的视觉辅助，当前正式二维/三维机场态势仍以 `../streamlit_app/pages/5_🗺_机场反无.py` 为主。

## 运行

Three.js 模块从 CDN 加载，需要联网。进入本目录后启动本地静态服务器：

```powershell
& ..\..\..\.venv-cuas\python.exe -m http.server 8000 --bind 127.0.0.1
```

访问 `http://127.0.0.1:8000/`。直接双击 HTML 可能因浏览器模块安全策略失败。

## 页面

- `index.html`：三个场景的统一入口；
- `scene_airport.html`：PKX 北京大兴参数化机场三维态势；
- `scene_ontology.html`：8 个 Object Type 与 10 个 Link Type；
- `scene_flywheel.html`：使命—场景—方案—效果反馈环。

## 证据边界

- 所有机场距离、防御层、飞行轨迹、效应器位置和结果均为演示参数，不是机场监管范围、真实部署坐标或装备性能；
- “55 km”只是一项明确标注的参数化演示边界；
- PKX/ZBAD 为北京大兴国际机场代码；
- 随机动画已使用固定种子，刷新后可复现；
- 本目录没有现场测试、WebXR 头显实机验收或武器效能结论。

提交前需联网加载一次并检查浏览器控制台；离线答辩优先使用无需 CDN 的 Streamlit 页面。
