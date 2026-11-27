"""Claude memory integration: a sandboxed file memory (Anthropic memory tool) that mirrors scraping + ICP learnings."""

from __future__ import annotations

from pathlib import Path

from .schema import ICP
from .store import Store


def make_memory_tool(base_path: str):
    """Anthropic's client-side memory tool backed by a local directory (path-traversal and symlink safe)."""
    from anthropic.lib.tools._beta_builtin_memory_tool import BetaLocalFilesystemMemoryTool

    Path(base_path).mkdir(parents=True, exist_ok=True)
    return BetaLocalFilesystemMemoryTool(base_path=base_path)


def sync_memory(store: Store, icp: ICP, base_path: str) -> None:
    """Write durable, human-readable notes Claude can `view` at the start of every run."""
    root = Path(base_path) / "memories"
    (root / "scraping").mkdir(parents=True, exist_ok=True)
    for domain, notes in store.domain_notes().items():
        (root / "scraping" / f"{domain}.md").write_text(f"# Scraping notes: {domain}\n{notes}\n", encoding="utf-8")
    weights = store.get_weights()
    feedback = store.list_feedback(25)
    lessons = [f"- {f.verdict.upper()} {f.lead_key}: {f.reason or 'no reason given'}" for f in feedback]
    (root / "icp_and_feedback.md").write_text(
        f"# ICP: {icp.name}\n{icp.model_dump_json(indent=2)}\n\n## Learned scoring weights\n"
        + "\n".join(f"- {k}: {v}" for k, v in sorted(weights.items()))
        + "\n\n## Recent operator feedback (newest first)\n"
        + ("\n".join(lessons) or "- none yet")
        + "\n",
        encoding="utf-8",
    )
