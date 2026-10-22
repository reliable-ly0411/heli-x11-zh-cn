# Runs before the original Java command; any error leaves the overlay disabled.
$ErrorActionPreference = 'Stop'
try {
    $root = Split-Path -Parent $PSScriptRoot
    $spec = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'guard.json') -Raw | ConvertFrom-Json
    foreach ($item in $spec.PSObject.Properties) {
        $path = Join-Path $root $item.Name
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $item.Value) { exit 1 }
    }
    exit 0
} catch { exit 1 }
