#!/usr/bin/env python3
"""
SZPERACZ OLX — Main Entry Point
Orchestrates scanning and reporting workflows with error handling.
"""

import sys
import os
import logging
import traceback
from datetime import datetime, timedelta
import json

# ─── Setup Logging ───────────────────────────────────────────────────────────

def setup_logging():
    """Configure logging with both file and console handlers."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"szperacz_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("szperacz-main")


# ─── Data Directory Initialization ──────────────────────────────────────────

def ensure_data_directory():
    """Create data directory and initialize empty JSON if needed."""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    json_path = os.path.join(data_dir, "dashboard_data.json")

    if not os.path.exists(json_path):
        initial_data = {
            "profiles": {},
            "scan_history": [],
            "last_scan": None,
            "metadata": {
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0.0"
            }
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)
        logging.info(f"Initialized empty dashboard data: {json_path}")

    return data_dir


# ─── API Files Generation ────────────────────────────────────────────────────

def generate_api_files(results, scan_start_time, log):
    """
    Generate docs/api/status.json and docs/api/history.json for Android app.

    status.json  — aktualny stan ostatniego skanu (polling co X minut)
    history.json — 30 ostatnich skanów; pole 'recent' = 3 najnowsze gotowe do UI
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.join(base_dir, "docs", "api")
        os.makedirs(api_dir, exist_ok=True)

        data_dir = os.path.join(base_dir, "data")
        json_path = os.path.join(data_dir, "dashboard_data.json")

        # Wczytaj dashboard_data.json — potrzebny do liczenia nowych ogłoszeń
        dash_data = {}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                dash_data = json.load(f)

        now = datetime.now()
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        today_str = now.strftime("%Y-%m-%d")
        duration = max(1, int((now - scan_start_time).total_seconds()))

        # ── Oblicz nowe ogłoszenia i zmiany cen per profil ────────────────
        profiles_status = {}
        total_new = 0
        total_price_changes = 0
        error_profiles = []

        for pk, result in results.items():
            crosscheck = result.get("crosscheck", "unknown")
            count = result.get("count", 0)

            # Błąd = jawny "error" albo 0 ogłoszeń przy niepasującym crosscheck
            is_error = (
                crosscheck == "error"
                or (count == 0 and crosscheck not in (
                    "passed", "passed_retry", "consistent", "best_of_two"
                ))
            )

            # Nowe ogłoszenia — first_seen zaczyna się od dzisiaj
            new_today = 0
            price_changes_today = 0
            profile_data = dash_data.get("profiles", {}).get(pk, {})

            for listing in profile_data.get("current_listings", []):
                fs = listing.get("first_seen", "")
                if fs.startswith(today_str):
                    new_today += 1

            # Zmiany cen dzisiaj
            for ph_entries in profile_data.get("price_history", {}).values():
                for entry in ph_entries:
                    if entry.get("date", "").startswith(today_str):
                        price_changes_today += 1

            total_new += new_today
            total_price_changes += price_changes_today

            profile_entry = {
                "label": result.get("label", pk),
                "count": count,
                "new_listings": new_today,
                "price_changes": price_changes_today,
                "crosscheck": crosscheck,
                "crosscheck_detail": result.get("crosscheck_detail", ""),
                "duration_seconds": result.get("duration_seconds", 0),
                "ok": not is_error,
            }

            if is_error:
                detail = result.get("crosscheck_detail", "Nieznany błąd")
                profile_entry["error"] = detail
                error_profiles.append(pk)

            profiles_status[pk] = profile_entry

        # ── Globalny status ────────────────────────────────────────────────
        profiles_count = len(results)
        error_count = len(error_profiles)

        if error_count == 0:
            global_status = "success"
            message = f"Skan {profiles_count} profili zakończony pomyślnie"
        elif error_count < profiles_count:
            global_status = "partial_failure"
            message = f"Skan częściowy — błędy w: {', '.join(error_profiles)}"
        else:
            global_status = "failure"
            message = "Skan nieudany — wszystkie profile zwróciły błędy"

        total_listings = sum(r.get("count", 0) for r in results.values())

        # Następny scan: jutro 07:00 UTC (= 9:00 CET zimą / lato: sprawdź)
        next_scan_utc = datetime(now.year, now.month, now.day, 7, 0, 0) + timedelta(days=1)
        if now.hour < 7:
            next_scan_utc = datetime(now.year, now.month, now.day, 7, 0, 0)
        next_scan_iso = next_scan_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        in_seconds = max(0, int((next_scan_utc - now).total_seconds()))

        # ── status.json ────────────────────────────────────────────────────
        status_json = {
            "status": global_status,
            "message": message,
            "lastScan": {
                "timestamp": now_iso,
                "duration_seconds": duration,
                "profiles_scanned": profiles_count,
                "total_listings": total_listings,
                "new_listings": total_new,
                "price_changes": total_price_changes,
                "errors": error_profiles,
            },
            "nextScan": {
                "scheduled": next_scan_iso,
                "in_seconds": in_seconds,
            },
            "profiles": profiles_status,
        }

        with open(os.path.join(api_dir, "status.json"), "w", encoding="utf-8") as f:
            json.dump(status_json, f, ensure_ascii=False, indent=2)

        # ── history.json ───────────────────────────────────────────────────
        history_path = os.path.join(api_dir, "history.json")
        existing_history = {"last_updated": now_iso, "scans": []}
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    existing_history = json.load(f)
            except Exception:
                pass

        new_scan_entry = {
            "timestamp": now_iso,
            "date": today_str,
            "status": global_status,
            "message": message,
            "duration_seconds": duration,
            "total_listings": total_listings,
            "new_listings": total_new,
            "price_changes": total_price_changes,
            "profiles_scanned": profiles_count,
            "errors": error_profiles,
            "profiles": {
                pk: {
                    "label": v["label"],
                    "count": v["count"],
                    "new_listings": v["new_listings"],
                    "price_changes": v["price_changes"],
                    "crosscheck": v["crosscheck"],
                    "ok": v["ok"],
                    "error": v.get("error"),  # None przy sukcesie
                }
                for pk, v in profiles_status.items()
            },
        }

        scans = existing_history.get("scans", [])
        scans.append(new_scan_entry)
        scans = scans[-30:]  # Max 30 wpisów

        history_json = {
            "last_updated": now_iso,
            "scans": scans,
            # Shortcut dla aplikacji — 3 najnowsze od razu, bez slice po stronie klienta
            "recent": list(reversed(scans[-3:])),
        }

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history_json, f, ensure_ascii=False, indent=2)

        log.info(
            f"API files generated — status={global_status}, "
            f"new_listings={total_new}, errors={error_profiles}"
        )
        return True

    except Exception as e:
        log.error(f"Failed to generate API files: {e}")
        log.error(traceback.format_exc())
        return False


def _write_failure_to_api(error_msg, scan_start_time, log):
    """Zapisuje status failure do plików API gdy scan crashuje całkowicie."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.join(base_dir, "docs", "api")
        os.makedirs(api_dir, exist_ok=True)

        now = datetime.now()
        now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        today_str = now.strftime("%Y-%m-%d")
        duration = max(1, int((now - scan_start_time).total_seconds()))

        status_path = os.path.join(api_dir, "status.json")
        existing = {}
        if os.path.exists(status_path):
            with open(status_path, "r", encoding="utf-8") as f:
                existing = json.load(f)

        error_status = {
            "status": "failure",
            "message": f"Błąd krytyczny skanu: {error_msg[:200]}",
            "failedAt": now_iso,
            "failureReason": error_msg[:500],
            "lastScan": {
                "timestamp": now_iso,
                "duration_seconds": duration,
                "profiles_scanned": 0,
                "total_listings": 0,
                "new_listings": 0,
                "price_changes": 0,
                "errors": ["critical_error"],
            },
            "nextScan": existing.get("nextScan", {}),
            "profiles": existing.get("profiles", {}),
        }

        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(error_status, f, ensure_ascii=False, indent=2)

        # Historia
        history_path = os.path.join(api_dir, "history.json")
        existing_history = {"last_updated": now_iso, "scans": []}
        if os.path.exists(history_path):
            with open(history_path, "r", encoding="utf-8") as f:
                existing_history = json.load(f)

        scans = existing_history.get("scans", [])
        scans.append({
            "timestamp": now_iso,
            "date": today_str,
            "status": "failure",
            "message": f"Błąd krytyczny: {error_msg[:200]}",
            "duration_seconds": duration,
            "total_listings": 0,
            "new_listings": 0,
            "price_changes": 0,
            "profiles_scanned": 0,
            "errors": ["critical_error"],
            "profiles": {},
        })
        scans = scans[-30:]

        history_json = {
            "last_updated": now_iso,
            "scans": scans,
            "recent": list(reversed(scans[-3:])),
        }
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history_json, f, ensure_ascii=False, indent=2)

        log.info("Failure status written to API files")
    except Exception as api_err:
        log.error(f"Could not write failure status to API: {api_err}")


# ─── Command Handlers ────────────────────────────────────────────────────────

def run_scan_workflow(log):
    """Execute OLX scanning workflow."""
    log.info("=" * 70)
    log.info("STARTING SCAN WORKFLOW")
    log.info("=" * 70)

    scan_start = datetime.now()

    try:
        from scraper import run_scan, PROFILES

        ensure_data_directory()
        results = run_scan()

        # Wzbogać wyniki o label
        for pk, result in results.items():
            result["label"] = PROFILES.get(pk, {}).get("label", pk)

        total_listings = sum(r["count"] for r in results.values())
        log.info(f"Scan completed: {len(results)} profiles, {total_listings} listings")

        for pk, result in results.items():
            log.info(f"  - {pk}: {result['count']} ({result.get('crosscheck', 'unknown')})")

        generate_api_files(results, scan_start, log)

        log.info("=" * 70)
        return True

    except ImportError as e:
        log.error(f"Failed to import scraper module: {e}")
        _write_failure_to_api(str(e), scan_start, log)
        return False
    except Exception as e:
        log.error(f"Scan workflow failed: {e}")
        log.error(traceback.format_exc())
        _write_failure_to_api(str(e), scan_start, log)
        return False


def run_email_workflow(log):
    """Execute email reporting workflow."""
    log.info("=" * 70)
    log.info("STARTING EMAIL WORKFLOW")
    log.info("=" * 70)

    if not os.environ.get("EMAIL_PASSWORD"):
        log.error("EMAIL_PASSWORD environment variable not set!")
        return False

    try:
        from email_report import send_report
        success = send_report()
        if success:
            log.info("Email report sent successfully")
        else:
            log.warning("Email report failed")
        log.info("=" * 70)
        return success
    except ImportError as e:
        log.error(f"Failed to import email_report module: {e}")
        return False
    except Exception as e:
        log.error(f"Email workflow failed: {e}")
        log.error(traceback.format_exc())
        return False


def show_status(log):
    """Display current system status."""
    log.info("=" * 70)
    log.info("SZPERACZ OLX — System Status")
    log.info("=" * 70)

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    json_path = os.path.join(data_dir, "dashboard_data.json")
    excel_path = os.path.join(data_dir, "szperacz_olx.xlsx")

    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            log.info(f"Last scan: {data.get('last_scan', 'Never')}")
            log.info(f"Profiles tracked: {len(data.get('profiles', {}))}")
            log.info(f"Current listings: {sum(len(p.get('current_listings', [])) for p in data.get('profiles', {}).values())}")
        except Exception as e:
            log.error(f"Error reading JSON: {e}")
    else:
        log.warning(f"Dashboard JSON not found: {json_path}")

    if os.path.exists(excel_path):
        log.info(f"Excel size: {os.path.getsize(excel_path) / (1024*1024):.2f} MB")

    log.info(f"Python: {sys.version.split()[0]}")
    log.info(f"EMAIL_PASSWORD set: {'Yes' if os.environ.get('EMAIL_PASSWORD') else 'No'}")
    log.info("=" * 70)


def show_help():
    print("""
SZPERACZ OLX — Usage

Commands:
  --scan          Run OLX scraping workflow
  --email         Send weekly email report
  --status        Show current system status
  --help          Show this help message
""")


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main():
    log = setup_logging()

    if len(sys.argv) < 2 or '--help' in sys.argv:
        show_help()
        sys.exit(0)

    command = sys.argv[1]

    try:
        if command == '--scan':
            success = run_scan_workflow(log)
            sys.exit(0 if success else 1)
        elif command == '--email':
            success = run_email_workflow(log)
            sys.exit(0 if success else 1)
        elif command == '--status':
            show_status(log)
            sys.exit(0)
        else:
            log.error(f"Unknown command: {command}")
            show_help()
            sys.exit(1)
    except KeyboardInterrupt:
        log.warning("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
