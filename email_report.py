#!/usr/bin/env python3
"""
SZPERACZ OLX — Weekly email report.
Sends rich HTML summary + Excel attachment every Monday.
"""

import smtplib
import json
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("szperacz-email")

SENDER_EMAIL = "slowholidays00@gmail.com"
RECEIVER_EMAIL = "malczarski@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")
EXCEL_PATH = os.path.join(DATA_DIR, "szperacz_olx.xlsx")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

PROFILE_ORDER = [
    "wszystkie_pokoje", "mzuri", "poqui", "dawny_patron",
    "pokojewlublinie", "artymiuk", "villahome",
]


def price_distribution(listings):
    buckets = {"<600": 0, "600-800": 0, "800-1000": 0, "1000-1500": 0, "1500-2000": 0, ">2000": 0}
    for l in listings:
        p = l.get("price")
        if not p or p <= 0:
            continue
        if p < 600:
            buckets["<600"] += 1
        elif p < 800:
            buckets["600-800"] += 1
        elif p < 1000:
            buckets["800-1000"] += 1
        elif p < 1500:
            buckets["1000-1500"] += 1
        elif p < 2000:
            buckets["1500-2000"] += 1
        else:
            buckets[">2000"] += 1
    return buckets


def bar_chart_html(buckets, max_height=70):
    items = list(buckets.items())
    max_val = max((v for _, v in items), default=1) or 1
    tds = ""
    for label, val in items:
        h = max(int((val / max_val) * max_height), 2)
        tds += (
            f'<td style="text-align:center;vertical-align:bottom;padding:0 3px;width:{100//len(items)}%">'
            f'<div style="font-size:10px;color:#6b7280;margin-bottom:2px;">{val}</div>'
            f'<div style="background:#2563EB;height:{h}px;border-radius:2px 2px 0 0;min-width:18px;"></div>'
            f'<div style="font-size:9px;color:#9ca3af;margin-top:3px;white-space:nowrap;">{label}</div>'
            f'</td>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<tr style="vertical-align:bottom;height:{max_height+28}px;">{tds}</tr>'
        f'</table>'
    )


def sparkline_html(values, width=200, height=40):
    if len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = round(i / (n - 1) * width)
        y = round((1 - (v - mn) / rng) * (height - 6)) + 3
        pts.append(f"{x},{y}")
    poly = " ".join(pts)
    lx, ly = pts[-1].split(",")
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        f'<polyline points="{poly}" fill="none" stroke="#2563EB" stroke-width="2" stroke-linejoin="round"/>'
        f'<circle cx="{lx}" cy="{ly}" r="3" fill="#2563EB"/>'
        f'</svg>'
    )


def change_badge(ch):
    if ch > 0:
        return f'<span style="background:#dcfce7;color:#166534;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">+{ch} &#8593;</span>'
    elif ch < 0:
        return f'<span style="background:#fee2e2;color:#991b1b;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">{ch} &#8595;</span>'
    return '<span style="background:#f3f4f6;color:#6b7280;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">0</span>'


def build_report_html():
    if not os.path.exists(JSON_PATH):
        return "<p>Brak danych — plik JSON nie istnieje.</p>"

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now()
    week_ago = today - timedelta(days=7)
    week_ago_str = week_ago.strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    last_scan = data.get("last_scan", "Brak danych")
    profiles = data.get("profiles", {})

    # Market-level stats
    market = profiles.get("wszystkie_pokoje", {})
    market_listings = market.get("current_listings", [])
    market_dc = market.get("daily_counts", [])
    market_week = [d for d in market_dc if d["date"] >= week_ago_str]
    market_current = market_week[-1]["count"] if market_week else 0
    market_first = market_week[0]["count"] if market_week else market_current
    market_change = market_current - market_first

    prices_all = [l["price"] for l in market_listings if l.get("price") and l["price"] > 0]
    avg_price = int(sum(prices_all) / len(prices_all)) if prices_all else 0
    min_price = min(prices_all) if prices_all else 0
    max_price = max(prices_all) if prices_all else 0

    price_changes_down = sorted(
        [l for l in market_listings if (l.get("price_change") or 0) < 0],
        key=lambda x: x.get("price_change", 0),
    )
    price_changes_up = [l for l in market_listings if (l.get("price_change") or 0) > 0]
    promoted_count = sum(1 for l in market_listings if l.get("is_promoted"))
    new_today = [l for l in market_listings if (l.get("first_seen") or "").startswith(today_str)]

    market_counts_week = [d["count"] for d in market_week]
    sparkline = sparkline_html(market_counts_week)
    dist = price_distribution(market_listings)
    bar_chart = bar_chart_html(dist)

    market_change_color = "#166534" if market_change > 0 else ("#991b1b" if market_change < 0 else "#6b7280")
    market_change_str = (f"+{market_change}" if market_change > 0 else str(market_change))

    # Profile rows
    profile_rows = ""
    for pk in PROFILE_ORDER:
        if pk not in profiles:
            continue
        pd = profiles[pk]
        label = pd.get("label", pk)
        is_cat = pd.get("is_category", False)
        dc = pd.get("daily_counts", [])
        week = [d for d in dc if d["date"] >= week_ago_str]
        cur = week[-1]["count"] if week else 0
        first_w = week[0]["count"] if week else cur
        ch = cur - first_w
        vals = [d["count"] for d in week]
        cls2 = pd.get("current_listings", [])
        pr = [l["price"] for l in cls2 if l.get("price") and l["price"] > 0]
        avg = int(sum(pr) / len(pr)) if pr else 0
        sp = sparkline_html(vals, width=90, height=28) if len(vals) >= 2 else ""
        row_bg = "#eff6ff" if is_cat else "#ffffff"
        icon = "&#127760; " if is_cat else ""
        mini = min(vals) if vals else 0
        maxi = max(vals) if vals else 0
        profile_rows += (
            f'<tr style="border-bottom:1px solid #e5e7eb;background:{row_bg};">'
            f'<td style="padding:10px 12px;font-weight:{"700" if is_cat else "400"};font-size:13px;">{icon}{label}</td>'
            f'<td style="padding:10px 12px;text-align:center;font-size:{"15" if is_cat else "13"}px;font-weight:700;">{cur}</td>'
            f'<td style="padding:10px 12px;text-align:center;">{change_badge(ch)}</td>'
            f'<td style="padding:10px 12px;text-align:center;font-size:12px;color:#6b7280;">{mini}–{maxi}</td>'
            f'<td style="padding:10px 12px;text-align:center;font-size:13px;">{avg} zł</td>'
            f'<td style="padding:10px 4px;text-align:center;">{sp}</td>'
            f'</tr>'
        )

    # Price drops
    drop_rows = ""
    for l in price_changes_down[:10]:
        ch_val = l.get("price_change", 0)
        prev = l.get("previous_price")
        cur_p = l.get("price")
        title = (l.get("title") or "—")[:52]
        url = l.get("url", "#")
        pct = f"{round(ch_val/prev*100)}%" if prev and prev > 0 else ""
        drop_rows += (
            f'<tr style="border-bottom:1px solid #f3f4f6;">'
            f'<td style="padding:8px 12px;font-size:13px;"><a href="{url}" style="color:#1d4ed8;text-decoration:none;">{title}</a></td>'
            f'<td style="padding:8px 12px;text-align:center;font-size:13px;color:#6b7280;text-decoration:line-through;">{prev} z&#322;</td>'
            f'<td style="padding:8px 12px;text-align:center;font-size:13px;font-weight:600;">{cur_p} z&#322;</td>'
            f'<td style="padding:8px 12px;text-align:center;font-size:13px;color:#166534;font-weight:700;">{ch_val} z&#322;</td>'
            f'<td style="padding:8px 12px;text-align:center;font-size:12px;color:#6b7280;">{pct}</td>'
            f'</tr>'
        )
    if not drop_rows:
        drop_rows = '<tr><td colspan="5" style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Brak zmian cen w tym tygodniu</td></tr>'

    # New listings
    new_rows = ""
    for l in sorted(new_today, key=lambda x: -(x.get("price") or 0))[:10]:
        title = (l.get("title") or "—")[:52]
        url = l.get("url", "#")
        price = f"{l['price']} z&#322;" if l.get("price") else "—"
        pub = l.get("published") or l.get("date_text") or "—"
        promo = "&#11088; " if l.get("is_promoted") else ""
        new_rows += (
            f'<tr style="border-bottom:1px solid #f3f4f6;">'
            f'<td style="padding:8px 12px;font-size:13px;">{promo}<a href="{url}" style="color:#1d4ed8;text-decoration:none;">{title}</a></td>'
            f'<td style="padding:8px 12px;text-align:center;font-size:13px;font-weight:600;">{price}</td>'
            f'<td style="padding:8px 12px;text-align:center;font-size:12px;color:#6b7280;">{pub}</td>'
            f'</tr>'
        )
    if not new_rows:
        new_rows = '<tr><td colspan="3" style="padding:16px;text-align:center;color:#9ca3af;font-size:13px;">Brak nowych og&#322;osze&#324; dzisiaj</td></tr>'

    section_header = lambda icon, title: (
        f'<div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:10px;'
        f'text-transform:uppercase;letter-spacing:0.06em;padding-bottom:6px;'
        f'border-bottom:2px solid #e5e7eb;">{icon} {title}</div>'
    )

    th = lambda text: f'<th style="padding:9px 12px;text-align:left;font-weight:600;font-size:12px;color:#374151;background:#f1f5f9;">{text}</th>'
    th_c = lambda text: f'<th style="padding:9px 12px;text-align:center;font-weight:600;font-size:12px;color:#374151;background:#f1f5f9;">{text}</th>'

    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;color:#111827;">
<div style="max-width:660px;margin:24px auto;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.09);">

  <div style="background:#1e3a5f;padding:26px 32px;">
    <div style="font-size:10px;letter-spacing:0.14em;color:#93c5fd;text-transform:uppercase;margin-bottom:5px;">SZPERACZ OLX</div>
    <div style="font-size:24px;font-weight:700;color:#ffffff;margin-bottom:4px;">Raport tygodniowy</div>
    <div style="font-size:13px;color:#93c5fd;">{week_ago.strftime('%d.%m.%Y')} &#8211; {today.strftime('%d.%m.%Y')} &nbsp;&#183;&nbsp; Lublin</div>
    <div style="font-size:11px;color:#60a5fa;margin-top:5px;">Ostatni scan: {last_scan}</div>
  </div>

  <table style="width:100%;border-collapse:collapse;background:#f8fafc;border-bottom:1px solid #e5e7eb;">
    <tr>
      <td style="padding:16px 20px;text-align:center;border-right:1px solid #e5e7eb;">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;">Og&#322;osze&#324; rynek</div>
        <div style="font-size:26px;font-weight:700;">{market_current}</div>
        <div style="font-size:12px;font-weight:600;color:{market_change_color};">{market_change_str} vs tydzie&#324;</div>
      </td>
      <td style="padding:16px 20px;text-align:center;border-right:1px solid #e5e7eb;">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;">&#346;r. cena</div>
        <div style="font-size:26px;font-weight:700;">{avg_price} z&#322;</div>
        <div style="font-size:12px;color:#6b7280;">{min_price}&#8211;{max_price} z&#322;</div>
      </td>
      <td style="padding:16px 20px;text-align:center;border-right:1px solid #e5e7eb;">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;">Spadki cen</div>
        <div style="font-size:26px;font-weight:700;color:#166534;">{len(price_changes_down)}</div>
        <div style="font-size:12px;color:#6b7280;">wzrosty: {len(price_changes_up)}</div>
      </td>
      <td style="padding:16px 20px;text-align:center;">
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:3px;">Promowane</div>
        <div style="font-size:26px;font-weight:700;">{promoted_count}</div>
        <div style="font-size:12px;color:#6b7280;">nowe dzi&#347;: {len(new_today)}</div>
      </td>
    </tr>
  </table>

  <div style="padding:22px 32px;">

    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
      <tr>
        <td style="width:50%;padding-right:10px;vertical-align:top;">
          <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:14px;">
            <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">Trend 7 dni — rynek</div>
            {sparkline}
            <div style="display:flex;justify-content:space-between;font-size:10px;color:#9ca3af;margin-top:3px;">
              <span>{week_ago.strftime('%d.%m')}</span><span>{today.strftime('%d.%m')}</span>
            </div>
          </div>
        </td>
        <td style="width:50%;padding-left:10px;vertical-align:top;">
          <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:8px;padding:14px;">
            <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Rozk&#322;ad cen (z&#322;)</div>
            {bar_chart}
          </div>
        </td>
      </tr>
    </table>

    <div style="margin-bottom:22px;">
      {section_header("&#128202;", "Podsumowanie profili")}
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr>{th("Profil")}{th_c("Aktywne")}{th_c("Zmiana (7d)")}{th_c("Min&#8211;Max")}{th_c("&#346;r. cena")}{th_c("Trend")}</tr></thead>
        <tbody>{profile_rows}</tbody>
      </table>
    </div>

    <div style="margin-bottom:22px;">
      {section_header("&#128201;", f"Najwi&#281;ksze spadki cen — top {min(10,len(price_changes_down))}")}
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr>{th("Og&#322;oszenie")}{th_c("Poprzednio")}{th_c("Teraz")}{th_c("Zmiana")}{th_c("%")}</tr></thead>
        <tbody>{drop_rows}</tbody>
      </table>
    </div>

    <div style="margin-bottom:8px;">
      {section_header("&#127379;", f"Nowe og&#322;oszenia dzi&#347; ({len(new_today)})")}
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead><tr>{th("Og&#322;oszenie")}{th_c("Cena")}{th_c("Data publ.")}</tr></thead>
        <tbody>{new_rows}</tbody>
      </table>
    </div>

  </div>

  <div style="background:#f8fafc;border-top:1px solid #e5e7eb;padding:14px 32px;text-align:center;">
    <div style="font-size:12px;color:#6b7280;">Wygenerowano automatycznie przez <strong>SZPERACZ OLX</strong> &#183; {today.strftime('%d.%m.%Y %H:%M')}</div>
    <div style="font-size:11px;color:#9ca3af;margin-top:3px;">W za&#322;&#261;czniku plik Excel z pe&#322;nymi danymi.</div>
  </div>

</div>
</body>
</html>"""


def send_report():
    if not EMAIL_PASSWORD:
        log.error("EMAIL_PASSWORD not set!")
        return False

    today = datetime.now()
    subject = f"&#128269; SZPERACZ OLX — Raport tygodniowy ({today.strftime('%d.%m.%Y')})"

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(build_report_html(), "html", "utf-8"))

    if os.path.exists(EXCEL_PATH):
        try:
            with open(EXCEL_PATH, "rb") as f:
                part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="szperacz_olx_{today.strftime("%Y%m%d")}.xlsx"',
                )
                msg.attach(part)
            log.info("Excel attached.")
        except Exception as e:
            log.warning(f"Could not attach Excel: {e}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        log.info(f"Email sent to {RECEIVER_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError:
        log.error("SMTP auth failed. Check EMAIL_PASSWORD (App Password required).")
        return False
    except Exception as e:
        log.error(f"Email failed: {e}")
        return False


def save_preview():
    """Save HTML to data/email_preview.html for local inspection."""
    html = build_report_html()
    out = os.path.join(DATA_DIR, "email_preview.html")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    log.info(f"Preview saved: {out}")
    return out


if __name__ == "__main__":
    import sys
    if "--preview" in sys.argv:
        save_preview()
    else:
        send_report()
