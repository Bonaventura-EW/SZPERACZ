#!/usr/bin/env python3
"""
SZPERACZ OLX — Main Entry Point
Orchestrates scanning and reporting workflows with error handling.
"""

import sys
import os
import logging
import traceback
from datetime import datetime
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
    
    # Initialize empty JSON structure if file doesn't exist
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


# ─── Command Handlers ────────────────────────────────────────────────────────

def run_scan_workflow(log):
    """Execute OLX scanning workflow."""
    log.info("="*70)
    log.info("STARTING SCAN WORKFLOW")
    log.info("="*70)
    
    try:
        from scraper import run_scan
        
        # Ensure data directory exists
        ensure_data_directory()
        
        # Run the scan
        results = run_scan()
        
        # Log statistics
        total_listings = sum(r['count'] for r in results.values())
        log.info(f"Scan completed successfully:")
        log.info(f"  - Profiles scanned: {len(results)}")
        log.info(f"  - Total listings: {total_listings}")
        
        for profile_key, result in results.items():
            status = result.get('crosscheck', 'unknown')
            log.info(f"  - {profile_key}: {result['count']} listings ({status})")
        
        log.info("="*70)
        return True
        
    except ImportError as e:
        log.error(f"Failed to import scraper module: {e}")
        log.error("Make sure scraper.py is in the same directory")
        return False
    except Exception as e:
        log.error(f"Scan workflow failed: {e}")
        log.error(traceback.format_exc())
        return False


def run_email_workflow(log):
    """Execute email reporting workflow."""
    log.info("="*70)
    log.info("STARTING EMAIL WORKFLOW")
    log.info("="*70)
    
    # Check for EMAIL_PASSWORD
    if not os.environ.get("EMAIL_PASSWORD"):
        log.error("EMAIL_PASSWORD environment variable not set!")
        log.error("Set it in GitHub Secrets or export it locally")
        return False
    
    try:
        from email_report import send_report
        
        success = send_report()
        
        if success:
            log.info("Email report sent successfully")
        else:
            log.warning("Email report failed (check logs above)")
        
        log.info("="*70)
        return success
        
    except ImportError as e:
        log.error(f"Failed to import email_report module: {e}")
        log.error("Make sure email_report.py is in the same directory")
        return False
    except Exception as e:
        log.error(f"Email workflow failed: {e}")
        log.error(traceback.format_exc())
        return False


def show_status(log):
    """Display current system status."""
    log.info("="*70)
    log.info("SZPERACZ OLX — System Status")
    log.info("="*70)
    
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    json_path = os.path.join(data_dir, "dashboard_data.json")
    excel_path = os.path.join(data_dir, "szperacz_olx.xlsx")
    
    # Check data files
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            last_scan = data.get('last_scan', 'Never')
            profile_count = len(data.get('profiles', {}))
            total_listings = sum(
                len(p.get('current_listings', [])) 
                for p in data.get('profiles', {}).values()
            )
            
            log.info(f"Dashboard Data:")
            log.info(f"  - Last scan: {last_scan}")
            log.info(f"  - Profiles tracked: {profile_count}")
            log.info(f"  - Current listings: {total_listings}")
        except Exception as e:
            log.error(f"  - Error reading JSON: {e}")
    else:
        log.warning(f"  - Dashboard JSON not found: {json_path}")
    
    if os.path.exists(excel_path):
        size_mb = os.path.getsize(excel_path) / (1024 * 1024)
        log.info(f"Excel Report:")
        log.info(f"  - Size: {size_mb:.2f} MB")
        log.info(f"  - Path: {excel_path}")
    else:
        log.warning(f"  - Excel file not found: {excel_path}")
    
    # Check environment
    log.info(f"Environment:")
    log.info(f"  - Python: {sys.version.split()[0]}")
    log.info(f"  - EMAIL_PASSWORD set: {'Yes' if os.environ.get('EMAIL_PASSWORD') else 'No'}")
    
    log.info("="*70)


def show_help():
    """Display usage information."""
    help_text = """
SZPERACZ OLX — Usage

Commands:
  --scan          Run OLX scraping workflow
  --email         Send weekly email report
  --status        Show current system status
  --help          Show this help message

Examples:
  python main.py --scan                 # Run daily scan
  python main.py --email                # Send email report
  python main.py --status               # Check system status

Environment Variables:
  EMAIL_PASSWORD    Gmail App Password (required for --email)

GitHub Actions:
  The workflows in .github/workflows/ run these commands automatically:
  - scan.yml: Runs --scan daily at 9:00 CET
  - weekly_report.yml: Runs --email every Monday at 9:30 CET
"""
    print(help_text)


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main():
    """Main entry point with command-line argument parsing."""
    log = setup_logging()
    
    # Parse arguments
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
