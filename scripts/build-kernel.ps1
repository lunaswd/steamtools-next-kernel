param(
  [ValidateSet('Release','Debug')][string]$Configuration = 'Release',
  [string]$Generator = 'Ninja Multi-Config',
  [string]$BuildDirectory = '',
  [string]$DependencyDirectory = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
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
  }
}
$configure = @('-S',(Join-Path $repo 'src'),'-B',$build,'-G',$Generator,"-DOST_DEPS_DIR=$deps","-DOPENSTEAMTOOL_VERSION=$version")
if ($Generator -like 'Visual Studio*') { $configure += @('-A','x64') }
& cmake @configure
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed' }
& cmake --build $build --config $Configuration --parallel
if ($LASTEXITCODE -ne 0) { throw 'CMake build failed' }

$files = @()
foreach ($name in @('OpenSteamTool.dll','dwmapi.dll','xinput1_4.dll','version.dll.disabled')) {
  $path = Join-Path (Join-Path $build $Configuration) $name
  if (-not (Test-Path -LiteralPath $path)) { throw "Missing kernel build output: $name" }
  $info = [Diagnostics.FileVersionInfo]::GetVersionInfo($path)
  if ($info.FileVersion -ne $version) { throw "PE file version mismatch: $name" }
  $files += [ordered]@{ name=$name; sizeBytes=(Get-Item -LiteralPath $path).Length; sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
}
$record = [ordered]@{ schemaVersion=1; version=$version; configuration=$Configuration; platform='windows-x64'; sourceCommit=$sourceCommit; files=$files }
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $build 'kernel-build.json') -Encoding utf8
Write-Output "Built OpenSteamTool $version at source commit $sourceCommit"
Write-Output "Build provenance: $(Join-Path $build 'kernel-build.json')"
