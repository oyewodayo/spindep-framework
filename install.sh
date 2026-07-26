#!/usr/bin/env python3
"""
SPINDEP — Cross-Platform Installer
====================================
Works on Windows, macOS, and Linux (including WSL).

Usage:
    python3 install.py

What it does:
    1. Checks Python >= 3.9
    2. Installs all dependencies (pip install --user -e .)
    3. Registers 'spin' as a permanent global command in ~/.local/bin
    4. Writes PATH export to ALL detected shell profiles (.bashrc, .zshrc, etc.)
    5. Sources the profile so 'spin' works in the CURRENT terminal immediately
    6. Works from any directory, any terminal — forever
"""

import sys
import os
import subprocess
import platform
from pathlib import Path


# ============================================================
# TERMINAL COLOURS
# ============================================================

def _ansi_supported() -> bool:
    if not sys.stdout.isatty():
        return False
    system = platform.system()
    if system == "Windows":
        return bool(
            os.environ.get("WT_SESSION") or
            os.environ.get("TERM_PROGRAM") or
            os.environ.get("ANSICON") or
            os.environ.get("TERM")
        )
    return True


class C:
    _on = _ansi_supported()
    BOLD   = "\033[1m"  if _on else ""
    GREEN  = "\033[92m" if _on else ""
    BLUE   = "\033[94m" if _on else ""
    YELLOW = "\033[93m" if _on else ""
    RED    = "\033[91m" if _on else ""
    CYAN   = "\033[96m" if _on else ""
    RESET  = "\033[0m"  if _on else ""


def ok(msg):   print(f"  {C.GREEN}[OK]{C.RESET}    {msg}")
def info(msg): print(f"  {C.BLUE}[..]{C.RESET}    {msg}")
def warn(msg): print(f"  {C.YELLOW}[!!]{C.RESET}    {msg}")
def blank():   print()


def err(msg):
    print(f"  {C.RED}[ERROR]{C.RESET}  {msg}")
    sys.exit(1)


def head(title):
    bar = "─" * 62
    print(f"\n{C.BOLD}{C.CYAN}{bar}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{bar}{C.RESET}\n")


# ============================================================
# PLATFORM DETECTION
# ============================================================

OS       = platform.system()
IS_WIN   = OS == "Windows"
IS_MAC   = OS == "Darwin"
IS_LINUX = OS == "Linux"
IS_WSL   = IS_LINUX and "microsoft" in platform.uname().release.lower()


def os_label() -> str:
    if IS_WSL: return "Windows WSL (Linux)"
    if IS_WIN: return "Windows"
    if IS_MAC: return "macOS"
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

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
        check=True,
    )

    # --user avoids permission issues and always installs to ~/.local/bin
    # which is what we explicitly configure in PATH below
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--user",
         "-e", f"{script_dir}[full]"],
        check=True,
    )
    ok("Package installed")


# ============================================================
# STEP 3 — GET SCRIPTS DIR
# ============================================================

def get_user_scripts_dir() -> Path:
    """Return the directory where pip install --user places scripts."""
    result = subprocess.run(
        [sys.executable, "-m", "site", "--user-base"],
        capture_output=True, text=True, check=True,
    )
    user_base = Path(result.stdout.strip())
    return user_base / "Scripts" if IS_WIN else user_base / "bin"


# ============================================================
# STEP 4 — CONFIGURE PATH (Unix / macOS / WSL)
# ============================================================

# The exact marker we write — we search for this to detect prior installs.
_PATH_MARKER = "# >>> SPINDEP PATH >>>"
_PATH_END    = "# <<< SPINDEP PATH <<<"


def _shell_profiles() -> list[Path]:
    """Return every shell profile that currently exists."""
    home = Path.home()
    candidates = [
        home / ".bashrc",
        home / ".bash_profile",
        home / ".zshrc",
        home / ".profile",
    ]
    found = [p for p in candidates if p.exists()]
    return found if found else [home / ".bashrc"]


def _path_block(scripts_dir: Path) -> str:
    return (
        f"\n{_PATH_MARKER}\n"
        f'export PATH="{scripts_dir}:$PATH"\n'
        f"{_PATH_END}\n"
    )


def configure_path_unix(scripts_dir: Path):
    """
    Write a clearly-marked PATH block into every shell profile.

    Uses a unique marker so:
      - Re-running the installer never creates duplicate entries.
      - The check is exact (not tripped by unrelated .local/bin mentions).
    """
    profiles  = _shell_profiles()
    updated   = []
    already   = []

    for profile in profiles:
        profile.touch(exist_ok=True)
        content = profile.read_text(encoding="utf-8")

        if _PATH_MARKER in content:
            already.append(profile.name)
            continue  # already written by a previous install

        with open(profile, "a", encoding="utf-8") as fh:
            fh.write(_path_block(scripts_dir))
        updated.append(profile.name)

    if updated:
        ok(f"PATH written to:   {', '.join(updated)}")
    if already:
        ok(f"PATH already set in: {', '.join(already)}")

    # Apply immediately to the current Python process (and any subprocess)
    os.environ["PATH"] = f"{scripts_dir}{os.pathsep}{os.environ.get('PATH', '')}"


# ============================================================
# STEP 4 — CONFIGURE PATH (Windows)
# ============================================================

def configure_path_windows(scripts_dir: Path):
    try:
        import winreg
    except ImportError:
        warn("winreg unavailable — not running on native Windows.")
        _print_manual_path_windows(scripts_dir)
        return

    scripts_str = str(scripts_dir)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment",
            0, winreg.KEY_READ | winreg.KEY_WRITE,
        )
        try:
            current_path, _ = winreg.QueryValueEx(key, "PATH")
        except FileNotFoundError:
            current_path = ""

        entries = [p.strip() for p in current_path.split(";") if p.strip()]
        if scripts_str not in entries:
            entries.append(scripts_str)
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, ";".join(entries))
            ok(f"PATH updated in registry: {scripts_str}")
            warn("Open a NEW terminal for the change to take effect.")
        else:
            ok("PATH already contains SPINDEP scripts folder")
        winreg.CloseKey(key)

        try:
            import ctypes
            ctypes.windll.user32.SendMessageTimeoutW(
                0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None,
            )
        except Exception:
            pass

        os.environ["PATH"] = f"{scripts_str}{os.pathsep}{os.environ.get('PATH', '')}"

    except (PermissionError, Exception) as exc:
        warn(f"Registry update failed: {exc}")
        _print_manual_path_windows(scripts_dir)


def _print_manual_path_windows(scripts_dir: Path):
    blank()
    print("  Add this folder to PATH manually:")
    print(f"    {C.CYAN}{scripts_dir}{C.RESET}")
    print("  How: Settings → System → Advanced System Settings")
    print("       → Environment Variables → User PATH → Edit → New")


def configure_path(scripts_dir: Path):
    info("Configuring PATH...")
    if IS_WIN:
        configure_path_windows(scripts_dir)
    else:
        configure_path_unix(scripts_dir)


# ============================================================
# STEP 5 — VERIFY INSTALLATION
# ============================================================

def verify(scripts_dir: Path) -> bool:
    info("Verifying installation...")
    spin_exe = scripts_dir / ("spin.exe" if IS_WIN else "spin")

    if spin_exe.exists():
        ok(f"'spin' found at: {spin_exe}")
        return True
    else:
        warn(f"'spin' not found at expected location: {spin_exe}")
        blank()
        # Try finding it anywhere on PATH as a fallback
        found = subprocess.run(
            ["which", "spin"], capture_output=True, text=True
        ).stdout.strip()
        if found:
            ok(f"'spin' found via PATH at: {found}")
            return True
        return False


# ============================================================
# STEP 6 — SOURCE PROFILE IN CURRENT SHELL SESSION
# Writes a small helper script the user can eval to activate
# the PATH in their current terminal without reopening it.
# ============================================================

def write_activate_hint(scripts_dir: Path):
    """
    We can't directly modify the parent shell's environment from Python,
    but we can:
      1. Print the exact one-liner the user needs (minimal friction).
      2. Write a tiny activate.sh they can source.
      3. Export PATH for any subprocess we spawn (already done above).
    """
    activate = Path(__file__).parent / "activate_spin.sh"
    activate.write_text(
        "#!/usr/bin/env bash\n"
        f'export PATH="{scripts_dir}:$PATH"\n'
        'echo "  [OK]  spin is now available in this terminal."\n',
        encoding="utf-8",
    )
    activate.chmod(0o755)

    blank()
    print(f"{C.BOLD}{C.CYAN}{'─'*62}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  One more step — activate in THIS terminal:{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'─'*62}{C.RESET}")
    blank()
    print(f"  {C.YELLOW}Run ONE of these:{C.RESET}")
    blank()

    shell = os.environ.get("SHELL", "")
    rc    = "~/.zshrc" if "zsh" in shell else "~/.bashrc"

    print(f"  {C.CYAN}source {rc}{C.RESET}              "
          f"  {C.BOLD}# reload your shell profile{C.RESET}")
    print(f"  {C.CYAN}source ./activate_spin.sh{C.RESET}      "
          f"  {C.BOLD}# quick one-shot activate{C.RESET}")
    print(f"  {C.CYAN}export PATH=\"{scripts_dir}:$PATH\"{C.RESET}  "
          f"  {C.BOLD}# inline (paste directly){C.RESET}")
    blank()
    print(f"  After that: {C.GREEN}spin --help{C.RESET}")
    blank()
    print(f"  {C.YELLOW}All new terminals will have 'spin' automatically.{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'─'*62}{C.RESET}")


# ============================================================
# STEP 7 — USAGE REMINDER
# ============================================================

def print_usage():
    blank()
    print(f"{C.BOLD}{C.CYAN}Quick start:{C.RESET}")
    cmds = [
        ("spin start",                                             "Launch the web interface (recommended)"),
        ("spin run      --data ./datasets",                       "Full analysis pipeline"),
        ("spin test     matter.csv anti.csv --plot",              "Quick CPT test with plot"),
        ("spin validate --data ./datasets",                       "Pre-flight check"),
        ("spin import   --from /data --coupling gAgA --potential V2 ...", "Import data"),
        ("spin config   myrun.yaml",                              "Config-file run"),
        ("spin batch    jobs.yaml",                               "Run multiple jobs"),
        ("spin info     --data ./datasets",                       "Framework status"),
        ("spin --help",                                           "All commands"),
    ]
    for cmd, desc in cmds:
        print(f"  {C.CYAN}{cmd:<58}{C.RESET}  {C.BOLD}#{C.RESET} {desc}")
    blank()


# ============================================================
# MAIN
# ============================================================

def main():
    head("SPINDEP Installer")

    repo_dir = Path(__file__).parent.resolve()
    script_dir = repo_dir / "spindep_cli"
    if not (script_dir / "setup.py").exists():
        err(
            f"setup.py not found in {script_dir}.\n"
            "  Run this script from the spindep_framework folder."
        )

    info(f"Framework directory: {repo_dir}")
    blank()

    check_python()
    blank()

    install_package(script_dir)
    blank()

    scripts_dir = get_user_scripts_dir()
    info(f"Scripts directory:   {scripts_dir}")
    configure_path(scripts_dir)
    blank()

    found = verify(scripts_dir)
    blank()

    if found:
        ok("Installation complete!")
        print_usage()
    else:
        warn("Installation finished but 'spin' was not found.")
        blank()
        print(f"  Expected: {scripts_dir / 'spin'}")
        blank()
        print("  Possible causes:")
        print("  1. pip used a different scripts directory")
        print("  2. The entry point in setup.py doesn't match the package")
        blank()
        print(f"  Debug: {C.CYAN}pip show -f spindep | grep spin{C.RESET}")
        print(f"  Debug: {C.CYAN}python3 -c \"from spindep.cli import main; print('OK')\"{C.RESET}")

    write_activate_hint(scripts_dir)


if __name__ == "__main__":
    main()