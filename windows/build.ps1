param([Parameter(Mandatory=$true)][string]$PreparedDirectory)
$ErrorActionPreference = 'Stop'
$prepared = (Resolve-Path -LiteralPath $PreparedDirectory).Path
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path -LiteralPath $compiler)) { throw '.NET Framework 4.x compiler is required on the Windows build host.' }
$info = Get-Content -LiteralPath (Join-Path $prepared 'build-info.json') -Raw | ConvertFrom-Json
$exe = Join-Path $prepared ("setupHeli-X11-" + $info.version + "-win64-zh-CN.exe")
& $compiler /nologo /target:winexe /platform:x64 /optimize+ /utf8output "/out:$exe" "/win32manifest:$prepared\app.manifest" "/resource:$prepared\payload.zip,payload.zip" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll "$prepared\Installer.cs" "$prepared\AssemblyInfo.cs"
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed.' }
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText((Join-Path $prepared 'SHA256SUMS'), "$hash  $([IO.Path]::GetFileName($exe))`n", (New-Object Text.UTF8Encoding($false)))
Write-Output $exe
