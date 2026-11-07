from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


class VitalAdapter:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root
        self.renderer = Path(os.environ["VITAL_RENDERER"]) if os.environ.get("VITAL_RENDERER") else None
        self.catalog = self._read_catalog()

    def _read_catalog(self) -> dict[str, dict]:
        source = self.root / "vendor" / "vital" / "src" / "common" / "synth_parameters.cpp"
        if not source.is_file(): return {}
        pattern = re.compile(r'\{\s*"([^"]+)",\s*0x[0-9A-Fa-f]+,\s*([^,]+),\s*([^,]+),')
        catalog = {}
        for name, low, high in pattern.findall(source.read_text(encoding="utf-8")):
            try: catalog[name] = {"minimum": float(low), "maximum": float(high)}
            except ValueError: pass
        return catalog

    def describe(self, preset: Path) -> dict:
        data = json.loads(preset.read_text(encoding="utf-8"))
        settings = data.get("settings", {})
        values = {key: value for key, value in settings.items() if isinstance(value, (int, float, bool))}
        return {"name": data.get("preset_name", ""), "author": data.get("author", ""), "style": data.get("preset_style", ""), "comments": data.get("comments", ""), "parameter_count": len(values), "parameters": values}

    def default_preset(self, output: Path) -> None:
        if not self.renderer or not self.renderer.is_file():
            raise RuntimeError("VITAL_RENDERER is not set to the built local renderer. Run scripts/build-vital.ps1 first.")
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [str(self.renderer), "--write-default", "--output", output.name]
        completed = subprocess.run(command, cwd=output.parent, capture_output=True, text=True, timeout=30)
        if completed.returncode or not output.is_file():
            raise RuntimeError(f"Vital default-preset export failed: {completed.stderr or completed.stdout}")

    def apply(self, preset: Path, changes: dict[str, float]) -> dict:
        data = json.loads(preset.read_text(encoding="utf-8"))
        settings = data.setdefault("settings", {})
        rejected = {}
        for name, value in changes.items():
            # Indexed controls (for example `filter_1_cutoff`) are generated
            # by Vital at startup. They are valid when present in the complete
            # preset, even though they do not occur literally in the source's
            # global parameter table.
            if name not in self.catalog and name not in settings:
                rejected[name] = "unknown Vital parameter"; continue
            if not isinstance(value, (int, float)): rejected[name] = "value must be numeric"; continue
            limits = self.catalog.get(name)
            if limits and not limits["minimum"] <= value <= limits["maximum"]:
                rejected[name] = f"outside [{limits['minimum']}, {limits['maximum']}]"; continue
            settings[name] = value
        if rejected: raise ValueError(json.dumps({"rejected": rejected}))
        preset.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"applied": changes, "preset_name": data.get("preset_name", "")}

    def render(self, preset: Path, output: Path, midi: str, length: float, bpm: float) -> dict:
        if not self.renderer or not self.renderer.is_file():
            raise RuntimeError("VITAL_RENDERER is not set to a built Vital headless executable. Run scripts/build-vital.ps1 first.")
        output.parent.mkdir(parents=True, exist_ok=True)
        # The Windows standalone project has a built-in offline render mode. It
        # writes `<preset-stem>.wav` into its working directory rather than
        # accepting an output flag, so use a private copy with the desired name.
        working_preset = output.with_suffix(".vital")
        shutil.copy2(preset, working_preset)
        command = [str(self.renderer), working_preset.name, "--render", "--headless",
                   "--midi", str(midi), "--length", str(length), "--bpm", str(bpm)]
        completed = subprocess.run(command, cwd=output.parent, capture_output=True, text=True, timeout=60)
        generated = output.parent / f"{working_preset.stem}.wav"
        if generated != output and generated.is_file():
            generated.replace(output)
        working_preset.unlink(missing_ok=True)
        if completed.returncode or not output.is_file():
            raise RuntimeError(f"Vital renderer failed: {completed.stderr or completed.stdout}")
        return {"output_path": str(output), "command": command}
