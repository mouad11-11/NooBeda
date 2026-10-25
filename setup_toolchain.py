#!/usr/bin/env python3
"""
NoobEDA Toolchain Setup & Downloader
Automatically detects or downloads OSS CAD Suite (Yosys, GHDL, Icarus, GTKWave, openFPGALoader).
"""

import os
import sys
import shutil
import json
import urllib.request
import subprocess

# Ensure UTF-8 output on Windows consoles
if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
LOCAL_OSS_DIR = os.path.join(TOOLS_DIR, "oss-cad-suite")
LOCAL_BIN = os.path.join(LOCAL_OSS_DIR, "bin")

def is_toolchain_installed():
    """Checks if yosys and gtkwave are available in local tools/ or in system PATH."""
    # 1. Local tools/ check
    if os.path.isdir(LOCAL_BIN):
        yosys_exe = os.path.join(LOCAL_BIN, "yosys.exe" if sys.platform.startswith("win") else "yosys")
        if os.path.isfile(yosys_exe):
            return True, LOCAL_BIN

    # 2. Global PATH check
    if shutil.which("yosys") and (shutil.which("ghdl") or shutil.which("iverilog")):
        return True, "system PATH"

    # 3. Known standard Windows locations
    standard_locs = [
        r"C:\tools\oss-cad-suite\bin",
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "oss-cad-suite", "bin"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "oss-cad-suite", "bin"),
    ]
    for loc in standard_locs:
        if os.path.isdir(loc) and os.path.isfile(os.path.join(loc, "yosys.exe")):
            return True, loc

    return False, None

def get_latest_release_asset():
    """Queries GitHub API for the latest OSS CAD Suite Windows x64 release."""
    api_url = "https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest"
    req = urllib.request.Request(api_url, headers={"User-Agent": "NoobEDA-Setup"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "latest")
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            # Look for windows-x64 tarball (.tgz or .tar.gz)
            if "windows-x64" in name and (name.endswith(".tgz") or name.endswith(".tar.gz")):
                return tag, name, asset["browser_download_url"], asset.get("size", 0)
    raise RuntimeError("Could not find a Windows x64 archive in the latest OSS CAD Suite release.")

def download_with_progress(url, dest_path, total_size):
    """Downloads a file showing a clean terminal progress bar."""
    print(f"📥 Connecting to: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "NoobEDA-Setup"})
    downloaded = 0
    block_size = 1024 * 1024  # 1MB chunks

    with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as out_file:
        while True:
            chunk = resp.read(block_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = min(100.0, (downloaded / total_size) * 100)
                mb_down = downloaded / (1024 * 1024)
                mb_tot = total_size / (1024 * 1024)
                bars = int(percent / 2)
                bar_str = "█" * bars + "░" * (50 - bars)
                sys.stdout.write(f"\r  [{bar_str}] {percent:5.1f}% ({mb_down:6.1f} / {mb_tot:6.1f} MB)")
                sys.stdout.flush()
            else:
                mb_down = downloaded / (1024 * 1024)
                sys.stdout.write(f"\r  Downloaded: {mb_down:6.1f} MB")
                sys.stdout.flush()
    print("\n✔ Download complete!")

def extract_archive(archive_path, extract_dir):
    """Extracts .tgz archive using built-in Windows tar.exe or python tarfile."""
    os.makedirs(extract_dir, exist_ok=True)
    print(f"📦 Extracting package into {extract_dir}...")

    # Prefer built-in tar.exe on Windows 10/11 (significantly faster than Python's tarfile)
    tar_exe = shutil.which("tar")
    if tar_exe:
        cmd = [tar_exe, "-xzf", archive_path, "-C", extract_dir]
        subprocess.run(cmd, check=True)
    else:
        import tarfile
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=extract_dir)

    print("✔ Extraction complete!")

def setup(force=False):
    """Main setup routine."""
    print("=" * 60)
    print("   ⚡ NoobEDA - FPGA & EDA Toolchain Auto-Installer ⚡")
    print("=" * 60)

    installed, path = is_toolchain_installed()
    if installed and not force:
        print(f"✅ Toolchain is already installed and available:")
        print(f"   Location: {path}")
        return True

    print("\n🔍 No pre-existing OSS CAD Suite installation detected.")
    print("   NoobEDA will download and install the open-source FPGA engines:")
    print("   • Yosys (Synthesis & RTL logic)")
    print("   • GHDL (VHDL simulation)")
    print("   • Icarus Verilog (Verilog simulation)")
    print("   • GTKWave (Digital waveform viewer)")
    print("   • openFPGALoader (JTAG programming)\n")

    os.makedirs(TOOLS_DIR, exist_ok=True)

    try:
        tag, name, download_url, size = get_latest_release_asset()
        archive_path = os.path.join(TOOLS_DIR, name)

        print(f"🚀 Found Release: {tag} ({name})")
        download_with_progress(download_url, archive_path, size)

        extract_archive(archive_path, TOOLS_DIR)

        # Cleanup archive to free disk space
        if os.path.exists(archive_path):
            os.remove(archive_path)
            print("🧹 Removed temporary archive.")

        print("\n" + "=" * 60)
        print("🎉 SUCCESS! OSS CAD Suite is installed and ready at:")
        print(f"   {LOCAL_BIN}")
        print("=" * 60 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ Error during toolchain installation: {e}")
        print("Please check your internet connection or install manually from:")
        print("https://github.com/YosysHQ/oss-cad-suite-build/releases/latest\n")
        return False

if __name__ == "__main__":
    force_download = "--force" in sys.argv
    success = setup(force=force_download)
    sys.exit(0 if success else 1)
