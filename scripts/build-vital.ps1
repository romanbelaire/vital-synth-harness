$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$solution = Join-Path $root 'vendor\vital\standalone\builds\vs19\Vial.sln'
if (-not (Test-Path $solution)) { throw "Vital source is missing: $solution" }

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) { throw 'Visual Studio Build Tools were not found.' }
$install = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -property installationPath
if (-not $install) { throw 'MSBuild-capable Visual Studio installation was not found.' }
$msbuild = Join-Path $install 'MSBuild\Current\Bin\MSBuild.exe'
& $msbuild $solution /m /p:Configuration=Release /p:Platform=x64
if ($LASTEXITCODE -ne 0) { throw "Vital build failed ($LASTEXITCODE)." }
