# FlexMem

FlexMem is a local, stdio MCP server for iterative synth sound design.  This
first implementation controls Vital-compatible `.vital` preset files, renders
them with Vital's official headless renderer, analyses the resulting WAV, and
stores accepted sounds in a searchable local SQLite library.

It deliberately has no cloud API, audio upload, or automatic acceptance step.
An agent proposes and renders; the human decides what is worth remembering.

## Quick start (Windows)

1. Clone upstream Vital into `vendor/vital`. This repository does not include the synth source, factory presets, or rendered audio.

   ```powershell
   git clone https://github.com/mtytel/vital.git vendor/vital
   ```

2. Build the renderer from a Developer PowerShell:

   ```powershell
   .\scripts\build-vital.ps1
   ```

3. Install the local stdio server (there are no third-party Python
   dependencies):

   ```powershell
   python -m pip install -e .
   ```

4. Set the renderer path for the process that launches your desktop agent:

   ```powershell
   $env:VITAL_RENDERER = "$PWD\vendor\vital\standalone\builds\vs19\x64\Release\Vial.exe"
   ```

5. Register the server in an MCP client with this command:

   ```json
   { "command": "python", "args": ["-m", "flexmem_mcp.server"], "cwd": "C:\\path\\to\\flexmem" }
   ```

The server uses only the Python standard library. Its data remains under
`data/`: original/copied presets, rendered previews, and `library.sqlite3`.

## Agent workflow

1. Start with `create_default_patch`, or `import_preset` a legitimate
   user-owned `.vital` preset.
2. Use `describe_patch`, `list_parameters`, and `apply_parameter_changes`.
3. `render_patch`, then `analyze_audio`.
4. Once the user accepts it, call `save_accepted_patch` with the request and
   notes. Use `search_patch_library` for later work.

## MCP tools

`import_preset`, `describe_patch`, `list_parameters`,
`apply_parameter_changes`, `render_patch`, `analyze_audio`,
`save_accepted_patch`, and `search_patch_library`.

## Licensing

`vendor/vital` is the upstream Vital source and is GPL-3.0 licensed. The
repository's restrictions also prohibit redistributing bundled factory presets
and using Vital branding for derivative binary distributions. FlexMem does not
ship any presets. Review the upstream license before distribution.

