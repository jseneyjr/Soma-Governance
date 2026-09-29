# Soma — Native Windows PowerShell Uninstaller
# Removes steering rules and skills deployed by install.ps1 / install.sh.
#
# Usage:
#   .\uninstall.ps1 [-Platform <gemini|kiro|copilot|claude>] [-DryRun] [-Force] [-KeepConfig] [-NoRestore]
# Examples:
#   .\uninstall.ps1
#   .\uninstall.ps1 kiro -DryRun
#   .\uninstall.ps1 -Platform copilot -Force
#
# Exit codes:
#   0  success (including "nothing to remove" and an explicit user abort)
#   1  failure (bad platform, unreadable/invalid manifest, platform mismatch, removal error)
#   2  confirmation required but the host is non-interactive (nothing was removed)

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [string]$Platform = "",

    [switch]$DryRun,

    [switch]$Force,

    [switch]$KeepConfig,

    [switch]$NoRestore,

    [switch]$Help
)

if ($Help) {
    Write-Host "Soma — Windows PowerShell Uninstaller"
    Write-Host "Usage: .\uninstall.ps1 [[-Platform] <gemini|kiro|copilot|claude>] [-DryRun] [-Force] [-KeepConfig] [-NoRestore]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Platform    Target platform: gemini (default), kiro, copilot, or claude"
    Write-Host "  -DryRun      Print the removal plan without deleting anything"
    Write-Host "  -Force       Skip the deletion confirmation prompt (the restore offer is still made)"
    Write-Host "  -KeepConfig  Never remove soma.conf, even if the manifest lists it"
    Write-Host "  -NoRestore   Do not offer to restore the previous configuration from backups"
    Write-Host "  -Help        Show this help message"
    Write-Host ""
    Write-Host "Never removed: .soma/cells/, fitness.jsonl, docs/snapshots/ (user-authored data)."
    Write-Host "Non-interactive hosts abort instead of prompting; pass -Force or -DryRun there."
    exit 0
}

# Ensure UTF-8 output encoding where supported
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Ignore if console encoding cannot be modified
}

# BOM-free UTF-8 writer (PS 5.1's -Encoding UTF8 adds a BOM)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-Utf8File {
    param([string]$Path, [string]$Content)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}

# ── Logging Functions ─────────────────────────────────────────────
function Write-LogInfo {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-LogWarn {
    param([string]$Message)
    Write-Host "  ⚠  $Message" -ForegroundColor Yellow
}

function Write-LogSkip {
    param([string]$Message)
    Write-Host "  ⏭  $Message" -ForegroundColor Cyan
}

function Write-LogError {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
}

$script:HadFailure = $false
function Set-Failure {
    param([string]$Message)
    Write-LogError $Message
    $script:HadFailure = $true
}

# ── Paths & Locations ─────────────────────────────────────────────
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if (-not $ScriptDir) {
    $ScriptDir = (Get-Location).Path
}
# This script lives in <repo>/install, so the repo root is one level up.
$RepoDir = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$SourceRules = Join-Path $RepoDir "genome"
$SourceSkills = Join-Path $RepoDir "organs"
$ConfigFile = Join-Path $RepoDir "soma.conf"
$WorkDir = (Get-Location).Path

$UserHome = $env:USERPROFILE
if (-not $UserHome) {
    $UserHome = [Environment]::GetFolderPath('UserProfile')
}
if (-not $UserHome) {
    $UserHome = $HOME
}

# ── Platform Resolution (CLI > env > soma.conf > default) ─────────
$ResolvedPlatform = "gemini"
if (Test-Path -LiteralPath $ConfigFile -PathType Leaf) {
    Get-Content -LiteralPath $ConfigFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        if ($line -match '^SOMA_PLATFORM\s*=\s*(.*)$') {
            $val = $matches[1]
            if ($val -match '^(.*?)\s*#.*$') { $val = $matches[1] }
            $val = $val.Trim().Trim('"').Trim("'")
            if ($val) { $ResolvedPlatform = $val }
        }
    }
}
$envPlatform = [Environment]::GetEnvironmentVariable("SOMA_PLATFORM")
if ($envPlatform) { $ResolvedPlatform = $envPlatform }
if ($Platform) { $ResolvedPlatform = $Platform }
$Platform = $ResolvedPlatform.Trim().ToLower()

# Allowed platforms must match what install.ps1 supports.
$AllowedPlatforms = @("gemini", "kiro", "copilot", "claude")
if ($AllowedPlatforms -notcontains $Platform) {
    Write-LogError "Invalid Platform: '$Platform' (allowed: $($AllowedPlatforms -join ' '))"
    exit 1
}

# ── Helpers ───────────────────────────────────────────────────────

# Manifests may be written by install.sh under Git Bash / MSYS / Cygwin, which
# records POSIX-style drive paths. Normalize them to native Windows paths.
function Convert-ManifestPath {
    param([string]$RawPath)
    if (-not $RawPath) { return "" }
    $p = $RawPath.Trim()
    if (-not $p) { return "" }
    if ($p -match '^/cygdrive/([A-Za-z])/(.*)$') {
        $p = "$($matches[1].ToUpper()):/$($matches[2])"
    } elseif ($p -match '^/([A-Za-z])/(.*)$') {
        $p = "$($matches[1].ToUpper()):/$($matches[2])"
    }
    return $p.Replace('/', '\')
}

function Get-ManifestProperty {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

function Get-ManifestPathList {
    param($Object, [string]$Name)
    $out = @()
    $raw = Get-ManifestProperty -Object $Object -Name $Name
    if ($null -eq $raw) { return $out }
    foreach ($item in @($raw)) {
        if ($null -eq $item) { continue }
        $converted = Convert-ManifestPath ([string]$item)
        if ($converted) { $out += $converted }
    }
    return $out
}

function Get-RepoRuleNames {
    $names = @()
    if (Test-Path -LiteralPath $SourceRules -PathType Container) {
        $names = @(Get-ChildItem -LiteralPath $SourceRules -Filter "*.md" -Recurse -Force -File -ErrorAction SilentlyContinue |
                   ForEach-Object { $_.Name })
    }
    return $names
}

function Get-RepoSkillNames {
    $names = @()
    if (Test-Path -LiteralPath $SourceSkills -PathType Container) {
        $names = @(Get-ChildItem -LiteralPath $SourceSkills -Directory -ErrorAction SilentlyContinue |
                   ForEach-Object { $_.Name })
    }
    return $names
}

# Only treat an mcp.json as ours if it actually references the soma server.
function Test-SomaMcpFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $text = $null
    try {
        $text = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop
    } catch {
        return $false
    }
    if (-not $text) { return $false }
    return ($text -match '"soma"')
}

function Test-HostInteractive {
    try {
        if ($env:SOMA_NONINTERACTIVE -eq '1') { return $false }
        if (-not [Environment]::UserInteractive) { return $false }
        if ($null -eq $Host -or $null -eq $Host.UI) { return $false }
        try {
            if ([Console]::IsInputRedirected) { return $false }
        } catch {
            # IsInputRedirected is unavailable on this runtime; assume a real console.
        }
        return $true
    } catch {
        return $false
    }
}

# install.ps1 backs up each item in place as "<path>.bak.<unix-epoch>".
# Return the newest such sibling for a given target path, or $null.
function Get-LatestBackupSibling {
    param([string]$TargetPath)
    $parent = Split-Path -Parent $TargetPath
    $leaf = Split-Path -Leaf $TargetPath
    if (-not $parent -or -not $leaf) { return $null }
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) { return $null }
    $pattern = '^' + [regex]::Escape($leaf) + '\.bak\.(?<epoch>\d+)$'
    $best = $null
    $bestEpoch = [int64]-1
    foreach ($c in @(Get-ChildItem -LiteralPath $parent -Force -ErrorAction SilentlyContinue)) {
        if ($c.Name -match $pattern) {
            $epoch = [int64]$matches['epoch']
            if ($epoch -gt $bestEpoch) {
                $bestEpoch = $epoch
                $best = $c
            }
        }
    }
    return $best
}

$SomaSectionHeaders = @('# Copilot Global Instructions', '# Soma Governance Rules')

# Find the first line that starts a Soma-generated section, or -1.
function Find-SomaSectionStart {
    param([string[]]$Lines)
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $line = $Lines[$i]
        if ($null -eq $line) { continue }
        foreach ($h in $SomaSectionHeaders) {
            if ($line.StartsWith($h)) { return $i }
        }
    }
    return -1
}

# Truncate a shared file at the first Soma header (parity with uninstall.sh's
# sed '/^# Soma Governance Rules/,$d'). Preserves anything above it.
function Remove-SomaSection {
    param([string]$FilePath)
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { return }
    $lines = @(Get-Content -LiteralPath $FilePath -ErrorAction Stop)
    $cut = Find-SomaSectionStart -Lines $lines
    if ($cut -lt 0) {
        Write-LogSkip "$FilePath (no Soma section found, left untouched)"
        return
    }

    $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    Copy-Item -LiteralPath $FilePath -Destination "$FilePath.bak.$epoch" -Force -ErrorAction Stop
    Write-LogWarn "$(Split-Path -Leaf $FilePath) backed up to $(Split-Path -Leaf $FilePath).bak.$epoch"

    $kept = @()
    if ($cut -gt 0) { $kept = @($lines[0..($cut - 1)]) }
    # Drop trailing blank lines left behind by the removed section. Index-based
    # so a 1-element result stays an array instead of collapsing to a string.
    $lastIndex = $kept.Count - 1
    while ($lastIndex -ge 0 -and -not ("$($kept[$lastIndex])".Trim())) {
        $lastIndex--
    }
    if ($lastIndex -lt 0) {
        $kept = @()
    } else {
        $kept = @($kept[0..$lastIndex])
    }

    if ($kept.Count -eq 0) {
        Remove-Item -LiteralPath $FilePath -Force -ErrorAction Stop
        Write-LogInfo "removed $FilePath (contained only Soma content)"
    } else {
        Write-Utf8File -Path $FilePath -Content (($kept -join "`r`n") + "`r`n")
        Write-LogInfo "cleaned Soma sections from $FilePath"
    }
}

# ── Manifest Resolution ───────────────────────────────────────────
$ManifestPath = Join-Path (Join-Path $UserHome ".soma") "manifest.json"
$LocalManifestPath = Join-Path (Join-Path $WorkDir ".soma") "manifest.json"
if (Test-Path -LiteralPath $LocalManifestPath -PathType Leaf) {
    $ManifestPath = $LocalManifestPath
}

$Manifest = $null
$ManifestExists = Test-Path -LiteralPath $ManifestPath -PathType Leaf

Write-Host "Uninstalling Soma ($Platform)..."
if ($DryRun) {
    Write-Host "Mode: DRY-RUN (no files will be deleted)"
}

if ($ManifestExists) {
    Write-Host "Found manifest at $ManifestPath. Reading paths..."
    $rawManifest = $null
    try {
        $rawManifest = Get-Content -LiteralPath $ManifestPath -Raw -ErrorAction Stop
    } catch {
        Write-LogError "Manifest exists at $ManifestPath but could not be read: $($_.Exception.Message)"
        Write-LogError "Refusing to continue — guessing paths here risks an incomplete uninstall."
        exit 1
    }
    try {
        $Manifest = $rawManifest | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Write-LogError "Manifest at $ManifestPath is not valid JSON: $($_.Exception.Message)"
        Write-LogError "Refusing to continue — repair or delete the manifest, then re-run."
        exit 1
    }
    if ($null -eq $Manifest) {
        Write-LogError "Manifest at $ManifestPath parsed to nothing (empty file?)."
        Write-LogError "Refusing to continue — repair or delete the manifest, then re-run."
        exit 1
    }
} else {
    Write-Host "No manifest found at $ManifestPath. Falling back to known install paths..."
}

# ── Platform Mismatch Guard (SOMA-C07) ────────────────────────────
$ManifestPlatform = ""
if ($Manifest) {
    $mp = Get-ManifestProperty -Object $Manifest -Name "platform"
    if ($mp) { $ManifestPlatform = ([string]$mp).Trim().ToLower() }
}
if ($ManifestPlatform -and $ManifestPlatform -ne $Platform) {
    if ($Force) {
        Write-LogWarn "PLATFORM MISMATCH: manifest records '$ManifestPlatform' but you requested '$Platform'."
        Write-LogWarn "-Force was supplied, so continuing anyway."
        Write-LogWarn "The paths recorded for '$ManifestPlatform' will be removed, NOT '$Platform' paths."
    } else {
        Write-LogError "PLATFORM MISMATCH: manifest records '$ManifestPlatform' but you requested '$Platform'."
        Write-LogError "Removing the wrong platform's paths could delete configuration you still use."
        Write-LogError "Re-run as: .\uninstall.ps1 -Platform $ManifestPlatform"
        Write-LogError "Or pass -Force to override (removes the '$ManifestPlatform' paths recorded in the manifest)."
        exit 1
    }
}

$ManifestScope = ""
if ($Manifest) {
    $ms = Get-ManifestProperty -Object $Manifest -Name "scope"
    if ($ms) { $ManifestScope = ([string]$ms).Trim().ToLower() }
}

# ── Build the Removal Plan ────────────────────────────────────────
$FilesToRemove = @()
$DirsToRemove  = @()
$ModifyFiles   = @()
$ConfigToRemove = @()
$BackupDir = ""

function Add-FileTarget {
    param([string]$Path)
    if (-not $Path) { return }
    if ($script:FilesToRemove -notcontains $Path) { $script:FilesToRemove += $Path }
}
function Add-DirTarget {
    param([string]$Path)
    if (-not $Path) { return }
    if ($script:DirsToRemove -notcontains $Path) { $script:DirsToRemove += $Path }
}
function Add-ModifyTarget {
    param([string]$Path)
    if (-not $Path) { return }
    if ($script:ModifyFiles -notcontains $Path) { $script:ModifyFiles += $Path }
}

if ($Manifest) {
    $bd = Get-ManifestProperty -Object $Manifest -Name "backup_dir"
    if ($bd) { $BackupDir = Convert-ManifestPath ([string]$bd) }

    foreach ($f in @(Get-ManifestPathList -Object $Manifest -Name "files")) {
        $leaf = Split-Path -Leaf $f
        if ($leaf -eq "copilot-instructions.md" -or $leaf -eq "CLAUDE.md") {
            Add-ModifyTarget $f
        } elseif ($leaf -eq "soma.conf") {
            if ($KeepConfig) {
                Write-LogSkip "$f (user config, -KeepConfig)"
            } else {
                $ConfigToRemove += $f
            }
        } else {
            Add-FileTarget $f
        }
    }

    foreach ($d in @(Get-ManifestPathList -Object $Manifest -Name "organs")) {
        Add-DirTarget $d
    }

    foreach ($h in @(Get-ManifestPathList -Object $Manifest -Name "hooks")) {
        Add-FileTarget $h
    }
} else {
    $knownRules = Get-RepoRuleNames
    $knownSkills = Get-RepoSkillNames

    # Without a manifest, the repo's genome/ is the only evidence of which files
    # belong to Soma. Refuse to guess rather than deleting every *.md in a shared
    # steering directory.
    if ($knownRules.Count -eq 0) {
        Write-LogError "No manifest, and no rules found under $SourceRules."
        Write-LogError "Cannot tell which installed files belong to Soma, so nothing will be touched."
        Write-LogError "Run this script from its checked-out location (<repo>/install/uninstall.ps1)."
        exit 1
    }

    # Remove only files/dirs whose names match what this repo installs, so that
    # user-authored rules and skills living alongside them survive.
    function Add-InstalledRuleFiles {
        param([string]$Dir, [string]$Extension = ".md")
        if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { return }
        # Filter in PowerShell rather than via -Filter: the Win32 wildcard engine
        # also matches 8.3 short names, so "*.md" can pull in "*.mdx" etc.
        foreach ($f in @(Get-ChildItem -LiteralPath $Dir -File -ErrorAction SilentlyContinue)) {
            if (-not $f.Name.EndsWith($Extension, [StringComparison]::OrdinalIgnoreCase)) { continue }
            $matchName = $f.Name
            if ($Extension -eq ".instructions.md") {
                $matchName = $f.Name -replace '\.instructions\.md$', '.md'
            }
            if ($knownRules -contains $matchName) {
                Add-FileTarget $f.FullName
            }
        }
    }
    function Add-InstalledSkillDirs {
        param([string]$Dir)
        if (-not (Test-Path -LiteralPath $Dir -PathType Container)) { return }
        foreach ($d in @(Get-ChildItem -LiteralPath $Dir -Directory -ErrorAction SilentlyContinue)) {
            if ($knownSkills -contains $d.Name) {
                Add-DirTarget $d.FullName
            }
        }
    }

    switch ($Platform) {
        "gemini" {
            Add-InstalledRuleFiles -Dir (Join-Path $UserHome ".gemini\config\rules")
            Add-InstalledSkillDirs -Dir (Join-Path $UserHome ".gemini\config\skills")
            $gov = Join-Path $UserHome ".gemini\config\plugins\governance"
            if (Test-Path -LiteralPath (Join-Path $gov "hooks.json") -PathType Leaf) {
                Add-FileTarget (Join-Path $gov "hooks.json")
            }
            # Local (--local) gemini installs land under .\.soma\
            Add-InstalledRuleFiles -Dir (Join-Path $WorkDir ".soma\rules")
            Add-InstalledSkillDirs -Dir (Join-Path $WorkDir ".soma\skills")
        }
        "kiro" {
            Add-InstalledRuleFiles -Dir (Join-Path $UserHome ".kiro\steering")
            Add-InstalledSkillDirs -Dir (Join-Path $UserHome ".kiro\skills")
            # .kiro\hooks is Kiro's own directory — only remove our generated file.
            $kiroHooks = Join-Path $UserHome ".kiro\hooks\hooks.json"
            if (Test-Path -LiteralPath $kiroHooks -PathType Leaf) {
                Add-FileTarget $kiroHooks
            }
            $kiroMcp = Join-Path $UserHome ".kiro\settings\mcp.json"
            if (Test-SomaMcpFile -Path $kiroMcp) { Add-FileTarget $kiroMcp }
        }
        "copilot" {
            # Project mode writes .github\instructions\<name>.instructions.md
            foreach ($base in @($WorkDir, $RepoDir)) {
                Add-InstalledRuleFiles -Dir (Join-Path $base ".github\instructions") -Extension ".instructions.md"
            }
            # Global mode appends to a shared file
            $copilotGlobal = Join-Path $UserHome "copilot-instructions.md"
            if (Test-Path -LiteralPath $copilotGlobal -PathType Leaf) {
                Add-ModifyTarget $copilotGlobal
            }
        }
        "claude" {
            foreach ($candidate in @((Join-Path $WorkDir "CLAUDE.md"), (Join-Path $UserHome ".claude\CLAUDE.md"))) {
                if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                    Add-ModifyTarget $candidate
                }
            }
            $localMcp = Join-Path $WorkDir ".mcp.json"
            if (Test-SomaMcpFile -Path $localMcp) { Add-FileTarget $localMcp }
        }
    }

    if (-not $KeepConfig -and (Test-Path -LiteralPath $ConfigFile -PathType Leaf)) {
        Write-LogSkip "$ConfigFile (user config, not recorded in a manifest — preserved)"
    }
}

# User-authored data is never touched. Stated explicitly so the omission is
# auditable rather than accidental.
$PreservedPaths = @(
    (Join-Path $RepoDir ".soma\cells"),
    (Join-Path $RepoDir "fitness.jsonl"),
    (Join-Path $RepoDir "docs\snapshots")
)

# ── Reconcile the Plan With Disk ──────────────────────────────────
# A manifest entry can be recorded as a file but exist as a directory (or be
# gone entirely). Reclassify against reality so the printed plan never labels a
# directory as a file, and never advertises something it will not touch.
$realFiles = @()
$realDirs  = @()
foreach ($p in @($FilesToRemove + $DirsToRemove)) {
    if (Test-Path -LiteralPath $p -PathType Container) {
        if ($realDirs -notcontains $p) { $realDirs += $p }
    } elseif (Test-Path -LiteralPath $p -PathType Leaf) {
        if ($realFiles -notcontains $p) { $realFiles += $p }
    } else {
        Write-LogSkip "$p (recorded but no longer present)"
    }
}
$FilesToRemove = $realFiles
$DirsToRemove  = $realDirs

$realMod = @()
foreach ($m in $ModifyFiles) {
    if (Test-Path -LiteralPath $m -PathType Leaf) {
        if ($realMod -notcontains $m) { $realMod += $m }
    } else {
        Write-LogSkip "$m (recorded but no longer present)"
    }
}
$ModifyFiles = $realMod

$realConfig = @()
foreach ($c in $ConfigToRemove) {
    if (Test-Path -LiteralPath $c -PathType Leaf) {
        if ($realConfig -notcontains $c) { $realConfig += $c }
    } else {
        Write-LogSkip "$c (recorded but no longer present)"
    }
}
$ConfigToRemove = $realConfig

# ── Print the Plan ────────────────────────────────────────────────
$PlanCount = $FilesToRemove.Count + $DirsToRemove.Count + $ModifyFiles.Count + $ConfigToRemove.Count

Write-Host ""
Write-Host "The following will be removed/modified:"
foreach ($f in $FilesToRemove) { Write-Host "  - [FILE] $f" }
foreach ($d in $DirsToRemove)  { Write-Host "  - [DIR]  $d" }
foreach ($m in $ModifyFiles)   { Write-Host "  - [MOD]  $m (strip Soma sections, keep the rest)" }
foreach ($c in $ConfigToRemove) { Write-Host "  - [USER CONFIG] $c (your Soma configuration — pass -KeepConfig to keep it)" }

if ($PlanCount -eq 0) {
    Write-Host "Nothing to remove."
    exit 0
}

Write-Host ""
Write-Host "Preserved (user-authored, never removed):"
foreach ($p in $PreservedPaths) {
    if (Test-Path -LiteralPath $p) {
        Write-Host "  - [KEEP] $p"
    }
}

# ── Confirmation ──────────────────────────────────────────────────
if (-not $DryRun -and -not $Force) {
    if (-not (Test-HostInteractive)) {
        Write-Host ""
        Write-LogError "Confirmation is required but this host is non-interactive."
        Write-LogError "Aborting without removing anything (safe default)."
        Write-LogError "Re-run with -Force to skip confirmation, or -DryRun to preview."
        exit 2
    }
    Write-Host ""
    $confirm = Read-Host "Proceed with deletion? (y/N)"
    if ($confirm -notmatch '^[Yy]') {
        Write-Host "Aborted."
        exit 0
    }
}

# Everything install.ps1 could have backed up in place, newest-first candidates
# for the restore step below.
$RestoreTargets = @()
$RestoreTargets += $FilesToRemove
$RestoreTargets += $DirsToRemove
$RestoreTargets += $ModifyFiles

# Inventory the in-place backups BEFORE removing anything. Two reasons:
#  1. Removal can delete the parent directory we would scan.
#  2. Cleaning a [MOD] file writes a fresh .bak.<epoch> containing Soma content;
#     if we scanned afterwards we would offer to restore that instead of the
#     genuine pre-install backup, silently reinstating what we just removed.
$InPlaceBackups = @()
foreach ($t in $RestoreTargets) {
    $bak = Get-LatestBackupSibling -TargetPath $t
    if ($null -ne $bak) {
        $InPlaceBackups += [PSCustomObject]@{
            Target = $t
            Source = $bak.FullName
            IsDir  = [bool]$bak.PSIsContainer
        }
    }
}

# ── Execute ───────────────────────────────────────────────────────
if (-not $DryRun) {
    Write-Host ""
    foreach ($f in $FilesToRemove) {
        if (Test-Path -LiteralPath $f -PathType Leaf) {
            try {
                Remove-Item -LiteralPath $f -Force -ErrorAction Stop
                Write-LogInfo "removed $f"
            } catch {
                Set-Failure "could not remove $f : $($_.Exception.Message)"
            }
        }
    }

    foreach ($d in $DirsToRemove) {
        if (Test-Path -LiteralPath $d -PathType Container) {
            try {
                Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction Stop
                Write-LogInfo "removed $d\"
            } catch {
                Set-Failure "could not remove $d : $($_.Exception.Message)"
            }
        }
    }

    foreach ($m in $ModifyFiles) {
        try {
            Remove-SomaSection -FilePath $m
        } catch {
            Set-Failure "could not clean $m : $($_.Exception.Message)"
        }
    }

    foreach ($c in $ConfigToRemove) {
        if (Test-Path -LiteralPath $c -PathType Leaf) {
            try {
                Remove-Item -LiteralPath $c -Force -ErrorAction Stop
                Write-LogInfo "removed user config $c"
            } catch {
                Set-Failure "could not remove $c : $($_.Exception.Message)"
            }
        }
    }

    # Remove now-empty directories that Soma created itself.
    $SomaOwnedDirs = @(
        (Join-Path $UserHome ".gemini\config\plugins\governance"),
        (Join-Path $WorkDir ".github\instructions"),
        (Join-Path $RepoDir ".github\instructions")
    )
    foreach ($dir in $SomaOwnedDirs) {
        if (Test-Path -LiteralPath $dir -PathType Container) {
            $remaining = @(Get-ChildItem -LiteralPath $dir -Force -ErrorAction SilentlyContinue)
            if ($remaining.Count -eq 0) {
                try {
                    Remove-Item -LiteralPath $dir -Force -ErrorAction Stop
                    Write-LogInfo "removed empty $dir\"
                } catch {
                    Write-LogWarn "could not remove empty $dir : $($_.Exception.Message)"
                }
            }
        }
    }

    if ($ManifestExists -and (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        try {
            Remove-Item -LiteralPath $ManifestPath -Force -ErrorAction Stop
            Write-LogInfo "removed $ManifestPath"
        } catch {
            Set-Failure "could not remove manifest $ManifestPath : $($_.Exception.Message)"
        }
    }
}

# ── Restore Offer ─────────────────────────────────────────────────
# -Force skips only the deletion prompt. Suppressing recovery is -NoRestore.
$ConsolidatedBackupExists = ($BackupDir -and (Test-Path -LiteralPath $BackupDir -PathType Container))

# Maps the consolidated backup layout install.sh actually writes (genome/organs)
# onto the live locations. Deliberately NOT rules/skills — that mismatch is the
# bug in uninstall.sh's restore block.
function Get-ConsolidatedRestoreMap {
    $map = @()
    switch ($Platform) {
        "gemini" {
            if ($ManifestScope -eq "local") {
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "genome"); Destination = (Join-Path $WorkDir ".soma\rules"); IsDir = $true }
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "organs"); Destination = (Join-Path $WorkDir ".soma\skills"); IsDir = $true }
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "governance"); Destination = (Join-Path $WorkDir ".soma\plugins\governance"); IsDir = $true }
            } else {
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "genome"); Destination = (Join-Path $UserHome ".gemini\config\rules"); IsDir = $true }
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "organs"); Destination = (Join-Path $UserHome ".gemini\config\skills"); IsDir = $true }
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "governance"); Destination = (Join-Path $UserHome ".gemini\config\plugins\governance"); IsDir = $true }
            }
        }
        "kiro" {
            $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "genome"); Destination = (Join-Path $UserHome ".kiro\steering"); IsDir = $true }
            $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "organs"); Destination = (Join-Path $UserHome ".kiro\skills"); IsDir = $true }
            $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "hooks"); Destination = (Join-Path $UserHome ".kiro\hooks"); IsDir = $true }
        }
        "copilot" {
            $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "copilot-instructions.md"); Destination = (Join-Path $UserHome "copilot-instructions.md"); IsDir = $false }
        }
        "claude" {
            if ($ManifestScope -eq "local") {
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "CLAUDE.md"); Destination = (Join-Path $WorkDir "CLAUDE.md"); IsDir = $false }
            } else {
                $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir "CLAUDE.md"); Destination = (Join-Path $UserHome ".claude\CLAUDE.md"); IsDir = $false }
            }
            $map += [PSCustomObject]@{ Source = (Join-Path $BackupDir ".mcp.json"); Destination = (Join-Path $WorkDir ".mcp.json"); IsDir = $false }
        }
    }
    return @($map | Where-Object { Test-Path -LiteralPath $_.Source })
}

function Copy-RestoreItem {
    param([string]$Source, [string]$Destination, [bool]$IsDir)
    $parent = Split-Path -Parent $Destination
    if ($parent -and -not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force -ErrorAction Stop | Out-Null
    }
    if ($IsDir) {
        # Copy contents, because the backup directory name differs from the
        # destination name (genome -> rules, organs -> skills).
        if (-not (Test-Path -LiteralPath $Destination -PathType Container)) {
            New-Item -ItemType Directory -Path $Destination -Force -ErrorAction Stop | Out-Null
        }
        foreach ($child in @(Get-ChildItem -LiteralPath $Source -Force -ErrorAction Stop)) {
            Copy-Item -LiteralPath $child.FullName -Destination $Destination -Recurse -Force -ErrorAction Stop
        }
    } else {
        Copy-Item -LiteralPath $Source -Destination $Destination -Force -ErrorAction Stop
    }
}

$ConsolidatedMap = @()
if ($ConsolidatedBackupExists) {
    $ConsolidatedMap = @(Get-ConsolidatedRestoreMap)
}

$HaveRestoreSources = (($InPlaceBackups.Count -gt 0) -or ($ConsolidatedMap.Count -gt 0))

if ($NoRestore) {
    if ($HaveRestoreSources) {
        Write-Host ""
        Write-LogSkip "-NoRestore supplied — leaving backups in place without restoring."
    }
} elseif (-not $HaveRestoreSources) {
    if ($BackupDir -and -not $ConsolidatedBackupExists) {
        Write-Host ""
        Write-LogWarn "Manifest referenced backup_dir '$BackupDir' but it no longer exists."
    }
} else {
    Write-Host ""
    Write-Host "Backups available for restore:"
    foreach ($b in $InPlaceBackups) { Write-Host "  $($b.Source) -> $($b.Target)" }
    foreach ($m in $ConsolidatedMap) { Write-Host "  $($m.Source) -> $($m.Destination)" }

    if ($DryRun) {
        Write-Host "Dry-run: would offer to restore the previous configuration from the above."
    } else {
        $doRestore = $false
        if (Test-HostInteractive) {
            $restoreConfirm = Read-Host "Restore previous configuration from backup? (y/N)"
            if ($restoreConfirm -match '^[Yy]') { $doRestore = $true }
        } else {
            Write-LogSkip "Non-interactive host — not restoring. Copy the paths above manually if needed."
        }

        if ($doRestore) {
            foreach ($b in $InPlaceBackups) {
                try {
                    Copy-RestoreItem -Source $b.Source -Destination $b.Target -IsDir ([bool]$b.IsDir)
                    Write-LogInfo "restored $($b.Target)"
                } catch {
                    Set-Failure "could not restore $($b.Target) : $($_.Exception.Message)"
                }
            }
            foreach ($m in $ConsolidatedMap) {
                try {
                    Copy-RestoreItem -Source $m.Source -Destination $m.Destination -IsDir ([bool]$m.IsDir)
                    Write-LogInfo "restored $($m.Destination)"
                } catch {
                    Set-Failure "could not restore $($m.Destination) : $($_.Exception.Message)"
                }
            }
            Write-Host "Restore complete."
        } else {
            Write-Host "Skipping restore."
        }
    }
}

Write-Host ""
if ($DryRun) {
    Write-Host "Dry-run complete. Nothing was removed."
} elseif ($script:HadFailure) {
    Write-LogError "Uninstall finished with errors — see the messages above."
    exit 1
} else {
    Write-Host "Uninstall complete."
}
exit 0
