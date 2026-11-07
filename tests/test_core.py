import json
from pathlib import Path

from flexmem_mcp.audio import analyze_wav
from flexmem_mcp.storage import Library


def test_library_import_accept_search(tmp_path: Path):
    source = tmp_path / "sound.vital"
    source.write_text(json.dumps({"synth_version":"1.0.0", "settings":{}}), encoding="utf-8")
    library = Library(tmp_path / "library")
    patch = library.import_preset(source)
    library.accept(patch, "Brassy Horn", "make a peaky horn", "less buzz", ["brassy", "horn"], None, None)
    assert library.search("horn", 5)[0]["name"] == "Brassy Horn"
