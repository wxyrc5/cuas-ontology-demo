"""Generate the authoritative technical snapshot and freeze stale deliverables."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PACKAGE_ROOT / "07_文档"
OUTPUT_JSON = DOCS_DIR / "当前技术版本清单.json"
OUTPUT_MARKDOWN = DOCS_DIR / "当前技术版本清单.md"
PUBLIC_MODE = (PACKAGE_ROOT / "PUBLIC_TECHNICAL_REPOSITORY").is_file()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return path.relative_to(PACKAGE_ROOT).as_posix()


def record(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    stat = path.stat()
    return {
        "path": relative(path),
        "bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(
            timespec="seconds"
        ),
        "sha256": sha256(path),
    }


def files_under(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        yield path


def records(paths: Iterable[Path]) -> list[dict]:
    unique = sorted({path.resolve() for path in paths}, key=lambda item: relative(item).lower())
    return [record(path) for path in unique]


def source_tree_digest(groups: dict[str, list[dict]]) -> str:
    digest = hashlib.sha256()
    for role in sorted(groups):
        for item in sorted(groups[role], key=lambda row: row["path"].lower()):
            digest.update(
                f"{role}\0{item['path']}\0{item['sha256']}\n".encode("utf-8")
            )
    return digest.hexdigest().upper()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    validation_dir = PACKAGE_ROOT / "05_Notebook与数据" / "验证输出"
    technical = load_json(validation_dir / "technical_acceptance_summary.json")
    decision = load_json(validation_dir / "指标裁决.json")
    execution = load_json(validation_dir / "最新执行" / "execution_manifest.json")
    streamlit_acceptance = load_json(validation_dir / "streamlit_acceptance.json")
    current_metrics = load_json(
        PACKAGE_ROOT / "03_源码" / "streamlit_app" / "data" / "current_metrics.json"
    )

    if technical.get("all_passed") is not True:
        raise ValueError("Technical acceptance is not passed")
    if decision.get("summary", {}).get("fail") != 0:
        raise ValueError("Metric adjudication contains one or more FAIL results")
    if execution.get("status") != "passed":
        raise ValueError("Notebook execution manifest is not passed")
    if streamlit_acceptance.get("status") != "passed":
        raise ValueError("Streamlit acceptance is not passed")
    expected_packages = {
        20: 1, 25: 2, 30: 2, 40: 2,
        50: 3, 60: 3, 75: 4, 100: 5,
    }
    actual_packages = {
        int(item["threat_count"]): item["adaptive_minimum_resource_packages"]
        for item in current_metrics["ooda"]["resource_scaling"]["minimum_packages"]
    }
    if actual_packages != expected_packages:
        raise ValueError(f"Resource scaling snapshot is stale: {actual_packages}")

    model_dir = PACKAGE_ROOT / "03_源码" / "本体模型"
    canonical_model = [
        model_dir / "cuas-ontology.ttl",
        model_dir / "cuas-data-valid.ttl",
        model_dir / "cuas-data-test.ttl",
        model_dir / "cuas-shapes.ttl",
    ]

    app_dir = PACKAGE_ROOT / "03_源码" / "streamlit_app"
    generated_app_snapshot = app_dir / "data" / "current_metrics.json"
    canonical_app = [
        path for path in files_under(app_dir) if path != generated_app_snapshot
    ]

    notebook_dir = PACKAGE_ROOT / "05_Notebook与数据"
    canonical_notebooks = [
        notebook_dir / "notebook_01_ontology_validation.ipynb",
        notebook_dir / "notebook_02_ooda_simulation.ipynb",
        notebook_dir / "notebook_03_bayesian_adaptive.ipynb",
        notebook_dir / "notebook_04_demo_end_to_end.ipynb",
        notebook_dir / "README.md",
    ]

    script_dir = PACKAGE_ROOT / "06_部署脚本"
    active_script_names = [
        ".env.example",
        "environment.yml",
        "requirements-local.txt",
        "安装本地环境.ps1",
        "启动本地项目.ps1",
        "启动Jupyter.ps1",
        "执行全部Notebook.ps1",
        "执行技术验收.ps1",
        "export_current_metrics.py",
        "fix_notebook_fonts.py",
        "generate_offline_maps.py",
        "generate_release_manifest.py",
        "repair_bayesian_notebook.py",
        "repair_end_to_end_notebook.py",
        "repair_ontology_notebook.py",
        "repair_ooda_notebook.py",
        "run_notebooks.py",
        "sync_streamlit_deploy.ps1",
        "validate_final_state.py",
        "validate_ontology_consistency.py",
        "verify_streamlit_app.py",
        "smoke_test_streamlit.ps1",
    ]
    active_scripts = [script_dir / name for name in active_script_names]

    canonical_docs = [
        PACKAGE_ROOT / "README.md",
        DOCS_DIR / "版本治理与融合决策.md",
        DOCS_DIR / "GitHub远端历史审计与发布策略.md",
        DOCS_DIR / "项目完成度与证据审计.md",
        DOCS_DIR / "事实口径与答辩边界.md",
        DOCS_DIR / "本地运行说明.md",
        DOCS_DIR / "README.md",
        PACKAGE_ROOT / "01_参赛交付物" / "README.md",
        PACKAGE_ROOT / "01_参赛交付物" / "00_暂停使用_待第7和第8步更新.md",
    ]
    public_controls = [
        PACKAGE_ROOT / "PUBLIC_TECHNICAL_REPOSITORY",
        PACKAGE_ROOT / "PUBLIC_REPOSITORY.md",
        PACKAGE_ROOT / ".gitignore",
    ] if PUBLIC_MODE else []
    auxiliary_3d = list(files_under(PACKAGE_ROOT / "03_源码" / "threejs_app"))

    source_groups = {
        "canonical_formal_model": records(canonical_model),
        "canonical_streamlit_source": records(canonical_app),
        "canonical_notebooks": records(canonical_notebooks),
        "active_reproducibility_tools": records(active_scripts),
        "canonical_governance_docs": records(canonical_docs),
        "auxiliary_threejs_source": records(auxiliary_3d),
    }
    if PUBLIC_MODE:
        source_groups["public_repository_controls"] = records(public_controls)
    tree_hash = source_tree_digest(source_groups)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    snapshot_id = f"ZX2026-TECH-{generated_at[:10].replace('-', '')}-{tree_hash[:12]}"

    evidence_paths = [
        validation_dir / "metrics_notebook_01.json",
        validation_dir / "metrics_notebook_02.json",
        validation_dir / "metrics_notebook_03.json",
        validation_dir / "指标裁决.json",
        validation_dir / "最新执行" / "execution_manifest.json",
        validation_dir / "streamlit_acceptance.json",
        validation_dir / "ontology_consistency_report.json",
        validation_dir / "technical_acceptance_summary.json",
        validation_dir / "swarm_resource_scaling_grid.csv",
        validation_dir / "swarm_resource_scaling_minimum.csv",
        validation_dir / "swarm_resource_scaling_thresholds.csv",
        validation_dir / "ooda_coordination_parameters_100_swarm_6_packages.csv",
        validation_dir / "fig2_5_resource_scaling.png",
        validation_dir / "action_feedback_demo.json",
        validation_dir / "action_feedback_writeback.ttl",
        validation_dir / "live_streamlit_smoke.json",
        generated_app_snapshot,
    ]

    deliverable_dir = PACKAGE_ROOT / "01_参赛交付物"
    warning_files = {
        "README.md",
        "00_暂停使用_待第7和第8步更新.md",
    }
    frozen_top_level = [] if PUBLIC_MODE else [
        path
        for path in sorted(deliverable_dir.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.name not in warning_files
    ]
    frozen_records = records(frozen_top_level)
    required_frozen_extensions = {".docx", ".pdf", ".pptx", ".mp4", ".zip"}
    actual_frozen_extensions = {Path(item["path"]).suffix.lower() for item in frozen_records}
    if not PUBLIC_MODE and not required_frozen_extensions.issubset(actual_frozen_extensions):
        raise ValueError("Frozen deliverable inventory is unexpectedly incomplete")

    deferred_generator_names = [
        "构建匿名技术包.ps1",
        "build_competition_deck.mjs",
        "build_competition_proposal.py",
        "build_review_video_deck.mjs",
        "export_review_video.ps1",
        "render_docx_workspace.py",
    ]
    deferred_generators = [] if PUBLIC_MODE else records(
        script_dir / name for name in deferred_generator_names
    )

    official_files = records(files_under(PACKAGE_ROOT / "00_官方材料"))
    history_roots = [
        PACKAGE_ROOT / "01_参赛交付物" / "历史版本",
        PACKAGE_ROOT / "04_可视化" / "历史版本",
        PACKAGE_ROOT / "05_Notebook与数据" / "历史版本",
        PACKAGE_ROOT / "06_部署脚本" / "历史版本",
    ]
    history_summary = []
    for root in history_roots:
        history_files = list(files_under(root)) if root.is_dir() else []
        history_summary.append(
            {
                "path": relative(root),
                "files": len(history_files),
                "bytes": sum(path.stat().st_size for path in history_files),
                "status": "REFERENCE_ONLY_DO_NOT_RUN_OR_SUBMIT",
            }
        )

    report = {
        "schema_version": 1,
        "generated_at": generated_at,
        "snapshot_id": snapshot_id,
        "status": (
            "PUBLIC_TECHNICAL_BASELINE_VERIFIED_SUBMISSION_ARTIFACTS_EXCLUDED"
            if PUBLIC_MODE
            else "TECHNICAL_BASELINE_VERIFIED_SUBMISSION_ARTIFACTS_FROZEN"
        ),
        "package_root": str(PACKAGE_ROOT),
        "git_repository_present": (PACKAGE_ROOT / ".git").is_dir()
        or (PACKAGE_ROOT.parent / ".git").is_dir(),
        "source_tree_sha256": tree_hash,
        "source_groups": source_groups,
        "source_file_count": sum(len(items) for items in source_groups.values()),
        "evidence": {
            "technical_acceptance_all_passed": technical["all_passed"],
            "technical_acceptance_checks": len(technical["checks"]),
            "metric_adjudication_summary": decision["summary"],
            "notebook_status": execution["status"],
            "notebook_code_cells": sum(
                item["executed_code_cells"] for item in execution["notebooks"]
            ),
            "streamlit_status": streamlit_acceptance["status"],
            "streamlit_pages": len(streamlit_acceptance["pages"]),
            "resource_minimum_packages": actual_packages,
            "files": records(evidence_paths),
        },
        "generated_mirrors": [
            {
                "path": "03_源码/streamlit_cloud_deploy",
                "authority": "generated_from_03_源码/streamlit_app",
                "edit_directly": False,
                "verification": (
                    f"{len(canonical_app)}/{len(canonical_app)} canonical files "
                    "covered by deployment-mirror verification"
                ),
            },
            {
                "path": relative(generated_app_snapshot),
                "authority": "generated_from_notebook_metrics_and_acceptance",
                "edit_directly": False,
            },
        ],
        "frozen_submission_artifacts": {
            "status": (
                "EXCLUDED_FROM_PUBLIC_TECHNICAL_REPOSITORY"
                if PUBLIC_MODE else "FROZEN_DO_NOT_SUBMIT"
            ),
            "reason": (
                "Submission artifacts are intentionally excluded from the public technical repository."
                if PUBLIC_MODE else
                "User deferred steps 7 and 8; these artifacts predate the current formal "
                "ontology, Bayesian, full-loop OODA and resource-scaling evidence."
            ),
            "warning": "01_参赛交付物/00_暂停使用_待第7和第8步更新.md",
            "files": frozen_records,
        },
        "deferred_submission_generators": {
            "status": (
                "EXCLUDED_FROM_PUBLIC_TECHNICAL_REPOSITORY"
                if PUBLIC_MODE else "DO_NOT_RUN_UNTIL_STEPS_7_AND_8_RESUME"
            ),
            "files": deferred_generators,
        },
        "official_reference_files": official_files,
        "reference_only_roots": [
            "02_SCI论文",
            "04_可视化",
            "C-UAS-Final-Package (outside this package; visual reference only)",
            "github.com/wxyrc5/cuas-ontology-demo (early remote snapshot only)",
        ],
        "history_summary": history_summary,
        "rules": [
            "Edit 03_源码/streamlit_app, never edit streamlit_cloud_deploy directly.",
            "Only four top-level canonical notebooks are executable evidence; history is excluded.",
            "Use 指标裁决.json for every numeric claim and preserve synthetic/not-field-test wording.",
            "Treat GitHub main as an early snapshot; preserve its history and publish only through an approved consolidation branch and PR.",
            "Do not submit any current file in 01_参赛交付物 until steps 7 and 8 resume.",
            "Run 执行技术验收.ps1 after every source or metric change; it regenerates this manifest.",
        ],
        "deferred_scope": technical["deferred_scope"],
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    evidence = report["evidence"]
    markdown = [
        "# 当前技术版本清单",
        "",
        f"> 状态：**{report['status']}**  ",
        f"> 快照编号：`{snapshot_id}`  ",
        f"> 生成时间：{generated_at}  ",
        f"> 源文件树 SHA-256：`{tree_hash}`",
        "",
        "## 当前结论",
        "",
        f"- 技术终审：**{evidence['technical_acceptance_checks']}/{evidence['technical_acceptance_checks']} 通过**；",
        f"- 指标裁决：**{evidence['metric_adjudication_summary']['pass']} PASS / {evidence['metric_adjudication_summary']['fail']} FAIL / {evidence['metric_adjudication_summary']['report_only']} REPORT_ONLY**；",
        f"- Notebook：**{evidence['notebook_code_cells']}/{evidence['notebook_code_cells']}** 代码单元；Streamlit：**{evidence['streamlit_pages']}/{evidence['streamlit_pages']}** 页面；",
        "- 协调感知点估计 Pk≥0.75 最少包数：20/25/30/40/50/60/75/100 机分别为 **1/2/2/2/3/3/4/5**；",
        f"- Git 仓库存在：**{report['git_repository_present']}**。以本快照编号、源文件树哈希和 Git 提交共同识别版本。",
        "",
        "## 权威源文件",
        "",
        "| 类别 | 文件数 | 规则 |",
        "|---|---:|---|",
        f"| 正式本体 | {len(source_groups['canonical_formal_model'])} | TBox、正向/负向 ABox、SHACL |",
        f"| Streamlit 唯一主线 | {len(source_groups['canonical_streamlit_source'])} | 只编辑 `streamlit_app` |",
        f"| Notebook 源与目录说明 | {len(source_groups['canonical_notebooks'])} | 4 个顶层 Notebook + 1 个 README；只执行四个 Notebook |",
        f"| 复现与验收工具 | {len(source_groups['active_reproducibility_tools'])} | 一键入口为 `执行技术验收.ps1` |",
        f"| 治理文档 | {len(source_groups['canonical_governance_docs'])} | 当前口径和运行说明 |",
        f"| Three.js 辅助源 | {len(source_groups['auxiliary_threejs_source'])} | 次于 Streamlit，不作为指标源 |",
        "",
        "完整路径、字节数、修改时间和 SHA-256 见同名 JSON。",
        "",
        "## 交付物边界",
        "",
        (
            "> DOCX/PDF/PPTX/视频/ZIP 与第 7、8 步生成器均已从公开技术仓库排除。"
            if PUBLIC_MODE else
            "> `01_参赛交付物` 顶层旧成品均为 **FROZEN / DO NOT SUBMIT**。它们含旧指标和旧验证结论；第 7、8 步恢复前不得提交或发送评委。"
        ),
        "",
        "| 文件 | 大小 MiB | SHA-256 前 12 位 |",
        "|---|---:|---|",
    ]
    for item in frozen_records:
        markdown.append(
            f"| `{item['path']}` | {item['bytes'] / (1024 * 1024):.2f} | `{item['sha256'][:12]}` |"
        )
    markdown.extend(
        [
            "",
            "## 不得混用",
            "",
            "- `streamlit_cloud_deploy` 是派生镜像，不得手工修改；",
            "- `历史版本`、旧实验、旧生成器不得运行或引用；",
            "- `C-UAS-Final-Package` 仅保留二维/三维修复参考身份；",
            "- GitHub 仓库是早期远程快照，不能反向覆盖当前本地技术主线；",
            "- 当前 DOCX/PDF/PPTX/视频/ZIP 均未随本轮技术结果重建。",
            "",
            "## 更新方式",
            "",
            "修改任一正式源文件后，运行：",
            "",
            "```powershell",
            ".\\06_部署脚本\\执行技术验收.ps1",
            "```",
            "",
            "只有该命令全部通过并生成新的快照编号，才可称为新的技术基线。",
        ]
    )
    OUTPUT_MARKDOWN.write_text("\n".join(markdown) + "\n", encoding="utf-8")

    print(f"SNAPSHOT_ID={snapshot_id}")
    print(f"SOURCE_FILES={report['source_file_count']}")
    print(f"FROZEN_SUBMISSION_FILES={len(frozen_records)}")
    print(f"JSON_MANIFEST={OUTPUT_JSON}")
    print(f"MARKDOWN_MANIFEST={OUTPUT_MARKDOWN}")


if __name__ == "__main__":
    main()
