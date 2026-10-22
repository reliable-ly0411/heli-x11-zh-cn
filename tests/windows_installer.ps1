# Run on Windows against a private fixture ZIP containing the pinned originals.
# The fixture contains only the three required JAR/ZIP inputs, BAT launchers,
# languages.txt, and synthetic settings. It must never be published.
param([Parameter(Mandatory=$true)][string]$Installer,
      [Parameter(Mandatory=$true)][string]$FixtureZip,
      [Parameter(Mandatory=$true)][string]$TestDirectory)
$ErrorActionPreference='Stop'
if(Test-Path -LiteralPath $TestDirectory){throw 'TestDirectory must be a new directory.'}
New-Item -ItemType Directory -Path $TestDirectory | Out-Null
$root=Join-Path $TestDirectory 'HELI X 中文 & 路径'
Expand-Archive -LiteralPath $FixtureZip -DestinationPath $root
function Assert($condition,$message){if(!$condition){throw $message}}
function Invoke-Patch([string]$command,[string]$name,[int]$expected=0){
 $log=Join-Path $TestDirectory ($name+'.log')
 $arguments='--command '+$command+' --helix-dir "'+$root+'" --log "'+$log+'"'
 $process=Start-Process -FilePath $Installer -ArgumentList $arguments -Wait -PassThru
 if($process.ExitCode -ne $expected){Get-Content -LiteralPath $log;throw "$name exit=$($process.ExitCode) expected=$expected"}
 Write-Output "PASS $name"
}
$original=@{}
Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object {$original[$_.FullName]=(Get-FileHash -LiteralPath $_.FullName).Hash}
Invoke-Patch check check
# A dedicated sleeping HELI-X.exe probe verifies the running-process guard.
$probeSource=Join-Path $TestDirectory 'ProcessProbe.cs'
[IO.File]::WriteAllText($probeSource,'class Probe { static void Main() { System.Threading.Thread.Sleep(60000); } }')
$probeExe=Join-Path $root 'HELI-X.exe'
& "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe "/out:$probeExe" $probeSource
Assert ($LASTEXITCODE -eq 0) 'Process probe failed to compile'
$probeProcess=Start-Process -FilePath $probeExe -PassThru
try {Invoke-Patch install running-process 1} finally {if(!$probeProcess.HasExited){$probeProcess.Kill();$probeProcess.WaitForExit()}}
Remove-Item -LiteralPath $probeExe
# Force a late write failure. All earlier changes and first-install directories must roll back.
$readonly=Join-Path $root 'files\Application\ApplicationSettings.xml'
(Get-Item -LiteralPath $readonly).IsReadOnly=$true
try {Invoke-Patch install readonly-rollback 1} finally {(Get-Item -LiteralPath $readonly).IsReadOnly=$false}
foreach($p in $original.Keys){Assert ((Get-FileHash -LiteralPath $p).Hash -eq $original[$p]) 'Failed install changed originals'}
Assert (!(Test-Path -LiteralPath (Join-Path $root '.helix-zh-cn-windows'))) 'Failed install left incomplete state'
Invoke-Patch install install
Invoke-Patch verify verify
$stateDir=Join-Path $root '.helix-zh-cn-windows'
$firstBackup=(Get-FileHash -LiteralPath "$stateDir\backup\files\Application\ApplicationSettings.xml").Hash
Invoke-Patch install repeat-install
Assert ((Get-FileHash -LiteralPath "$stateDir\backup\files\Application\ApplicationSettings.xml").Hash -eq $firstBackup) 'Backup was overwritten'
$guard=Join-Path $stateDir 'guard.ps1'
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $guard
Assert ($LASTEXITCODE -eq 0) 'Guard rejected original inputs'
# Run the actual BAT guard block through cmd.exe; never start the simulator.
$bat=[IO.File]::ReadAllText((Join-Path $root 'runHELI-X-local.bat'))
$begin=$bat.IndexOf('rem BEGIN HELI-X Chinese patch for Windows')
$end=$bat.IndexOf('rem END HELI-X Chinese patch for Windows')+'rem END HELI-X Chinese patch for Windows'.Length
$block=$bat.Substring($begin,$end-$begin)
$probe=Join-Path $root 'guard-probe.cmd'
[IO.File]::WriteAllText($probe,"@echo off`r`nset jars=original.jar`r`n"+$block+"`r`necho %jars%`r`n",[Text.Encoding]::ASCII)
Push-Location -LiteralPath $root
try {$result=& cmd.exe /d /c guard-probe.cmd} finally {Pop-Location}
Assert (($result -join '') -match 'Chinese.jar;original.jar') 'BAT did not prepend overlay'
# Corrupt a protected backup: uninstall must stop before touching the installation.
$backup=Join-Path $stateDir 'backup\runHELI-X-local.bat'
$saved=[IO.File]::ReadAllBytes($backup)
[IO.File]::AppendAllText($backup,'changed')
Invoke-Patch uninstall damaged-backup 1
Assert ((Get-Content -LiteralPath "$stateDir\state.json" -Raw -Encoding UTF8 | ConvertFrom-Json).active) 'Failed uninstall changed state'
[IO.File]::WriteAllBytes($backup,$saved)
# Simulate an upstream update: guard disables patch and check refuses; uninstall remains available.
$main=Join-Path $root 'libs\HeliX\HeliX11.jar'
[IO.File]::AppendAllText($main,'updated')
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $guard
Assert ($LASTEXITCODE -ne 0) 'Guard accepted changed inputs'
Push-Location -LiteralPath $root
try {$result=& cmd.exe /d /c guard-probe.cmd} finally {Pop-Location}
Assert (($result -join '') -notmatch 'Chinese.jar;original.jar') 'BAT loaded incompatible overlay'
Invoke-Patch check incompatible-input 1
$settings=Join-Path $root 'files\Application\ApplicationSettings.xml'
[IO.File]::WriteAllText($settings,[IO.File]::ReadAllText($settings).Replace('<UserSetting>keep</UserSetting>','<UserSetting>edited</UserSetting>'),(New-Object Text.UTF8Encoding($false)))
Invoke-Patch uninstall uninstall-after-update
Assert ((Get-Content -LiteralPath $settings -Raw -Encoding UTF8).Contains('<UserSetting>edited</UserSetting>')) 'Other settings lost'
Assert ((Get-Content -LiteralPath $settings -Raw -Encoding UTF8).Contains('<Language>en</Language>')) 'Language not restored'
foreach($name in @('runHELI-X.bat','runHELI-X_VR.bat','runHELI-X-local.bat','runHELI-X_VR-local.bat','resources\miscellaneous\languages.txt')){
 $p=Join-Path $root $name
 Assert ((Get-FileHash -LiteralPath $p).Hash -eq $original[$p]) "Byte-exact restore failed: $name"
}
Assert (!(Test-Path -LiteralPath "$root\resources\miscellaneous\images\flag_zh.jpg")) 'Added icon remains'
Write-Output 'PASS all Windows installer tests; no simulator process was launched.'
