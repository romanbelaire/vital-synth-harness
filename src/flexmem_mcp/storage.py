from __future__ import annotations

import json
import shutil
import sqlite3
import uuid
from pathlib import Path


class Library:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.presets = root / "presets"
        self.renders = root / "renders"
        self.presets.mkdir(parents=True, exist_ok=True)
        self.renders.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "library.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.db.execute("""CREATE TABLE IF NOT EXISTS patches (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, prompt TEXT NOT NULL, notes TEXT NOT NULL,
          tags TEXT NOT NULL, preset_path TEXT NOT NULL, render_path TEXT, analysis_json TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS patch_search USING fts5(id UNINDEXED, text)")
        self.db.commit()

    def import_preset(self, source: Path) -> str:
        if source.suffix.lower() != ".vital":
            raise ValueError("Only .vital preset files are accepted")
        json.loads(source.read_text(encoding="utf-8"))
        patch_id = uuid.uuid4().hex
        shutil.copy2(source, self.presets / f"{patch_id}.vital")
        return patch_id

    def preset_path(self, patch_id: str) -> Path:
        path = self.presets / f"{patch_id}.vital"
        if not path.is_file():
            raise KeyError(f"Unknown patch_id: {patch_id}")
        return path

    def accept(self, patch_id: str, name: str, prompt: str, notes: str, tags: list[str], render: Path | None, analysis: dict | None) -> str:
        entry_id = uuid.uuid4().hex
        preset = self.preset_path(patch_id)
        render_path = None
        if render and render.is_file():
            render_path = self.renders / f"{entry_id}.wav"
            shutil.copy2(render, render_path)
        tag_text = " ".join(tags)
        self.db.execute("INSERT INTO patches(id,name,prompt,notes,tags,preset_path,render_path,analysis_json) VALUES(?,?,?,?,?,?,?,?)",
          (entry_id, name, prompt, notes, tag_text, str(preset), str(render_path) if render_path else None, json.dumps(analysis) if analysis else None))
        self.db.execute("INSERT INTO patch_search(id,text) VALUES(?,?)", (entry_id, " ".join((name, prompt, notes, tag_text))))
        self.db.commit()
        return entry_id

    def search(self, query: str, limit: int) -> list[dict]:
        rows = self.db.execute("""SELECT p.*, snippet(patch_search, 1, '[', ']', '…', 12) AS match
          FROM patch_search JOIN patches p ON p.id = patch_search.id
          WHERE patch_search MATCH ? ORDER BY bm25(patch_search) LIMIT ?""", (query, limit)).fetchall()
        return [{"id": row["id"], "name": row["name"], "prompt": row["prompt"], "tags": row["tags"].split(),
                 "notes": row["notes"], "preset_path": row["preset_path"], "render_path": row["render_path"], "match": row["match"]} for row in rows]
