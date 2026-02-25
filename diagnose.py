#!/usr/bin/env python3
"""
SZPERACZ Diagnostics - sprawdź status workflow i zidentyfikuj problemy
"""

import sys
import json
from datetime import datetime, timedelta

def check_workflow_status():
    """Wyświetl instrukcje diagnostyczne"""
    
    print("=" * 70)
    print("🔍 SZPERACZ - Diagnostyka Workflow")
    print("=" * 70)
    print()
    
    print("📋 CHECKLIST - Co sprawdzić w GitHub:")
    print()
    
    print("1️⃣  SPRAWDŹ STATUS WORKFLOW:")
    print("   Idź do: https://github.com/Bonaventura-EW/SZPERACZ/actions")
    print("   ❓ Co widzisz?")
    print("      ✅ Zielone checkmarki - workflow działa")
    print("      ❌ Czerwone X - są błędy (kliknij i sprawdź logi)")
    print("      ⚠️  Żółty status - workflow w toku")
    print("      🔇 Brak wykonań - workflow wyłączony lub nie trigger'owany")
    print()
    
    print("2️⃣  SPRAWDŹ CZY WORKFLOW JEST ENABLED:")
    print("   Idź do: https://github.com/Bonaventura-EW/SZPERACZ/actions/workflows/scan.yml")
    print("   ❓ Czy widzisz przycisk 'Enable workflow'?")
    print("      → Jeśli TAK - kliknij go!")
    print("      → Jeśli NIE - workflow jest aktywny")
    print()
    
    print("3️⃣  TIMEZONE CRON:")
    print("   Obecny czas:")
    now = datetime.now()
    print(f"   🕐 UTC:    {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # CET = UTC+1, CEST = UTC+2
    cet_time = now + timedelta(hours=1)
    cest_time = now + timedelta(hours=2)
    
    print(f"   🕐 CET:    {cet_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+1, zima)")
    print(f"   🕐 CEST:   {cest_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC+2, lato)")
    print()
    print("   📌 Twój cron: '0 8 * * *' (8:00 UTC)")
    print(f"      → Zimą (CET):  wykonuje się o {cet_time.replace(hour=9, minute=0).strftime('%H:%M')} PL")
    print(f"      → Latem (CEST): wykonuje się o {cest_time.replace(hour=10, minute=0).strftime('%H:%M')} PL")
    print()
    
    print("4️⃣  MANUAL TRIGGER TEST:")
    print("   Idź do: https://github.com/Bonaventura-EW/SZPERACZ/actions/workflows/scan.yml")
    print("   1. Kliknij 'Run workflow' (prawy górny róg)")
    print("   2. Wybierz branch 'main'")
    print("   3. Kliknij zielony 'Run workflow'")
    print("   4. Odśwież stronę po 10 sekundach")
    print("   ❓ Czy workflow się uruchomił?")
    print()
    
    print("5️⃣  REPO ACTIVITY (GitHub wyłącza crony po 60 dniach):")
    print("   Jeśli repo nieaktywne >60 dni, scheduled workflows są wyłączane")
    print("   💊 FIX: Zrób pusty commit")
    print("      git commit --allow-empty -m 'Re-enable scheduled workflows'")
    print("      git push")
    print()
    
    print("=" * 70)
    print("🔧 SZYBKA NAPRAWA:")
    print("=" * 70)
    print()
    print("Jeśli workflow NIE działa automatycznie:")
    print()
    print("OPCJA A - Uruchom ręcznie przez Dashboard:")
    print("  1. Otwórz: https://bonaventura-ew.github.io/SZPERACZ/")
    print("  2. Kliknij 'Scan teraz'")
    print("  3. Wklej GitHub token (Settings → Developer → Personal tokens)")
    print()
    print("OPCJA B - Uruchom przez GitHub Actions UI:")
    print("  1. Idź do Actions tab")
    print("  2. Wybierz 'SZPERACZ OLX - Daily Scan'")
    print("  3. Kliknij 'Run workflow'")
    print()
    print("OPCJA C - Uruchom lokalnie:")
    print("  python scraper.py")
    print("  git add data/")
    print("  git commit -m 'Manual scan'")
    print("  git push")
    print()
    print("=" * 70)
    print()
    print("🆘 Potrzebujesz pomocy?")
    print("   Zobacz: TROUBLESHOOTING.md")
    print()

if __name__ == "__main__":
    check_workflow_status()
