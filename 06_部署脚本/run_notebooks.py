"""Execute the four canonical notebooks and write auditable fresh outputs."""
from __future__ import annotations

import hashlib
import importlib.metadata
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parent
NOTEBOOK_ROOT = PACKAGE_ROOT / "05_Notebook与数据"
OUTPUT_ROOT = NOTEBOOK_ROOT / "验证输出" / "最新执行"
STDOUT_ROOT = OUTPUT_ROOT / "文本输出"
JUPYTER_STATE_ROOT = WORKSPACE_ROOT / ".jupyter-cuas"
KERNEL_NAME = "cuas-zx2026"
CANONICAL = (
    "notebook_01_ontology_validation.ipynb",
    "notebook_02_ooda_simulation.ipynb",
    "notebook_03_bayesian_adaptive.ipynb",
    "notebook_04_demo_end_to_end.ipynb",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def configure_kernel() -> None:
    runtime_dir = JUPYTER_STATE_ROOT / "runtime"
    config_dir = JUPYTER_STATE_ROOT / "config"
    data_dir = JUPYTER_STATE_ROOT / "data"
    jupyter_path = JUPYTER_STATE_ROOT / "share" / "jupyter"
    ipython_dir = JUPYTER_STATE_ROOT / "ipython"
    for directory in (runtime_dir, config_dir, data_dir, jupyter_path, ipython_dir):
        directory.mkdir(parents=True, exist_ok=True)
    os.environ["JUPYTER_RUNTIME_DIR"] = str(runtime_dir)
    os.environ["JUPYTER_CONFIG_DIR"] = str(config_dir)
    os.environ["JUPYTER_DATA_DIR"] = str(data_dir)
    os.environ["JUPYTER_PATH"] = str(jupyter_path)
    os.environ["IPYTHONDIR"] = str(ipython_dir)
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ.get("PATH", "")

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    kernel_json = jupyter_path / "kernels" / KERNEL_NAME / "kernel.json"
    if not kernel_json.exists():
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ipykernel",
                "install",
                "--prefix",
                str(JUPYTER_STATE_ROOT),
                "--name",
                KERNEL_NAME,
                "--display-name",
                "C-UAS Python 3.11",
            ],
            check=True,
        )

    kernel = json.loads(kernel_json.read_text(encoding="utf-8"))
    configured_python = Path(kernel["argv"][0]).resolve()
    current_python = Path(sys.executable).resolve()
    if configured_python != current_python:
        raise RuntimeError(
            f"Kernel interpreter mismatch: {configured_python} != {current_python}"
        )


def collect_text_output(notebook: nbformat.NotebookNode) -> str:
    chunks: list[str] = []
    for cell_index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code":
            continue
        for output in cell.get("outputs", []):
            text = ""
            if output.output_type == "stream":
                text = output.get("text", "")
            elif output.output_type in {"execute_result", "display_data"}:
                text = output.get("data", {}).get("text/plain", "")
            elif output.output_type == "error":
                text = "\n".join(output.get("traceback", []))
            if text:
                chunks.append(f"--- cell {cell_index} / {output.output_type} ---\n{text.rstrip()}\n")
    return "\n".join(chunks)


def execute_one(source_path: Path) -> dict:
    started = datetime.now().astimezone()
    start_clock = time.perf_counter()
    notebook = nbformat.read(source_path, as_version=4)
    for cell_index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            compile(cell.source, f"{source_path.name}:cell-{cell_index}", "exec")
    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name=KERNEL_NAME,
        allow_errors=False,
        resources={"metadata": {"path": str(NOTEBOOK_ROOT)}},
        record_timing=True,
    )
    executed = client.execute()
    duration = time.perf_counter() - start_clock

    output_ipynb = OUTPUT_ROOT / f"{source_path.stem}_executed.ipynb"
    output_html = OUTPUT_ROOT / f"{source_path.stem}_executed.html"
    output_text = STDOUT_ROOT / f"{source_path.stem}.txt"
    nbformat.write(executed, output_ipynb)
    html, _ = HTMLExporter(template_name="lab").from_notebook_node(executed)
    output_html.write_text(html, encoding="utf-8")
    output_text.write_text(collect_text_output(executed), encoding="utf-8")

    errors = [
        output
        for cell in executed.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type == "error"
    ]
    return {
        "source": source_path.name,
        "source_sha256": sha256(source_path),
        "executed_notebook": output_ipynb.name,
        "executed_sha256": sha256(output_ipynb),
        "html": output_html.name,
        "text_output": str(output_text.relative_to(OUTPUT_ROOT)),
        "started_at": started.isoformat(timespec="seconds"),
        "duration_seconds": round(duration, 3),
        "code_cells": sum(cell.cell_type == "code" for cell in executed.cells),
        "executed_code_cells": sum(
            cell.cell_type == "code" and cell.execution_count is not None
            for cell in executed.cells
        ),
        "errors": len(errors),
        "status": "passed" if not errors else "failed",
    }


def runtime_manifest() -> dict:
    packages = (
        "streamlit",
        "plotly",
        "rdflib",
        "pyshacl",
        "owlready2",
        "numpy",
        "pandas",
        "scipy",
        "scikit-learn",
        "statsmodels",
        "matplotlib",
        "nbclient",
    )
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "kernel": KERNEL_NAME,
        "working_directory": str(NOTEBOOK_ROOT),
        "packages": {name: importlib.metadata.version(name) for name in packages},
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    configure_kernel()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    STDOUT_ROOT.mkdir(parents=True, exist_ok=True)

    manifest = runtime_manifest()
    manifest["notebooks"] = []
    for name in CANONICAL:
        source_path = NOTEBOOK_ROOT / name
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        notebook = nbformat.read(source_path, as_version=4)
        for cell_index, cell in enumerate(notebook.cells):
            if cell.cell_type == "code":
                compile(cell.source, f"{source_path.name}:cell-{cell_index}", "exec")
    print("Syntax preflight passed for all canonical notebooks.", flush=True)

    for name in CANONICAL:
        source_path = NOTEBOOK_ROOT / name
        print(f"Executing {name} ...", flush=True)
        result = execute_one(source_path)
        manifest["notebooks"].append(result)
        print(
            f"  {result['status']} in {result['duration_seconds']:.1f}s "
            f"({result['executed_code_cells']}/{result['code_cells']} code cells)",
            flush=True,
        )

    manifest["status"] = (
        "passed"
        if all(item["status"] == "passed" for item in manifest["notebooks"])
        else "failed"
    )
    manifest_path = OUTPUT_ROOT / "execution_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Execution manifest: {manifest_path}")
    if manifest["status"] != "passed":
        raise RuntimeError("One or more notebooks failed.")


if __name__ == "__main__":
    main()
