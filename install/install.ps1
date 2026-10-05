# Soma - Native Windows PowerShell Installer
# Deploys steering rules and skills for Gemini, Kiro, and Copilot.
# NOTE: Hooks require bash (Git Bash, WSL, or MSYS2) and cannot run via native PowerShell.
#
# Usage:
#   .\install.ps1 [-Platform <gemini|kiro|copilot|claude|mcp>] [-Mode <global|project>] [-DryRun]
# Examples:
#   .\install.ps1
#   .\install.ps1 -Platform kiro
#   .\install.ps1 -Platform copilot -Mode project
#   .\install.ps1 -DryRun

[CmdletBinding()]
param (
    [Parameter(Position = 0)]
    [string]$Platform = "",

    [Parameter(Position = 1)]
    [string]$Mode = "global",

    [switch]$Hooks,

    [switch]$DryRun,

    [switch]$Help
)

if ($Help) {
    Write-Host "Soma - Windows PowerShell Installer"
    Write-Host "Usage: .\install.ps1 [[-Platform] <gemini|kiro|copilot|claude|mcp>] [[-Mode] <global|project>] [-Hooks] [-DryRun]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Platform   Target platform: gemini (default), kiro, copilot, claude, or mcp"
    Write-Host "  -Mode       Copilot/Claude mode: global (default) or project/local"
    Write-Host "  -Hooks      Install git pre-commit hook into .git/hooks"
    Write-Host "  -DryRun     Preview changes without copying or modifying files"
    Write-Host "  -Help       Show this help message"
    exit 0
}

# Ensure UTF-8 output encoding where supported
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Ignore if console encoding cannot be modified
}

# BOM-free UTF-8 writers (PS 5.1's -Encoding UTF8 adds a BOM)
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Write-Utf8File {
    param([string]$Path, [string]$Content)
    [System.IO.File]::WriteAllText($Path, $Content, $Utf8NoBom)
}
function Append-Utf8File {
    param([string]$Path, [string]$Content)
    [System.IO.File]::AppendAllText($Path, $Content, $Utf8NoBom)
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
# (Parity with install.sh, which resolves REPO_DIR as "$(dirname "$PRG")/..")
$RepoDir = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$SourceRules = Join-Path $RepoDir "genome"
$SourceSkills = Join-Path $RepoDir "organs"
$ConfigFile = Join-Path $RepoDir "soma.conf"

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

# ── Source Layout Validation ──────────────────────────────────────
# Fail loudly rather than silently reporting "Installed 0 rules".
if (-not (Test-Path -LiteralPath $SourceRules -PathType Container)) {
    Write-LogError "Rule source directory not found: $SourceRules"
    Write-LogError "Run this script from its checked-out location (<repo>/install/install.ps1)."
    exit 1
}

# ── Configuration Loading ─────────────────────────────────────────
$Config = @{
    SOMA_PLATFORM = "gemini"
    TEAM_SIZE         = "solo"
    GIT_STRATEGY      = "trunk"
    APPROVAL_CHAIN    = "none"
    RULES_SUBSET      = "all"
    ENABLE_HOOKS      = "true"
}

if (Test-Path $ConfigFile) {
    Get-Content -Path $ConfigFile -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        if ($line -match '^([A-Za-z0-9_]+)\s*=\s*(.*)$') {
            $key = $matches[1]
            $val = $matches[2]
            # Strip inline comments
            if ($val -match '^(.*?)\s*#.*$') {
                $val = $matches[1]
            }
            $val = $val.Trim().Trim('"').Trim("'")
            if ($Config.ContainsKey($key)) {
                $Config[$key] = $val
            }
        }
    }
}

# Environment variables take precedence over config file
foreach ($key in @("SOMA_PLATFORM", "TEAM_SIZE", "GIT_STRATEGY", "APPROVAL_CHAIN", "RULES_SUBSET", "ENABLE_HOOKS")) {
    $envVal = [Environment]::GetEnvironmentVariable($key)
    if ($envVal) {
        $Config[$key] = $envVal
    }
}

# CLI argument takes precedence over environment / config
if ($Platform) {
    $Config["SOMA_PLATFORM"] = $Platform
}
$Platform = $Config["SOMA_PLATFORM"].ToLower()
$Mode = $Mode.ToLower()

# ── Enum Validation ───────────────────────────────────────────────
function Assert-Enum {
    param(
        [string]$Name,
        [string]$Value,
        [string[]]$Allowed
    )
    if ($Allowed -notcontains $Value) {
        Write-LogError "Invalid ${Name}: '$Value' (allowed: $($Allowed -join ' '))"
        exit 1
    }
}

Assert-Enum -Name "TEAM_SIZE" -Value $Config["TEAM_SIZE"] -Allowed @("solo", "small", "team", "enterprise")
Assert-Enum -Name "GIT_STRATEGY" -Value $Config["GIT_STRATEGY"] -Allowed @("trunk", "feature-branch", "gitflow")
Assert-Enum -Name "APPROVAL_CHAIN" -Value $Config["APPROVAL_CHAIN"] -Allowed @("none", "peer", "lead")
Assert-Enum -Name "RULES_SUBSET" -Value $Config["RULES_SUBSET"] -Allowed @("all", "core", "minimal")
Assert-Enum -Name "SOMA_PLATFORM" -Value $Platform -Allowed @("gemini", "kiro", "copilot", "claude", "mcp")
Assert-Enum -Name "MODE" -Value $Mode -Allowed @("global", "project", "local")

# ── Subset Resolution ─────────────────────────────────────────────
$Subset = $Config["RULES_SUBSET"]
$AllowedRules = @()
switch ($Subset) {
    "minimal" { $AllowedRules = @("providence.md", "subagent-delegation.md", "destructive-ops.md") }
    "core"    { $AllowedRules = @("providence.md", "cost-optimization.md", "subagent-delegation.md", "testing.md", "git-workflow.md", "destructive-ops.md") }
    "all"     { $AllowedRules = @() }
}

function Should-InstallRule {
    param([string]$RuleName)
    if ($AllowedRules.Count -eq 0) { return $true }
    return ($AllowedRules -contains $RuleName)
}

# ── User Profile Resolution ───────────────────────────────────────
$UserHome = $env:USERPROFILE
if (-not $UserHome) {
    $UserHome = [Environment]::GetFolderPath('UserProfile')
}
if (-not $UserHome) {
    $UserHome = $HOME
}

# ── Exact Ownership & MCP Merge ──────────────────────────────────
$InstalledFiles = [System.Collections.Generic.List[string]]::new()
$InstalledOrgans = [System.Collections.Generic.List[string]]::new()
$InstalledHooks = [System.Collections.Generic.List[string]]::new()
$InstalledMcpConfigs = [System.Collections.Generic.List[string]]::new()
$BackupDir = $null
$InstallScope = "global"
if ($Platform -eq "mcp" -or
    ($Platform -eq "claude" -and ($Mode -eq "project" -or $Mode -eq "local")) -or
    ($Platform -eq "copilot" -and $Mode -eq "project")) {
    $InstallScope = "local"
}

function Record-InstalledFile { param([string]$Path) if ($Path) { $InstalledFiles.Add($Path) } }
function Record-InstalledOrgan { param([string]$Path) if ($Path) { $InstalledOrgans.Add($Path) } }
function Record-InstalledHook { param([string]$Path) if ($Path) { $InstalledHooks.Add($Path) } }
function Record-McpConfig { param([string]$Path) if ($Path) { $InstalledMcpConfigs.Add($Path) } }

function Write-InstallManifest {
    if ($DryRun) { return }
    $manifestBase = $UserHome
    if ($InstallScope -eq "local") { $manifestBase = (Get-Location).Path }
    $manifestDir = Join-Path $manifestBase ".soma"
    if (-not (Test-Path -LiteralPath $manifestDir -PathType Container)) {
        New-Item -ItemType Directory -Path $manifestDir -Force | Out-Null
    }
    $version = "unknown"
    $versionFile = Join-Path $RepoDir "VERSION"
    if (Test-Path -LiteralPath $versionFile -PathType Leaf) {
        $version = (Get-Content -LiteralPath $versionFile -Raw -Encoding UTF8).Trim()
    }
    $manifestPath = Join-Path $manifestDir "manifest.json"
    $existingPathLines = $null
    if ($InstallScope -ne "local" -and (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        try {
            $rawExisting = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($null -ne $rawExisting -and $null -ne $rawExisting.path_lines) {
                $existingPathLines = $rawExisting.path_lines
            }
        } catch {}
    }
    $manifest = [ordered]@{
        "version" = $version
        "installed_at" = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        "platform" = $Platform
        "scope" = $InstallScope
        "rules_subset" = $Subset
        "source_repo" = $RepoDir
        "backup_dir" = $BackupDir
        "files" = @($InstalledFiles)
        "organs" = @($InstalledOrgans)
        "hooks" = @($InstalledHooks)
        "mcp_configs" = @($InstalledMcpConfigs)
    }
    if ($null -ne $existingPathLines) {
        $manifest["path_lines"] = $existingPathLines
    }
    Write-Utf8File -Path $manifestPath -Content (($manifest | ConvertTo-Json -Depth 8) + "`n")
}

function Merge-SomaMcpConfig {
    param([string]$Path, [string]$Workspace)
    $data = [PSCustomObject]@{}
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 -ErrorAction Stop
        try {
            $data = $raw | ConvertFrom-Json -ErrorAction Stop
        } catch {
            throw "Invalid JSON in ${Path}: $($_.Exception.Message)"
        }
        if ($null -eq $data -or $data -is [Array] -or $data -is [string] -or $data -is [ValueType]) {
            throw "MCP configuration root must be a JSON object: $Path"
        }
    }

    $serversProperty = $data.PSObject.Properties["mcpServers"]
    if ($null -eq $serversProperty) {
        $data | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
    } elseif ($null -eq $serversProperty.Value -or $serversProperty.Value -is [Array] -or
              $serversProperty.Value -is [string] -or $serversProperty.Value -is [ValueType]) {
        throw "MCP configuration field 'mcpServers' must be a JSON object: $Path"
    }
    $servers = $data.PSObject.Properties["mcpServers"].Value

    # Prefer a normally installed soma_mcp package. A checkout-only install
    # gets a documented source PYTHONPATH fallback instead of using the
    # checkout as the governed workspace/cwd. Uses isolated mode (-I) and
    # importlib.util.find_spec to check without executing workspace code (BUG-044).
    $sourceFallback = $null
    try {
        & python3 -I -c "import sys, importlib.util; sys.path.append(sys.argv[1]); sys.exit(0 if importlib.util.find_spec('soma_mcp') is not None else 1)" "$Workspace" *> $null
        if ($LASTEXITCODE -ne 0) { $sourceFallback = $RepoDir }
    } catch {
        $sourceFallback = $RepoDir
    }
    $serverEnv = [ordered]@{ "SOMA_WORKSPACE" = $Workspace }
    if ($sourceFallback) { $serverEnv["PYTHONPATH"] = $sourceFallback }
    $somaEntry = [PSCustomObject][ordered]@{
        "command" = "python3"
        "args" = @("-m", "soma_mcp")
        "cwd" = $Workspace
        "env" = [PSCustomObject]$serverEnv
    }
    $somaProperty = $servers.PSObject.Properties["soma"]
    if ($null -eq $somaProperty) {
        $servers | Add-Member -NotePropertyName "soma" -NotePropertyValue $somaEntry
    } else {
        $somaProperty.Value = $somaEntry
    }

    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent -PathType Container)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $tempPath = "$Path.soma.$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        Write-Utf8File -Path $tempPath -Content (($data | ConvertTo-Json -Depth 12) + "`n")
        Move-Item -LiteralPath $tempPath -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $tempPath -PathType Leaf) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }
}

# ── Backup Utilities ──────────────────────────────────────────────
function Backup-FileItem {
    param([string]$FilePath)
    if ($DryRun) { return }
    if (Test-Path -Path $FilePath -PathType Leaf) {
        $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $backupPath = "$FilePath.bak.$epoch"
        Copy-Item -Path $FilePath -Destination $backupPath -Force
        $leafName = Split-Path -Leaf $FilePath
        $bakLeaf = Split-Path -Leaf $backupPath
        Write-LogWarn "$leafName backed up to $bakLeaf"
    }
}

function Backup-DirItem {
    param([string]$DirPath)
    if ($DryRun) { return }
    if (Test-Path -Path $DirPath -PathType Container) {
        $epoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $backupPath = "$DirPath.bak.$epoch"
        if (Test-Path $backupPath) {
            Remove-Item -Path $backupPath -Recurse -Force
        }
        Copy-Item -Path $DirPath -Destination $backupPath -Recurse -Force
        $leafName = Split-Path -Leaf $DirPath
        $bakLeaf = Split-Path -Leaf $backupPath
        Write-LogWarn "$leafName/ backed up to $bakLeaf/"
    }
}

# ── Hooks Installation ───────────────────────────────────────────
function Install-Hooks {
    param(
        [string]$RepoDir,
        [string]$TargetHooksDir
    )

    if ($Config.ENABLE_HOOKS -ne "true") {
        return
    }

    $targetFile = Join-Path $TargetHooksDir "hooks.json"

    if ($DryRun) {
        Write-LogInfo "[dry-run] would install hooks.json to $TargetHooksDir"
        return
    }

    if (-not (Test-Path -LiteralPath $TargetHooksDir -PathType Container)) {
        New-Item -ItemType Directory -Path $TargetHooksDir -Force | Out-Null
    }

    # Resolve working Python interpreter
    $pythonCmd = "python"
    foreach ($py in @("python", "python3", "py")) {
        if (Get-Command $py -ErrorAction SilentlyContinue) {
            try {
                $null = & $py -c "import sys; sys.exit(0)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $pythonCmd = $py
                    break
                }
            } catch {}
        }
    }

    $hooksJson = @"
{
  "governance-monitor": {
    "PreInvocation": [
      {
        "type": "command",
        "command": "$pythonCmd -m soma_cli.hooks pre-invocation",
        "timeout": 15
      }
    ]
  },
  "safety-gate": {
    "PreToolUse": [
      {
        "matcher": "run_command",
        "hooks": [
          {
            "type": "command",
            "command": "$pythonCmd -m soma_cli.hooks safety-gate",
            "timeout": 5
          }
        ]
      }
    ]
  },
  "session-close": {
    "Stop": [
      {
        "type": "command",
        "command": "$pythonCmd -m soma_cli.hooks session-close",
        "timeout": 30
      }
    ]
  }
}
"@

    try {
        $null = $hooksJson | ConvertFrom-Json
    } catch {
        Write-LogError "hooks.json rendering produced invalid JSON: $_"
        return
    }

    Backup-FileItem -FilePath $targetFile
    Write-Utf8File -Path $targetFile -Content ($hooksJson + "`n")
    Record-InstalledHook -Path $targetFile
    Write-LogInfo "installed hooks.json"
}

# ── Frontmatter Stripping ─────────────────────────────────────────
function Get-ContentWithoutFrontmatter {
    param([string]$FilePath)
    $lines = Get-Content -Path $FilePath -Encoding UTF8
    $inFront = $false
    $found = $false
    $output = [System.Collections.Generic.List[string]]::new()

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ($i -eq 0 -and $line.Trim() -eq "---") {
            $inFront = $true
            continue
        }
        if ($inFront -and $line.Trim() -eq "---") {
            $inFront = $false
            $found = $true
            continue
        }
        if (-not $inFront) {
            $output.Add($line)
        }
    }
    return $output
}

# ── Team Overrides ────────────────────────────────────────────────
function Apply-TeamOverrides {
    param([string]$RulesDir)

    $gitWf = Join-Path $RulesDir "git-workflow.md"
    if (Test-Path (Join-Path $RulesDir "git-workflow.instructions.md")) {
        $gitWf = Join-Path $RulesDir "git-workflow.instructions.md"
    }

    if ($Config["TEAM_SIZE"] -ne "solo") {
        if ($DryRun) {
            Write-LogInfo "[dry-run] would apply team branching override to $(Split-Path -Leaf $gitWf)"
        } elseif (Test-Path $gitWf) {
            $content = Get-Content -Path $gitWf -Raw -Encoding UTF8
            if ($content -notmatch "## Team Workflow Overrides") {
                $override = @"


## Team Workflow Overrides (auto-generated)
- **All changes via feature branches**: Direct commits to main are prohibited for teams.
- **PR descriptions**: Every PR must include a summary of what changed and why.
- **Review required**: At least one peer review before merge.
- **Branch naming**: Use ``feature/<name>``, ``fix/<name>``, ``chore/<name>`` prefixes.
"@
                Add-Content -Path $gitWf -Value $override -Encoding UTF8
                Write-LogInfo "$([System.IO.Path]::GetFileName($gitWf)): team branching enforced"
            }
        }
    }

    if ($Config["GIT_STRATEGY"] -eq "gitflow") {
        if ($DryRun) {
            Write-LogInfo "[dry-run] would apply gitflow strategy override to $(Split-Path -Leaf $gitWf)"
        } elseif (Test-Path $gitWf) {
            $content = Get-Content -Path $gitWf -Raw -Encoding UTF8
            if ($content -notmatch "## Gitflow Overrides") {
                $override = @"


## Gitflow Overrides (auto-generated)
- **develop branch**: All feature branches merge to ``develop``, not ``main``.
- **release branches**: Cut ``release/<version>`` from ``develop`` when preparing a release.
- **hotfix branches**: Branch from ``main`` as ``hotfix/<name>``, merge back to both ``main`` and ``develop``.
"@
                Add-Content -Path $gitWf -Value $override -Encoding UTF8
                Write-LogInfo "$([System.IO.Path]::GetFileName($gitWf)): gitflow strategy applied"
            }
        }
    }

    $destOps = Join-Path $RulesDir "destructive-ops.md"
    if (Test-Path (Join-Path $RulesDir "destructive-ops.instructions.md")) {
        $destOps = Join-Path $RulesDir "destructive-ops.instructions.md"
    }

    if ($Config["APPROVAL_CHAIN"] -ne "none") {
        $chain = $Config["APPROVAL_CHAIN"]
        if ($DryRun) {
            Write-LogInfo "[dry-run] would apply $chain approval chain override to $(Split-Path -Leaf $destOps)"
        } elseif (Test-Path $destOps) {
            $content = Get-Content -Path $destOps -Raw -Encoding UTF8
            if ($content -notmatch "## Approval Chain Override") {
                $override = @"


## Approval Chain Override (auto-generated)
- **Approval required**: All destructive operations require $chain approval before execution.
- **Document approver**: When executing destructive ops, cite who approved and when.
"@
                Add-Content -Path $destOps -Value $override -Encoding UTF8
                Write-LogInfo "$([System.IO.Path]::GetFileName($destOps)): $chain approval chain enforced"
            }
        }
    }
}

# ── Installation Banner ───────────────────────────────────────────
Write-Host "Installing Soma for $Platform (OS: Windows, PowerShell)..."
Write-Host "  Source: $SourceRules"
Write-Host "  Config: TEAM_SIZE=$($Config['TEAM_SIZE']) GIT_STRATEGY=$($Config['GIT_STRATEGY']) RULES_SUBSET=$($Config['RULES_SUBSET'])"
if ($DryRun) {
    Write-Host "  Mode:   DRY-RUN (no files will be modified)"
}
Write-Host ""

# ── Platform Deployment ───────────────────────────────────────────
switch ($Platform) {
    "gemini" {
        $targetRules = Join-Path $UserHome ".gemini\config\rules"
        $targetSkills = Join-Path $UserHome ".gemini\config\skills"

        if (-not $DryRun) {
            if (-not (Test-Path $targetRules)) { New-Item -ItemType Directory -Path $targetRules -Force | Out-Null }
            if (-not (Test-Path $targetSkills)) { New-Item -ItemType Directory -Path $targetSkills -Force | Out-Null }
        }

        # Install rules
        $ruleCount = 0
        $skippedCount = 0
        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" -Recurse -Force -File | Sort-Object Name
        foreach ($file in $ruleFiles) {
            $name = $file.Name
            if (-not (Should-InstallRule $name)) {
                Write-LogSkip "$name (not in $Subset subset)"
                $skippedCount++
                continue
            }
            $targetPath = Join-Path $targetRules $name
            if ($DryRun) {
                Write-LogInfo "[dry-run] would install $name -> $targetPath"
            } else {
                Backup-FileItem -FilePath $targetPath
                Copy-Item -Path $file.FullName -Destination $targetPath -Force
                Record-InstalledFile -Path $targetPath
                Write-LogInfo "$name"
            }
            $ruleCount++
        }

        # Install skills
        $skillCount = 0
        if (Test-Path $SourceSkills) {
            $skillDirs = Get-ChildItem -Path $SourceSkills -Directory | Sort-Object Name
            foreach ($dir in $skillDirs) {
                $skillName = $dir.Name
                $destSkill = Join-Path $targetSkills $skillName
                if ($DryRun) {
                    Write-LogInfo "[dry-run] would install skill/$skillName -> $destSkill"
                } else {
                    Backup-DirItem -DirPath $destSkill
                    if (Test-Path $destSkill) {
                        Remove-Item -Path $destSkill -Recurse -Force
                    }
                    Copy-Item -Path $dir.FullName -Destination $destSkill -Recurse -Force
                    Record-InstalledOrgan -Path $destSkill
                    Write-LogInfo "skill/$skillName"
                }
                $skillCount++
            }
        }

        # Team overrides
        Apply-TeamOverrides -RulesDir $targetRules

        # Hooks
        $targetHooks = Join-Path $UserHome ".gemini\config\plugins\governance"
        if ($InstallScope -eq "local") {
            $targetHooks = Join-Path (Get-Location).Path ".soma\plugins\governance"
        }
        Install-Hooks -RepoDir $RepoDir -TargetHooksDir $targetHooks

        Write-Host ""
        if ($DryRun) {
            Write-Host "Dry-run complete. Would install $ruleCount rules, $skillCount skills to $targetRules"
        } else {
            Write-Host "Done! Installed $ruleCount rules, $skillCount skills to $targetRules"
            Write-Host "These will take effect on your next Gemini conversation."
        }
        if ($skippedCount -gt 0) {
            Write-Host "  ($skippedCount rules skipped - not in $Subset subset)"
        }
    }

    "kiro" {
        $targetRules = Join-Path $UserHome ".kiro\steering"
        $targetSkills = Join-Path $UserHome ".kiro\skills"

        if (-not $DryRun) {
            if (-not (Test-Path $targetRules)) { New-Item -ItemType Directory -Path $targetRules -Force | Out-Null }
            if (-not (Test-Path $targetSkills)) { New-Item -ItemType Directory -Path $targetSkills -Force | Out-Null }
        }

        $ruleCount = 0
        $skippedCount = 0
        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" -Recurse -Force -File | Sort-Object Name
        foreach ($file in $ruleFiles) {
            $name = $file.Name
            if (-not (Should-InstallRule $name)) {
                Write-LogSkip "$name (not in $Subset subset)"
                $skippedCount++
                continue
            }
            $targetPath = Join-Path $targetRules $name
            if ($DryRun) {
                Write-LogInfo "[dry-run] would install $name (converted syntax) -> $targetPath"
            } else {
                Backup-FileItem -FilePath $targetPath
                $content = Get-Content -Path $file.FullName -Encoding UTF8
                $converted = $content | ForEach-Object {
                    $_ -replace '^trigger: always_on$', 'inclusion: always' `
                       -replace '^trigger: model_decision$', 'inclusion: manual'
                }
                Set-Content -Path $targetPath -Value $converted -Encoding UTF8
                Record-InstalledFile -Path $targetPath
                Write-LogInfo "$name"
            }
            $ruleCount++
        }

        # Install skills
        $skillCount = 0
        if (Test-Path $SourceSkills) {
            $skillDirs = Get-ChildItem -Path $SourceSkills -Directory | Sort-Object Name
            foreach ($dir in $skillDirs) {
                $skillName = $dir.Name
                $destSkill = Join-Path $targetSkills $skillName
                if ($DryRun) {
                    Write-LogInfo "[dry-run] would install skill/$skillName -> $destSkill"
                } else {
                    Backup-DirItem -DirPath $destSkill
                    if (Test-Path $destSkill) {
                        Remove-Item -Path $destSkill -Recurse -Force
                    }
                    Copy-Item -Path $dir.FullName -Destination $destSkill -Recurse -Force
                    Record-InstalledOrgan -Path $destSkill
                    Write-LogInfo "skill/$skillName"
                }
                $skillCount++
            }
        }

        # Team overrides
        Apply-TeamOverrides -RulesDir $targetRules

        # Kiro settings are global, while the server governs this project.
        $kiroMcpFile = Join-Path $UserHome ".kiro\settings\mcp.json"
        $workspace = (Get-Location).Path
        if ($DryRun) {
            Write-LogInfo "[dry-run] would merge soma into $kiroMcpFile"
        } else {
            Backup-FileItem -FilePath $kiroMcpFile
            Merge-SomaMcpConfig -Path $kiroMcpFile -Workspace $workspace
            Record-McpConfig -Path $kiroMcpFile
            Write-LogInfo "merged soma into mcp.json"
        }

        # Hooks
        $targetHooks = Join-Path $UserHome ".kiro\hooks"
        Install-Hooks -RepoDir $RepoDir -TargetHooksDir $targetHooks

        Write-Host ""
        if ($DryRun) {
            Write-Host "Dry-run complete. Would install $ruleCount rules, $skillCount skills to $targetRules"
        } else {
            Write-Host "Done! Installed $ruleCount rules, $skillCount skills to $targetRules"
            Write-Host "Rules with 'inclusion: always' are active on every interaction."
            Write-Host "Rules with 'inclusion: manual' can be referenced via #rulename."
        }
        if ($skippedCount -gt 0) {
            Write-Host "  ($skippedCount rules skipped - not in $Subset subset)"
        }
    }

    "copilot" {
        if ($Mode -eq "project") {
            $targetDir = Join-Path (Get-Location).Path ".github\instructions"
            Write-Host "  Target: $targetDir"
            if (-not $DryRun) {
                if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
            }

            $ruleCount = 0
            $skippedCount = 0
            $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" -Recurse -Force -File | Sort-Object Name
            foreach ($file in $ruleFiles) {
                $filename = $file.Name
                if (-not (Should-InstallRule $filename)) {
                    Write-LogSkip "$filename (not in $Subset subset)"
                    $skippedCount++
                    continue
                }
                $baseName = [System.IO.Path]::GetFileNameWithoutExtension($filename)
                $instructionFile = "${baseName}.instructions.md"
                $targetPath = Join-Path $targetDir $instructionFile
                if ($DryRun) {
                    Write-LogInfo "[dry-run] would install $instructionFile -> $targetPath"
                } else {
                    Backup-FileItem -FilePath $targetPath
                    $stripped = Get-ContentWithoutFrontmatter -FilePath $file.FullName
                    Set-Content -Path $targetPath -Value $stripped -Encoding UTF8
                    Record-InstalledFile -Path $targetPath
                    Write-LogInfo "$instructionFile"
                }
                $ruleCount++
            }

            Apply-TeamOverrides -RulesDir $targetDir

            Write-Host ""
            if ($DryRun) {
                Write-Host "Dry-run complete. Would install $ruleCount instruction files to $targetDir"
            } else {
                Write-Host "Done! Installed $ruleCount instruction files to $targetDir"
                Write-Host "Commit .github/instructions/ to share with your team."
            }
            if ($skippedCount -gt 0) {
                Write-Host "  ($skippedCount rules skipped - not in $Subset subset)"
            }
        } elseif ($Mode -eq "global") {
            $targetFile = Join-Path $UserHome "copilot-instructions.md"
            Write-Host "  Target: $targetFile"

            $ruleCount = 0
            $skippedCount = 0
            $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" -Recurse -Force -File | Sort-Object Name

            if (-not $DryRun) {
                Backup-FileItem -FilePath $targetFile
                $headerText = "# Copilot Global Instructions`r`n`r`n> Auto-generated from soma. Do not edit directly.`r`n`r`n"
                Write-Utf8File -Path $targetFile -Content $headerText
                Record-InstalledFile -Path $targetFile
            }

            foreach ($file in $ruleFiles) {
                $filename = $file.Name
                if (-not (Should-InstallRule $filename)) {
                    Write-LogSkip "$filename (not in $Subset subset)"
                    $skippedCount++
                    continue
                }
                if ($DryRun) {
                    Write-LogInfo "[dry-run] would merge $filename into $targetFile"
                } else {
                    $stripped = Get-ContentWithoutFrontmatter -FilePath $file.FullName
                    $ruleContent = "---`r`n" + ($stripped -join "`r`n") + "`r`n`r`n"
                    Append-Utf8File -Path $targetFile -Content $ruleContent
                    Write-LogInfo "$filename"
                }
                $ruleCount++
            }

            Write-Host ""
            if ($DryRun) {
                Write-Host "Dry-run complete. Would merge $ruleCount rules into $targetFile"
            } else {
                Write-Host "Done! All rules merged into $targetFile"
                Write-Host "Enable 'Custom Instructions' in your IDE's Copilot settings."
            }
            if ($skippedCount -gt 0) {
                Write-Host "  ($skippedCount rules skipped - not in $Subset subset)"
            }
        }
    }

    "claude" {
        $targetDir = ""
        $isLocal = ($Mode -eq "project" -or $Mode -eq "local")
        if ($isLocal) {
            $targetDir = (Get-Location).Path
            $targetFile = Join-Path $targetDir "CLAUDE.md"
            $mcpFile = Join-Path $targetDir ".mcp.json"
        } else {
            $targetDir = Join-Path $UserHome ".claude"
            $targetFile = Join-Path $targetDir "CLAUDE.md"
        }

        Write-Host "  Target: $targetFile"
        if (-not $DryRun) {
            if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
            Backup-FileItem -FilePath $targetFile
            $header = @(
                "# Soma Governance Rules",
                "",
                "> Auto-generated by Soma. Do not edit directly.",
                ""
            )
            Set-Content -Path $targetFile -Value $header -Encoding UTF8
            Record-InstalledFile -Path $targetFile
        }

        $ruleCount = 0
        $skippedCount = 0
        $skillCount = 0
        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" -Recurse -Force -File | Sort-Object Name

        foreach ($file in $ruleFiles) {
            $filename = $file.Name
            if (-not (Should-InstallRule $filename)) {
                Write-LogSkip "$filename (not in $Subset subset)"
                $skippedCount++
                continue
            }
            if ($DryRun) {
                Write-LogInfo "[dry-run] would merge $filename into $targetFile"
            } else {
                $stripped = Get-ContentWithoutFrontmatter -FilePath $file.FullName
                Add-Content -Path $targetFile -Value "---`n" -Encoding UTF8
                Add-Content -Path $targetFile -Value $stripped -Encoding UTF8
                Add-Content -Path $targetFile -Value "`n" -Encoding UTF8
                Write-LogInfo "$filename"
            }
            $ruleCount++
        }

        if (Test-Path $SourceSkills) {
            $skillDirs = Get-ChildItem -Path $SourceSkills -Directory
            $skillCount = $skillDirs.Count
        }

        if ($isLocal) {
            if ($DryRun) {
                Write-LogInfo "[dry-run] would create/update .mcp.json at $mcpFile"
            } else {
                Backup-FileItem -FilePath $mcpFile
                Merge-SomaMcpConfig -Path $mcpFile -Workspace $targetDir
                Record-McpConfig -Path $mcpFile
                Write-LogInfo "merged soma into .mcp.json"
            }
        }

        Write-Host ""
        if ($DryRun) {
            Write-Host "Dry-run complete. Would merge $ruleCount rules into $targetFile"
        } else {
            Write-Host "Done! All rules merged into $targetFile ($skillCount skills tracked)"
            if ($isLocal) {
                Write-Host "Created .mcp.json for local MCP server."
            } else {
                Write-Host "For global mode, run 'claude mcp add soma python3 -m soma_mcp' manually."
                Write-Host "Note: Global hooks must be configured in ~/.claude/settings.json"
            }
        }
        if ($skippedCount -gt 0) {
            Write-Host "  ($skippedCount rules skipped - not in $Subset subset)"
        }
    }

    "mcp" {
        $targetDir = (Get-Location).Path
        $mcpFile = Join-Path $targetDir ".mcp.json"
        
        Write-Host "  Target: $mcpFile"
        if ($DryRun) {
            Write-LogInfo "[dry-run] would create/update .mcp.json at $mcpFile"
        } else {
            Backup-FileItem -FilePath $mcpFile
            Merge-SomaMcpConfig -Path $mcpFile -Workspace $targetDir
            Record-McpConfig -Path $mcpFile
            Write-LogInfo "merged soma into .mcp.json"
        }
    }
}

if ($Hooks -or $env:INSTALL_GIT_HOOKS -eq "true") {
    $gitHooksDir = Join-Path (Get-Location).Path ".git\hooks"
    if (Test-Path -LiteralPath $gitHooksDir -PathType Container) {
        $preCommitPath = Join-Path $gitHooksDir "pre-commit"
        if ($DryRun) {
            Write-Host "[dry-run] would install git pre-commit hook."
        } else {
            Backup-FileItem -FilePath $preCommitPath
            $hookBody = @'
#!/bin/sh
# Soma Git Pre-Commit Hook (cross-platform runner)
if command -v soma >/dev/null 2>&1; then
  soma hook pre-commit || exit $?
elif python3 -c 'import soma_cli' >/dev/null 2>&1; then
  python3 -m soma_cli.hooks pre-commit || exit $?
elif python -c 'import soma_cli' >/dev/null 2>&1; then
  python -m soma_cli.hooks pre-commit || exit $?
elif py -3 -c 'import soma_cli' >/dev/null 2>&1; then
  py -3 -m soma_cli.hooks pre-commit || exit $?
else
  echo "soma pre-commit: cannot run governance checks. 'soma' is not on PATH" >&2
  exit 1
fi
'@
            $cleanHookBody = $hookBody.Replace("`r`n", "`n") + "`n"
            Write-Utf8File -Path $preCommitPath -Content $cleanHookBody
            if ($IsLinux -or $IsMacOS) {
                try { chmod +x $preCommitPath 2>$null } catch {}
            }
            Record-InstalledHook -Path $preCommitPath
            Write-Host "Installed git pre-commit hook."
        }
    } else {
        Write-Host "No .git\hooks directory found, skipping pre-commit hook installation."
    }
}

if (-not $DryRun) {
    Write-InstallManifest
}

# CLI PATH guidance (BUG-041). Advisory only: prints the line to run, never
# edits the user's environment, and never fails the install. Runs from the
# Soma checkout so the governed project cannot shadow soma_cli via sys.path[0].
if (-not $DryRun -and -not (Get-Command soma -ErrorAction SilentlyContinue)) {
    $savedExitCode = $LASTEXITCODE
    Push-Location -LiteralPath $RepoDir
    try {
        foreach ($py in @("python", "python3")) {
            if (-not (Get-Command $py -ErrorAction SilentlyContinue)) { continue }
            try {
                $hint = & $py -m soma_cli.pathcheck --hint 2>$null
                if ($LASTEXITCODE -eq 0) {
                    if ($hint) { Write-Host ""; $hint | ForEach-Object { Write-Host $_ } }
                    break
                }
            } catch { }
        }
    } finally {
        Pop-Location
        $global:LASTEXITCODE = $savedExitCode
    }
}
