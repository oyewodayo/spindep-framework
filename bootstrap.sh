#!/usr/bin/env bash
# SPINDEP - macOS / Linux bootstrap
# ===================================
# Run this FIRST, right after cloning, before install.py:
#
#   chmod +x bootstrap.sh && ./bootstrap.sh
#
# Why this exists: install.py is a Python script, so it can't run at all on
# a machine that has no Python - there's nothing to interpret it. This
# script checks for Python and Node.js first using nothing but the shell,
# offers to install whichever is missing via the OS package manager, and
# then hands off to install.py.
#
# Node.js is only needed for 'spin start' (the browser-based web GUI) -
# every other 'spin' command works without it, so declining that install is
# fine if you only plan to use the command line.

set -u

ok()   { echo "  [OK]    $1"; }
info() { echo "  [..]    $1"; }
warn() { echo "  [!!]    $1"; }
err()  { echo "  [ERROR] $1"; }

confirm() {
    if [ ! -t 0 ]; then
        return 1
    fi
    read -r -p "  $1 [Y/n]: " reply
    case "$reply" in
        "" | y | Y | yes | YES | Yes) return 0 ;;
        *) return 1 ;;
    esac
}

OS="$(uname -s)"
IS_MAC=false
IS_LINUX=false
case "$OS" in
    Darwin) IS_MAC=true ;;
    Linux)  IS_LINUX=true ;;
esac

echo ""
echo "--------------------------------------------------------------"
echo "  SPINDEP Setup - checking prerequisites"
echo "--------------------------------------------------------------"
echo ""

# ============================================================
# PYTHON
# ============================================================

PYTHON_CMD=""
for candidate in python3 python; do
    if ! command -v "$candidate" >/dev/null 2>&1; then
        continue
    fi
    ver="$("$candidate" --version 2>&1)"
    maj="$(echo "$ver" | grep -oE '[0-9]+\.[0-9]+' | head -1 | cut -d. -f1)"
    min="$(echo "$ver" | grep -oE '[0-9]+\.[0-9]+' | head -1 | cut -d. -f2)"
    if [ -n "$maj" ] && { [ "$maj" -gt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -ge 9 ]; }; }; then
        PYTHON_CMD="$candidate"
        ok "Python found: $candidate ($ver)"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    warn "Python 3.9+ was not found on this system."
    echo "  SPINDEP is a Python tool - it can't run without it."
    echo ""
    if confirm "Install Python automatically now?"; then
        if $IS_MAC && command -v brew >/dev/null 2>&1; then
            info "Installing Python (brew install python3)..."
            brew install python3
        elif $IS_LINUX && command -v apt-get >/dev/null 2>&1; then
            info "Installing Python (apt-get install python3 python3-pip)..."
            sudo apt-get update && sudo apt-get install -y python3 python3-pip
        elif $IS_LINUX && command -v dnf >/dev/null 2>&1; then
            info "Installing Python (dnf install python3 python3-pip)..."
            sudo dnf install -y python3 python3-pip
        elif $IS_LINUX && command -v pacman >/dev/null 2>&1; then
            info "Installing Python (pacman -S python python-pip)..."
            sudo pacman -S --noconfirm python python-pip
        else
            err "No supported package manager found (need brew, apt-get, dnf, or pacman)."
        fi

        for candidate in python3 python; do
            if command -v "$candidate" >/dev/null 2>&1; then
                PYTHON_CMD="$candidate"
                break
            fi
        done
    fi

    if [ -z "$PYTHON_CMD" ]; then
        echo ""
        err "Could not set up Python automatically."
        echo "  Install it manually from https://www.python.org/downloads/"
        echo "  then re-run: ./bootstrap.sh"
        exit 1
    fi
    ok "Python installed and ready: $PYTHON_CMD"
fi

# ============================================================
# NODE.JS  (only needed for 'spin start', the browser GUI)
# ============================================================

echo ""
if ! command -v npm >/dev/null 2>&1; then
    warn "Node.js was not found."
    echo "  It's only needed so you can VIEW SPINDEP in your browser ('spin start')."
    echo "  Every other command (spin run, spin test, spin validate, ...) works without it."
    echo ""
    if confirm "Install Node.js automatically now?"; then
        if $IS_MAC && command -v brew >/dev/null 2>&1; then
            info "Installing Node.js (brew install node)..."
            brew install node
        elif $IS_LINUX && command -v apt-get >/dev/null 2>&1; then
            info "Installing Node.js (apt-get install nodejs npm)..."
            sudo apt-get update && sudo apt-get install -y nodejs npm
        elif $IS_LINUX && command -v dnf >/dev/null 2>&1; then
            info "Installing Node.js (dnf install nodejs npm)..."
            sudo dnf install -y nodejs npm
        elif $IS_LINUX && command -v pacman >/dev/null 2>&1; then
            info "Installing Node.js (pacman -S nodejs npm)..."
            sudo pacman -S --noconfirm nodejs npm
        else
            err "No supported package manager found (need brew, apt-get, dnf, or pacman)."
            echo "  Install Node.js manually from https://nodejs.org whenever you want the browser UI."
        fi

        if command -v npm >/dev/null 2>&1; then
            ok "Node.js installed and ready."
        else
            warn "Node.js install didn't complete - 'spin start' won't work until it's fixed."
        fi
    else
        echo "  Skipping - install it later from https://nodejs.org if you want 'spin start'."
    fi
else
    ok "Node.js found: $(npm --version)"
fi

# ============================================================
# HAND OFF TO install.py
# ============================================================

echo ""
echo "--------------------------------------------------------------"
info "Running the SPINDEP installer..."
echo "--------------------------------------------------------------"
echo ""

exec "$PYTHON_CMD" install.py
