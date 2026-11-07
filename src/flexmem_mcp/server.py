from __future__ import annotations

import json
import sys
from pathlib import Path

from .adapter import VitalAdapter
from .audio import analyze_wav
from .storage import Library

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = Library(ROOT / "data")
VITAL = VitalAdapter(ROOT)

TOOLS = [
 ("create_default_patch", "Create a complete, valid default Vital preset for a new sound-design session.", {}),
 ("import_preset", "Import a user-owned complete .vital preset as a mutable working patch.", {"source_path": {"type":"string"}}),
 ("describe_patch", "Return Vital metadata and current numeric parameter values.", {"patch_id": {"type":"string"}}),
 ("list_parameters", "List known Vital parameter names and legal value ranges.", {"contains": {"type":"string"}}),
 ("apply_parameter_changes", "Atomically set numeric Vital parameters after range validation.", {"patch_id": {"type":"string"}, "changes": {"type":"object"}}),
 ("render_patch", "Render a working patch to WAV with Vital's offline renderer.", {"patch_id": {"type":"string"}, "midi": {"type":"string"}, "length_seconds": {"type":"number"}, "bpm": {"type":"number"}}),
 ("analyze_audio", "Analyze a rendered PCM WAV for duration, loudness, brightness proxy, and zero crossings.", {"audio_path": {"type":"string"}}),
 ("save_accepted_patch", "Persist an accepted patch plus its prompt, notes, tags, optional render, and analysis in local searchable memory.", {"patch_id": {"type":"string"}, "name": {"type":"string"}, "prompt": {"type":"string"}, "notes": {"type":"string"}, "tags": {"type":"array", "items":{"type":"string"}}, "audio_path": {"type":"string"}}),
 ("search_patch_library", "Full-text search accepted patches by a musical request, tags, or technique.", {"query": {"type":"string"}, "limit": {"type":"integer"}}),
]

def schema(properties: dict) -> dict:
    required = [k for k in properties if k not in {"contains", "midi", "length_seconds", "bpm", "notes", "tags", "audio_path", "limit"}]
    return {"type":"object", "properties": properties, "required": required, "additionalProperties": False}

def call(name: str, a: dict) -> dict:
    if name == "create_default_patch":
        import uuid
        temporary = LIBRARY.presets / f"default-{uuid.uuid4().hex}.vital"
        VITAL.default_preset(temporary)
        patch_id = LIBRARY.import_preset(temporary)
        temporary.unlink(missing_ok=True)
        return {"patch_id": patch_id}
    if name == "import_preset": return {"patch_id": LIBRARY.import_preset(Path(a["source_path"])).__str__()}
    if name == "describe_patch": return VITAL.describe(LIBRARY.preset_path(a["patch_id"]))
    if name == "list_parameters":
        needle = a.get("contains", "").lower()
        return {"parameters": {k:v for k,v in VITAL.catalog.items() if needle in k.lower()}}
    if name == "apply_parameter_changes": return VITAL.apply(LIBRARY.preset_path(a["patch_id"]), a["changes"])
    if name == "render_patch":
        patch_id = a["patch_id"]; output = LIBRARY.renders / f"working-{patch_id}.wav"
        return VITAL.render(LIBRARY.preset_path(patch_id), output, a.get("midi", "48"), a.get("length_seconds", 5), a.get("bpm", 120))
    if name == "analyze_audio": return analyze_wav(Path(a["audio_path"]))
    if name == "save_accepted_patch":
        audio = Path(a["audio_path"]) if a.get("audio_path") else None
        analysis = analyze_wav(audio) if audio else None
        return {"library_id": LIBRARY.accept(a["patch_id"], a["name"], a["prompt"], a.get("notes", ""), a.get("tags", []), audio, analysis)}
    if name == "search_patch_library": return {"results": LIBRARY.search(a["query"], min(max(a.get("limit", 5), 1), 20))}
    raise ValueError(f"Unknown tool: {name}")

def response(identifier, result=None, error=None):
    payload = {"jsonrpc":"2.0", "id":identifier}
    payload["result" if error is None else "error"] = result if error is None else {"code": -32000, "message": str(error)}
    print(json.dumps(payload), flush=True)

def main() -> None:
    for line in sys.stdin:
        try:
            message = json.loads(line)
            method, identifier = message.get("method"), message.get("id")
            if method == "initialize": response(identifier, {"protocolVersion":"2024-11-05", "capabilities":{"tools":{}}, "serverInfo":{"name":"flexmem", "version":"0.1.0"}})
            elif method == "tools/list": response(identifier, {"tools":[{"name":n,"description":d,"inputSchema":schema(p)} for n,d,p in TOOLS]})
            elif method == "tools/call":
                result = call(message["params"]["name"], message["params"].get("arguments", {}))
                response(identifier, {"content":[{"type":"text", "text":json.dumps(result, indent=2)}]})
            elif identifier is not None: response(identifier, {})
        except Exception as exc:
            if 'identifier' in locals() and identifier is not None: response(identifier, error=exc)
            else: print(f"flexmem error: {exc}", file=sys.stderr, flush=True)

if __name__ == "__main__": main()
