<#
SPINDEP - Windows bootstrap
============================
Run this FIRST, right after cloning, before install.py:

    powershell -ExecutionPolicy Bypass -File bootstrap.ps1

Why this exists: install.py is a Python script, so it can't run at all on a
machine that has no Python - there's nothing to interpret it. This script
checks for Python and Node.js first (using nothing but built-in PowerShell),
offers to install whichever is missing via winget, and then hands off to
install.py.

Node.js is only needed for 'spin start' (the browser-based web GUI) - every
other 'spin' command works without it, so declining that install is fine if
you only plan to use the command line.
#>

function Write-Ok($msg)   { Write-Host "  [OK]    $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host "  [..]    $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "  [!!]    $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  [ERROR] $msg" -ForegroundColor Red }

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Confirm-Action($prompt) {
    $reply = Read-Host "  $prompt [Y/n]"
    return ($reply -eq "" -or $reply -match '^(y|yes)$')
}

function Update-SessionPath {
    # winget updates the registry, not this already-running process - pull
    # the fresh PATH in so a just-installed command works immediately.
    try {
        $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
        $user    = [System.Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$machine;$user"
    } catch {}
}

Write-Host ""
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Host "  SPINDEP Setup - checking prerequisites" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# PYTHON
# ============================================================

$pythonCmd = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (-not (Test-Command $candidate)) { continue }
    try {
        $verText = (& $candidate --version 2>&1) -join " "
        if ($verText -match '(\d+)\.(\d+)') {
            $maj = [int]$Matches[1]; $min = [int]$Matches[2]
            if ($maj -gt 3 -or ($maj -eq 3 -and $min -ge 9)) {
                $pythonCmd = $candidate
                Write-Ok "Python found: $candidate ($verText)"
                break
            } else {
                Write-Warn "$candidate is $verText - SPINDEP needs 3.9+"
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Warn "Python 3.9+ was not found on this system."
    Write-Host "  SPINDEP is a Python tool - it can't run without it."
    Write-Host ""
    if (Confirm-Action "Install Python automatically now via winget?") {
        if (Test-Command "winget") {
            Write-Info "Installing Python (winget install Python.Python.3.13)..."
            winget install -e --id Python.Python.3.13 --accept-source-agreements --accept-package-agreements
            Update-SessionPath
            foreach ($candidate in @("py", "python", "python3")) {
                if (Test-Command $candidate) { $pythonCmd = $candidate; break }
            }
        } else {
            Write-Err "winget is not available on this system."
        }
    }

    if (-not $pythonCmd) {
        Write-Host ""
        Write-Err "Could not set up Python automatically."
        Write-Host "  Install it manually from https://www.python.org/downloads/"
        Write-Host "  then re-run:  powershell -ExecutionPolicy Bypass -File bootstrap.ps1"
        exit 1
    }
    Write-Ok "Python installed and ready: $pythonCmd"
}

# ============================================================
# NODE.JS  (only needed for 'spin start', the browser GUI)
# ============================================================

Write-Host ""
if (-not (Test-Command "npm")) {
    Write-Warn "Node.js was not found."
    Write-Host "  It's only needed so you can VIEW SPINDEP in your browser ('spin start')."
    Write-Host "  Every other command (spin run, spin test, spin validate, ...) works without it."
    Write-Host ""
    if (Confirm-Action "Install Node.js automatically now via winget?") {
        if (Test-Command "winget") {
            Write-Info "Installing Node.js (winget install OpenJS.NodeJS.LTS)..."
            winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
            Update-SessionPath
            if (Test-Command "npm") {
                Write-Ok "Node.js installed and ready."
            } else {
                Write-Warn "Node.js was installed, but this terminal can't see it yet."
                Write-Host "  Open a NEW terminal before running 'spin start'."
            }
        } else {
            Write-Err "winget is not available on this system."
            Write-Host "  Install Node.js manually from https://nodejs.org whenever you want the browser UI."
        }
    } else {
        Write-Host "  Skipping - install it later from https://nodejs.org if you want 'spin start'."
    }
} else {
    Write-Ok "Node.js found: $(npm --version)"
}

# ============================================================
# HAND OFF TO install.py
# ============================================================

Write-Host ""
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Info "Running the SPINDEP installer..."
Write-Host "--------------------------------------------------------------" -ForegroundColor Cyan
Write-Host ""

& $pythonCmd install.py
