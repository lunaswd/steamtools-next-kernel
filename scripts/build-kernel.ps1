param(
  [ValidateSet('Release','Debug')][string]$Configuration = 'Release',
  [string]$Generator = 'Ninja Multi-Config',
  [string]$BuildDirectory = '',
  [string]$DependencyDirectory = '',
  [ValidateRange(1,64)][int]$Jobs = 6
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
# Ninja's MSVC dependency scanner needs stable include output on localized VS.
$env:VSLANG = '1033'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $BuildDirectory) { $BuildDirectory = Join-Path $repo 'build-release' }
if (-not $DependencyDirectory) { $DependencyDirectory = Join-Path $repo '.deps' }
$build = [IO.Path]::GetFullPath($BuildDirectory)
$deps = [IO.Path]::GetFullPath($DependencyDirectory)
$cmakeText = Get-Content -Raw -LiteralPath (Join-Path $repo 'src/CMakeLists.txt')
if ($cmakeText -notmatch 'project\(OpenSteamTool VERSION ([0-9]+(?:\.[0-9]+){3})') { throw 'Four-part kernel version is required' }
$version = $Matches[1]
$sourceCommit = (& git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'A Git checkout is required for release provenance' }
$dirty = & git -C $repo status --porcelain --untracked-files=normal
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Commit source changes before a release build' }

# Validate pre-populated caches against the committed dependency lock. Empty
# caches are populated by CMake from the exact revisions in its recipes.
$lock = Get-Content -Raw -LiteralPath (Join-Path $repo 'dependency-lock.json') | ConvertFrom-Json
foreach ($dep in $lock.dependencies) {
  $source = Join-Path $deps ($dep.name + '-src')
  if ((Test-Path -LiteralPath $source) -and $dep.PSObject.Properties['commit']) {
    $actual = (& git -C $source rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $actual -ne $dep.commit) { throw "Dependency cache revision mismatch: $($dep.name)" }
    $modified = & git -C $source status --porcelain --untracked-files=normal
    if ($LASTEXITCODE -ne 0 -or $modified) { throw "Dependency cache has local changes: $($dep.name)" }
  }
}
$configure = @('-S',(Join-Path $repo 'src'),'-B',$build,'-G',$Generator,"-DOST_DEPS_DIR=$deps","-DOPENSTEAMTOOL_VERSION=$version")
if ($Generator -like 'Visual Studio*') { $configure += @('-A','x64') }
& cmake @configure
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed' }
& python (Join-Path $PSScriptRoot 'package_kernel.py') --verify-dependencies --deps-dir $deps
if ($LASTEXITCODE -ne 0) { throw 'Dependency source verification failed' }
& cmake --build $build --config $Configuration --parallel $Jobs
if ($LASTEXITCODE -ne 0) { throw 'CMake build failed' }

$files = @()
function Get-Sha256([string]$Path) {
  $stream = [IO.File]::OpenRead($Path)
  $hash = [Security.Cryptography.SHA256]::Create()
  try { return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
  finally { $stream.Dispose(); $hash.Dispose() }
}
foreach ($name in @('OpenSteamTool.dll','dwmapi.dll','xinput1_4.dll','version.dll.disabled')) {
  $path = Join-Path (Join-Path $build $Configuration) $name
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing kernel build output: $name" }
  $info = [Diagnostics.FileVersionInfo]::GetVersionInfo($path)
  if ($info.FileVersion -ne $version) { throw "PE file version mismatch: $name" }
  $files += [ordered]@{ name=$name; sizeBytes=(Get-Item -LiteralPath $path).Length; sha256=(Get-Sha256 $path) }
}
$record = [ordered]@{ schemaVersion=1; version=$version; configuration=$Configuration; platform='windows-x64'; sourceCommit=$sourceCommit; files=$files }
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $build 'kernel-build.json') -Encoding utf8
Write-Output "Built OpenSteamTool $version at source commit $sourceCommit"
Write-Output "Build provenance: $(Join-Path $build 'kernel-build.json')"
