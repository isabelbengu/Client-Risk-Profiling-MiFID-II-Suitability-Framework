"""The generated documentation must match the configuration.

Documentation that has drifted from the configuration is worse than no
documentation: a supervisor reads the document, the client is assessed by the
YAML. `tools/render_docs.py --check` fails if they have parted company.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")


def test_generated_docs_are_up_to_date():
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "render_docs.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "generated docs are stale - run: python3 tools/render_docs.py\n" + result.stderr
    )


def test_every_doc_page_exists():
    expected = {
        "01-regulatory-basis.md",
        "02-methodology.md",
        "03-questionnaire.md",
        "04-mapping-and-portfolios.md",
        "05-esma-control-mapping.md",
        "06-governance.md",
        "07-limitations.md",
        "08-control-index.md",
    }
    assert expected <= set(os.listdir(DOCS))


def test_control_mapping_covers_all_twelve_guidelines():
    text = open(os.path.join(DOCS, "05-esma-control-mapping.md"), encoding="utf-8").read()
    for n in range(1, 13):
        assert f"## Guideline {n} " in text, n


def test_every_control_id_appears_in_the_documentation(cfg):
    text = "".join(
        open(os.path.join(DOCS, name), encoding="utf-8").read() for name in os.listdir(DOCS)
    )
    for control in cfg.scoring["coherence_controls"]:
        assert control["id"] in text, control["id"]


def test_internal_doc_links_resolve():
    pattern = re.compile(r"\]\((\d\d-[a-z0-9-]+\.md)(#[a-z0-9-]+)?\)")
    for name in os.listdir(DOCS):
        text = open(os.path.join(DOCS, name), encoding="utf-8").read()
        for target, _anchor in pattern.findall(text):
            assert os.path.exists(os.path.join(DOCS, target)), f"{name} -> {target}"


def test_readme_links_resolve():
    readme = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    for target in re.findall(r"\]\((docs/[a-z0-9-]+\.md|examples/[^)]+|config/[^)]+|src/[^)]+)\)", readme):
        assert os.path.exists(os.path.join(ROOT, target.split("#")[0])), target
