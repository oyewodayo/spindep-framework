#!/usr/bin/env python3
"""
SPINDEP — Cross-Platform Installer
====================================
Works on Windows, macOS, and Linux (including WSL).

Usage:
    python install.py
    python3 install.py

What it does:
    1. Checks Python >= 3.9
    2. Installs all dependencies
    3. Registers 'spin' as a permanent global command
    4. Configures PATH automatically for your OS and shell
    5. Works from any directory, any terminal — forever
"""

import sys
import os
import subprocess
import platform
from pathlib import Path


# ============================================================
# TERMINAL COLOURS
# Safe cross-platform detection: disabled on Windows CMD/PowerShell
# unless running in Windows Terminal or a known ANSI-capable host.
# ============================================================

def _ansi_supported() -> bool:
    """Return True only when the terminal can render ANSI escape codes."""
    if not sys.stdout.isatty():
        return False
    system = platform.system()
    if system == "Windows":
        # Windows Terminal, VS Code, or ConEmu set WT_SESSION / TERM_PROGRAM
        return bool(
            os.environ.get("WT_SESSION") or
            os.environ.get("TERM_PROGRAM") or
            os.environ.get("ANSICON") or
            os.environ.get("TERM")
        )
    return True


class C:
    _on = _ansi_supported()
    BOLD    = "\033[1m"  if _on else ""
    GREEN   = "\033[92m" if _on else ""
    BLUE    = "\033[94m" if _on else ""
    YELLOW  = "\033[93m" if _on else ""
    RED     = "\033[91m" if _on else ""
    CYAN    = "\033[96m" if _on else ""
    RESET   = "\033[0m"  if _on else ""


def ok(msg):   print(f"  {C.GREEN}[OK]{C.RESET}  {msg}")
def info(msg): print(f"  {C.BLUE}[..]{C.RESET}  {msg}")
def warn(msg): print(f"  {C.YELLOW}[!!]{C.RESET}  {msg}")
def blank():   print()

def err(msg):
    print(f"  {C.RED}[ERROR]{C.RESET}  {msg}")
    sys.exit(1)

def head(title):
    bar = "─" * 60
    print(f"\n{C.BOLD}{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{bar}{C.RESET}\n")


# ============================================================
# PLATFORM DETECTION
# ============================================================

OS       = platform.system()   # 'Windows', 'Linux', 'Darwin'
IS_WIN   = OS == "Windows"
IS_MAC   = OS == "Darwin"
IS_LINUX = OS == "Linux"
IS_WSL   = IS_LINUX and "microsoft" in platform.uname().release.lower()


def os_label() -> str:
    if IS_WSL:  return "Windows WSL (Linux)"
    if IS_WIN:  return "Windows"
    if IS_MAC:  return "macOS"
    return "Linux"


# ============================================================
# STEP 1 — CHECK PYTHON VERSION
# ============================================================

def check_python():
    info("Checking Python version...")
    major, minor, micro = sys.version_info[:3]
    version_str = f"{major}.{minor}.{micro}"
    if major < 3 or (major == 3 and minor < 9):
        err(f"Python 3.9+ required. Found: {version_str}")
    ok(f"Python {version_str}  ({os_label()})")


# ============================================================
# STEP 2 — INSTALL PACKAGE
# ============================================================

def install_package(script_dir: Path):
    info("Installing SPINDEP and dependencies...")
    blank()

    # Upgrade pip quietly
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=True,
    )

    # --user installs into the user's local bin, avoiding permission issues
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--user",
         "-e", f"{script_dir}[full]"],
        check=True,
    )
    ok("Installation complete")


# ============================================================
# STEP 3 — CONFIGURE PATH
# ============================================================

def get_user_scripts_dir() -> Path:
    """Return the directory where 'pip install --user' places scripts."""
    result = subprocess.run(
        [sys.executable, "-m", "site", "--user-base"],
        capture_output=True, text=True, check=True,
    )
    user_base = Path(result.stdout.strip())
    return user_base / "Scripts" if IS_WIN else user_base / "bin"


# ── Unix / macOS / WSL ──────────────────────────────────────

def _shell_profiles() -> list[Path]:
    """Return shell profile files that exist (or one default to create)."""
    home = Path.home()
    candidates = [
        home / ".bashrc",
        home / ".bash_profile",
        home / ".zshrc",
        home / ".profile",
    ]
    found = [p for p in candidates if p.exists()]
    return found if found else [home / ".bashrc"]


def configure_path_unix(scripts_dir: Path):
    path_line = f'export PATH="{scripts_dir}:$PATH"'
    comment   = "# Added by SPINDEP installer"

    profiles = _shell_profiles()
    updated  = []

    for profile in profiles:
        # Create if it doesn't exist yet
        if not profile.exists():
            profile.touch()

        content = profile.read_text(encoding="utf-8")
        if str(scripts_dir) not in content and ".local/bin" not in content:
            with open(profile, "a", encoding="utf-8") as fh:
                fh.write(f"\n{comment}\n{path_line}\n")
            updated.append(profile.name)

    if updated:
        ok(f"PATH configured in: {', '.join(updated)}")
    else:
        ok("PATH already configured in shell profile(s)")

    # Apply to the current Python process session as well
    os.environ["PATH"] = f"{scripts_dir}{os.pathsep}{os.environ.get('PATH', '')}"


# ── Windows ─────────────────────────────────────────────────

def configure_path_windows(scripts_dir: Path):
    """Add scripts_dir to the Windows user PATH via the registry."""
    try:
        import winreg  # noqa: PLC0415 — Windows-only
    except ImportError:
        warn("winreg not available (not running on native Windows).")
        _print_manual_path_windows(scripts_dir)
        return

    key_path = r"Environment"
    scripts_str = str(scripts_dir)

    try:
        key = winreg.OpenKey( # type: ignore
            winreg.HKEY_CURRENT_USER, # pyright: ignore[reportAttributeAccessIssue]
            key_path,
            0,
            winreg.KEY_READ | winreg.KEY_WRITE, # type: ignore
        )
        try:
            current_path, _ = winreg.QueryValueEx(key, "PATH") # type: ignore
        except FileNotFoundError:
            current_path = ""

        path_entries = [p.strip() for p in current_path.split(";") if p.strip()]

        if scripts_str not in path_entries:
            path_entries.append(scripts_str)
            new_path = ";".join(path_entries)
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path) # type: ignore
            ok(f"PATH updated in Windows registry")
            ok(f"Added: {scripts_str}")
            blank()
            warn("Open a NEW terminal window for the PATH change to take effect.")
        else:
            ok("PATH already contains the SPINDEP scripts folder")

        winreg.CloseKey(key) # type: ignore

        # Broadcast WM_SETTINGCHANGE so Explorer / new shells pick it up
        try:
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageTimeoutW( # type: ignore
                HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
                0x0002, 5000, None,
            )
        except Exception:
            pass  # Non-fatal; the registry change is already saved

        os.environ["PATH"] = f"{scripts_str}{os.pathsep}{os.environ.get('PATH', '')}"

    except PermissionError:
        warn("Could not write to registry (permission denied).")
        _print_manual_path_windows(scripts_dir)
    except Exception as exc:
        warn(f"Registry update failed: {exc}")
        _print_manual_path_windows(scripts_dir)


def _print_manual_path_windows(scripts_dir: Path):
    blank()
    print("  Add this folder to your PATH manually:")
    print(f"    {C.CYAN}{scripts_dir}{C.RESET}")
    print("  How:  Settings → System → Advanced System Settings")
    print("        → Environment Variables → User PATH → Edit → New")


# ── Dispatcher ──────────────────────────────────────────────

def configure_path(scripts_dir: Path):
    info("Configuring PATH...")
    if IS_WIN:
        configure_path_windows(scripts_dir)
    else:
        configure_path_unix(scripts_dir)


# ============================================================
# STEP 4 — VERIFY
# ============================================================

def verify(scripts_dir: Path):
    info("Verifying installation...")
    spin_exe = scripts_dir / ("spin.exe" if IS_WIN else "spin")

    if spin_exe.exists():
        ok("'spin' command installed successfully")
        blank()
        try:
            subprocess.run([str(spin_exe), "info"], check=False)
        except Exception:
            pass
    else:
        warn("'spin' executable not found at expected path.")
        blank()
        print(f"  Expected location: {spin_exe}")
        blank()
        print("  Possible causes:")
        print("  1. pip chose a different scripts directory")
        print("  2. The package did not register the entry point")
        blank()
        print(f"  Try running manually:  {C.CYAN}pip install --user -e .[full]{C.RESET}")


# ============================================================
# STEP 5 — USAGE REMINDER
# ============================================================

def print_usage():
    blank()
    print(f"{C.BOLD}{C.CYAN}Quick start:{C.RESET}")
    cmds = [
        ("spin run      --data ./datasets",            "Full analysis pipeline"),
        ("spin test     matter.csv anti.csv --plot",   "Quick CPT test with plot"),
        ("spin validate --data ./datasets",            "Pre-flight check"),
        ("spin import   --from /data --coupling gAgA --potential V2 ...", "Import data"),
        ("spin config   myrun.yaml",                   "Config file run"),
        ("spin --help",                                "All commands"),
    ]
    for cmd, desc in cmds:
        print(f"  {C.CYAN}{cmd:<55}{C.RESET}  {C.BOLD}#{C.RESET} {desc}")
    blank()

    if IS_WIN:
        ok("SPINDEP is ready!  Open a new terminal and run:  spin --help")
    else:
        ok("SPINDEP is ready!  Open a new terminal and run:  spin --help")
        blank()
        shell = os.environ.get("SHELL", "bash")
        rc = "~/.zshrc" if "zsh" in shell else "~/.bashrc"
        print(f"  {C.YELLOW}If 'spin' is not recognised in your current terminal, run:{C.RESET}")
        print(f"    {C.CYAN}source {rc}{C.RESET}")


# ============================================================
# MAIN
# ============================================================

def main():
    head("SPINDEP Installer")

    script_dir = Path(__file__).parent.resolve()
    if not (script_dir / "setup.py").exists():
        err(
            f"setup.py not found in {script_dir}.\n"
            "  Run this script from the spindep_framework folder."
        )

    info(f"Framework directory: {script_dir}")
    blank()

    check_python()
    blank()

    install_package(script_dir)
    blank()

    scripts_dir = get_user_scripts_dir()
    info(f"Scripts directory: {scripts_dir}")
    configure_path(scripts_dir)
    blank()

    verify(scripts_dir)

    print_usage()


if __name__ == "__main__":
    main()