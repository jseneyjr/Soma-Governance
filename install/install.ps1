# Prism AI Steering — Native Windows PowerShell Installer
# Deploys steering rules and skills for Gemini, Kiro, and Copilot.
# NOTE: Hooks require bash (Git Bash, WSL, or MSYS2) and cannot run via native PowerShell.
#
# Usage:
#   .\install.ps1 [-Platform <gemini|kiro|copilot>] [-Mode <global|project>] [-DryRun]
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

    [switch]$DryRun,

    [switch]$Help
)

if ($Help) {
    Write-Host "Prism AI Steering — Windows PowerShell Installer"
    Write-Host "Usage: .\install.ps1 [[-Platform] <gemini|kiro|copilot>] [[-Mode] <global|project>] [-DryRun]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Platform   Target platform: gemini (default), kiro, or copilot"
    Write-Host "  -Mode       Copilot mode: global (default) or project"
    Write-Host "  -DryRun     Preview changes without copying or modifying files"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Note: Hooks require bash (Git Bash, WSL, or MSYS2) and are not deployed by this script."
    exit 0
}

# Ensure UTF-8 output encoding where supported
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # Ignore if console encoding cannot be modified
}

# ── Paths & Locations ─────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = (Get-Location).Path
}
$RepoDir = (Resolve-Path $ScriptDir).Path
$SourceRules = Join-Path $RepoDir "rules"
$SourceSkills = Join-Path $RepoDir "skills"
$ConfigFile = Join-Path $RepoDir "steering.conf"

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

# ── Configuration Loading ─────────────────────────────────────────
$Config = @{
    STEERING_PLATFORM = "gemini"
    TEAM_SIZE         = "solo"
    GIT_STRATEGY      = "trunk"
    APPROVAL_CHAIN    = "none"
    RULES_SUBSET      = "all"
    ENABLE_HOOKS      = "true"
}

if (Test-Path $ConfigFile) {
    Get-Content -Path $ConfigFile | ForEach-Object {
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
foreach ($key in @("STEERING_PLATFORM", "TEAM_SIZE", "GIT_STRATEGY", "APPROVAL_CHAIN", "RULES_SUBSET", "ENABLE_HOOKS")) {
    $envVal = [Environment]::GetEnvironmentVariable($key)
    if ($envVal) {
        $Config[$key] = $envVal
    }
}

# CLI argument takes precedence over environment / config
if ($Platform) {
    $Config["STEERING_PLATFORM"] = $Platform
}
$Platform = $Config["STEERING_PLATFORM"].ToLower()
$Mode = $Mode.ToLower()

# ── Enum Validation ───────────────────────────────────────────────
function Assert-Enum {
    param(
        [string]$Name,
        [string]$Value,
        [string[]]$Allowed
    )
    if ($Allowed -notcontains $Value) {
        Write-LogError "Invalid $Name: '$Value' (allowed: $($Allowed -join ' '))"
        exit 1
    }
}

Assert-Enum -Name "TEAM_SIZE" -Value $Config["TEAM_SIZE"] -Allowed @("solo", "small", "team", "enterprise")
Assert-Enum -Name "GIT_STRATEGY" -Value $Config["GIT_STRATEGY"] -Allowed @("trunk", "feature-branch", "gitflow")
Assert-Enum -Name "APPROVAL_CHAIN" -Value $Config["APPROVAL_CHAIN"] -Allowed @("none", "peer", "lead")
Assert-Enum -Name "RULES_SUBSET" -Value $Config["RULES_SUBSET"] -Allowed @("all", "core", "minimal")
Assert-Enum -Name "STEERING_PLATFORM" -Value $Platform -Allowed @("gemini", "kiro", "copilot")
Assert-Enum -Name "MODE" -Value $Mode -Allowed @("global", "project")

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

# ── Frontmatter Stripping ─────────────────────────────────────────
function Get-ContentWithoutFrontmatter {
    param([string]$FilePath)
    $lines = Get-Content -Path $FilePath
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
            $content = Get-Content -Path $gitWf -Raw
            if ($content -notmatch "## Team Workflow Overrides") {
                $override = @"


## Team Workflow Overrides (auto-generated)
- **All changes via feature branches**: Direct commits to main are prohibited for teams.
- **PR descriptions**: Every PR must include a summary of what changed and why.
- **Review required**: At least one peer review before merge.
- **Branch naming**: Use ``feature/<name>``, ``fix/<name>``, ``chore/<name>`` prefixes.
"@
                Add-Content -Path $gitWf -Value $override
                Write-LogInfo "$([System.IO.Path]::GetFileName($gitWf)): team branching enforced"
            }
        }
    }

    if ($Config["GIT_STRATEGY"] -eq "gitflow") {
        if ($DryRun) {
            Write-LogInfo "[dry-run] would apply gitflow strategy override to $(Split-Path -Leaf $gitWf)"
        } elseif (Test-Path $gitWf) {
            $content = Get-Content -Path $gitWf -Raw
            if ($content -notmatch "## Gitflow Overrides") {
                $override = @"


## Gitflow Overrides (auto-generated)
- **develop branch**: All feature branches merge to ``develop``, not ``main``.
- **release branches**: Cut ``release/<version>`` from ``develop`` when preparing a release.
- **hotfix branches**: Branch from ``main`` as ``hotfix/<name>``, merge back to both ``main`` and ``develop``.
"@
                Add-Content -Path $gitWf -Value $override
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
            $content = Get-Content -Path $destOps -Raw
            if ($content -notmatch "## Approval Chain Override") {
                $override = @"


## Approval Chain Override (auto-generated)
- **Approval required**: All destructive operations require $chain approval before execution.
- **Document approver**: When executing destructive ops, cite who approved and when.
"@
                Add-Content -Path $destOps -Value $override
                Write-LogInfo "$([System.IO.Path]::GetFileName($destOps)): $chain approval chain enforced"
            }
        }
    }
}

# ── Installation Banner ───────────────────────────────────────────
Write-Host "Installing steering rules for $Platform (OS: Windows, PowerShell)..."
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
        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" | Sort-Object Name
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
                    Write-LogInfo "skill/$skillName"
                }
                $skillCount++
            }
        }

        # Team overrides
        Apply-TeamOverrides -RulesDir $targetRules

        # Hook warning (PowerShell limitation)
        Write-Host ""
        Write-LogWarn "Hooks require bash (Git Bash, WSL, or MSYS2) — hook scripts were NOT installed."

        Write-Host ""
        if ($DryRun) {
            Write-Host "Dry-run complete. Would install $ruleCount rules, $skillCount skills to $targetRules"
        } else {
            Write-Host "Done! Installed $ruleCount rules, $skillCount skills to $targetRules"
            Write-Host "These will take effect on your next Gemini conversation."
        }
        if ($skippedCount -gt 0) {
            Write-Host "  ($skippedCount rules skipped — not in $Subset subset)"
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
        $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" | Sort-Object Name
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
                $content = Get-Content -Path $file.FullName
                $converted = $content | ForEach-Object {
                    $_ -replace '^trigger: always_on$', 'inclusion: always' `
                       -replace '^trigger: model_decision$', 'inclusion: manual'
                }
                Set-Content -Path $targetPath -Value $converted -Encoding UTF8
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
                    Write-LogInfo "skill/$skillName"
                }
                $skillCount++
            }
        }

        # Team overrides
        Apply-TeamOverrides -RulesDir $targetRules

        # Hook warning (PowerShell limitation)
        Write-Host ""
        Write-LogWarn "Hooks require bash (Git Bash, WSL, or MSYS2) — hook scripts were NOT installed."

        Write-Host ""
        if ($DryRun) {
            Write-Host "Dry-run complete. Would install $ruleCount rules, $skillCount skills to $targetRules"
        } else {
            Write-Host "Done! Installed $ruleCount rules, $skillCount skills to $targetRules"
            Write-Host "Rules with 'inclusion: always' are active on every interaction."
            Write-Host "Rules with 'inclusion: manual' can be referenced via #rulename."
        }
        if ($skippedCount -gt 0) {
            Write-Host "  ($skippedCount rules skipped — not in $Subset subset)"
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
            $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" | Sort-Object Name
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
                Write-Host "  ($skippedCount rules skipped — not in $Subset subset)"
            }
        } elseif ($Mode -eq "global") {
            $targetFile = Join-Path $UserHome "copilot-instructions.md"
            Write-Host "  Target: $targetFile"

            $ruleCount = 0
            $skippedCount = 0
            $ruleFiles = Get-ChildItem -Path $SourceRules -Filter "*.md" | Sort-Object Name

            if (-not $DryRun) {
                Backup-FileItem -FilePath $targetFile
                $header = @(
                    "# Copilot Global Instructions",
                    "",
                    "> Auto-generated from prism-ai-steering. Do not edit directly.",
                    ""
                )
                Set-Content -Path $targetFile -Value $header -Encoding UTF8
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
                    Add-Content -Path $targetFile -Value "---`n" -Encoding UTF8
                    Add-Content -Path $targetFile -Value $stripped -Encoding UTF8
                    Add-Content -Path $targetFile -Value "`n" -Encoding UTF8
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
                Write-Host "  ($skippedCount rules skipped — not in $Subset subset)"
            }
        }
    }
}
