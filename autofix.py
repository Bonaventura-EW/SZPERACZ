#!/usr/bin/env python3
"""
SZPERACZ Auto-Fix - reaktywuj scheduled workflows i napraw typowe problemy
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command(cmd, description, allow_fail=False):
    """Execute shell command"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✅ {description} - sukces")
        if result.stdout and result.stdout.strip():
            print(f"   📄 {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        if allow_fail:
            print(f"   ℹ️  {description} - pominięto (oczekiwane)")
            return True
        print(f"   ❌ {description} - błąd:")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False

def check_git_status():
    """Check if we're in a git repo"""
    try:
        subprocess.run(
            "git rev-parse --git-dir",
            shell=True,
            capture_output=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def reactivate_workflows():
    """Main fix function"""
    
    print("=" * 70)
    print("🚀 SZPERACZ Auto-Fix - Reaktywacja Workflow")
    print("=" * 70)
    print()
    
    # Check if in git repo
    if not check_git_status():
        print("❌ BŁĄD: Nie znaleziono repozytorium Git")
        print("   Uruchom ten skrypt w katalogu głównym projektu SZPERACZ")
        sys.exit(1)
    
    print("✅ Repozytorium Git znalezione")
    print()
    
    # Create keep-alive directory
    keep_alive_dir = ".github/workflows"
    keep_alive_file = os.path.join(keep_alive_dir, ".keep-alive")
    
    os.makedirs(keep_alive_dir, exist_ok=True)
    
    # Write keep-alive timestamp
    with open(keep_alive_file, "a") as f:
        f.write(f"Keep-alive: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"📝 Utworzono/zaktualizowano: {keep_alive_file}")
    print()
    
    # Git operations
    steps = [
        ("git add .github/workflows/.keep-alive", "Dodaj keep-alive file", False),
        ("git add data/", "Dodaj folder data (jeśli istnieje)", True),
        (f"git commit -m '⏰ Re-enable workflows: {datetime.now().strftime('%Y-%m-%d %H:%M')}'", "Commit zmian", True),
        ("git push", "Push do GitHub", False),
    ]
    
    for cmd, desc, allow_fail in steps:
        if not run_command(cmd, desc, allow_fail):
            if "commit" in cmd or "data" in cmd:
                print("   ℹ️  Brak zmian do commitowania - to normalne")
            else:
                print(f"   ⚠️  {desc} nie powiodło się")
    
    print()
    print("=" * 70)
    print("✅ GOTOWE!")
    print("=" * 70)
    print()
    print("📋 Co dalej:")
    print()
    print("1️⃣  Sprawdź GitHub Actions:")
    print("   https://github.com/Bonaventura-EW/SZPERACZ/actions")
    print()
    print("2️⃣  Uruchom workflow ręcznie (test):")
    print("   Actions → 'SZPERACZ OLX - Daily Scan' → 'Run workflow'")
    print()
    print("3️⃣  Następny automatyczny scan:")
    print("   Jutro o 9:00 czasu polskiego (8:00 UTC)")
    print()
    print("4️⃣  Jeśli potrzebujesz danych TERAZ:")
    print("   python scraper.py")
    print("   git add data/ && git commit -m 'Manual scan' && git push")
    print()

if __name__ == "__main__":
    reactivate_workflows()
