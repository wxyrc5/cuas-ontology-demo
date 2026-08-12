"""Install a deterministic CJK Matplotlib prelude in the four canonical notebooks."""
from __future__ import annotations

from pathlib import Path

import nbformat


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PACKAGE_ROOT / "05_Notebook与数据"
NOTEBOOKS = [
    NOTEBOOK_DIR / "notebook_01_ontology_validation.ipynb",
    NOTEBOOK_DIR / "notebook_02_ooda_simulation.ipynb",
    NOTEBOOK_DIR / "notebook_03_bayesian_adaptive.ipynb",
    NOTEBOOK_DIR / "notebook_04_demo_end_to_end.ipynb",
]
TAG = "cuas-cjk-font"

PRELUDE = """# 可复现中文绘图字体配置（由 fix_notebook_fonts.py 管理）
import matplotlib as mpl
from matplotlib import font_manager as _font_manager

_preferred_cjk_fonts = [
    'Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC',
    'Source Han Sans SC', 'Arial Unicode MS', 'DejaVu Sans'
]
_available_fonts = {item.name for item in _font_manager.fontManager.ttflist}
_cjk_font = next((name for name in _preferred_cjk_fonts if name in _available_fonts), 'DejaVu Sans')
mpl.rcParams['font.sans-serif'] = [_cjk_font, 'DejaVu Sans']
mpl.rcParams['axes.unicode_minus'] = False
print(f'Matplotlib font: {_cjk_font}')
"""


def patch_notebook(path: Path) -> str:
    notebook = nbformat.read(path, as_version=4)
    tagged = [
        cell for cell in notebook.cells
        if cell.cell_type == "code" and TAG in cell.get("metadata", {}).get("tags", [])
    ]
    if tagged:
        tagged[0].source = PRELUDE
        for extra in tagged[1:]:
            notebook.cells.remove(extra)
        action = "updated"
    else:
        cell = nbformat.v4.new_code_cell(PRELUDE)
        cell.metadata["tags"] = [TAG]
        first_code = next(
            (index for index, item in enumerate(notebook.cells) if item.cell_type == "code"),
            len(notebook.cells),
        )
        notebook.cells.insert(first_code, cell)
        action = "inserted"

    for cell in notebook.cells:
        if cell.cell_type != "code" or TAG in cell.get("metadata", {}).get("tags", []):
            continue
        cell.source = cell.source.replace(
            "plt.rcParams['font.sans-serif'] = ['DejaVu Sans']",
            "plt.rcParams['font.sans-serif'] = [_cjk_font, 'DejaVu Sans']",
        ).replace(
            "plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'DejaVu Sans']",
            "plt.rcParams['font.sans-serif'] = [_cjk_font, 'DejaVu Sans']",
        ).replace(
            'plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]',
            'plt.rcParams["font.sans-serif"] = [_cjk_font, "DejaVu Sans"]',
        ).replace(
            'plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "DejaVu Sans"]',
            'plt.rcParams["font.sans-serif"] = [_cjk_font, "DejaVu Sans"]',
        )
        if "# CUAS_CJK_AFTER_SEABORN" not in cell.source:
            for style_call in ("sns.set_style('whitegrid')", 'sns.set_style("whitegrid")'):
                if style_call in cell.source:
                    cell.source = cell.source.replace(
                        style_call,
                        style_call
                        + "\n# CUAS_CJK_AFTER_SEABORN"
                        + "\nplt.rcParams['font.family'] = 'sans-serif'"
                        + "\nplt.rcParams['font.sans-serif'] = [_cjk_font, 'SimHei', 'DejaVu Sans']"
                        + "\nplt.rcParams['axes.unicode_minus'] = False",
                        1,
                    )
                    break

    nbformat.write(notebook, path)
    return action


def main() -> None:
    for notebook_path in NOTEBOOKS:
        if not notebook_path.is_file():
            raise FileNotFoundError(notebook_path)
        print(f"{notebook_path.name}: {patch_notebook(notebook_path)}")


if __name__ == "__main__":
    main()
