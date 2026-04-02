#!/usr/bin/env python3
"""
SZPERACZ OLX — Weekly email report with analytics.
Sends HTML report with embedded charts + Excel attachment every Monday.
"""

import smtplib
import json
import os
import logging
import base64
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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


# ─── Chart Generator ────────────────────────────────────────────────────────

def generate_trend_chart(profile_data, profile_label, days=7):
    """
    Generate a 7-day trend chart as Base64 PNG.
    Returns: Base64 string or None if no data.
    """
    dc = profile_data.get("daily_counts", [])
    if not dc:
        return None
    
    # Get last N days
    recent = dc[-days:] if len(dc) >= days else dc
    if not recent:
        return None
    
    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in recent]
    counts = [d["count"] for d in recent]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 3), dpi=100)
    fig.patch.set_facecolor('#f8f9fa')
    ax.set_facecolor('#ffffff')
    
    # Plot bar chart
    bars = ax.bar(dates, counts, color='#3b82f6', edgecolor='#2563eb', linewidth=1.5, width=0.6)
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'{int(height)}',
            ha='center',
            va='bottom',
            fontsize=9,
            fontweight='bold',
            color='#1e293b'
        )
    
    # Styling
    ax.set_title(f'{profile_label} — Ostatnie {len(recent)} dni', 
                 fontsize=12, fontweight='bold', color='#1e293b', pad=15)
    ax.set_xlabel('Data', fontsize=10, color='#64748b')
    ax.set_ylabel('Liczba ogłoszeń', fontsize=10, color='#64748b')
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.xticks(rotation=0, ha='center', fontsize=9)
    
    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3, color='#cbd5e1')
    ax.set_axisbelow(True)
    
    # Spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#cbd5e1')
    ax.spines['bottom'].set_color('#cbd5e1')
    
    # Tight layout
    plt.tight_layout()
    
    # Save to Base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', facecolor='#f8f9fa')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"


def calculate_weekly_stats(profile_data, week_ago_str):
    """
    Calculate weekly statistics for a profile.
    Returns: dict with stats or None.
    """
    dc = profile_data.get("daily_counts", [])
    week = [d for d in dc if d["date"] >= week_ago_str]
    
    if not week:
        return None
    
    current = week[-1]["count"] if week else 0
    first = week[0]["count"] if week else 0
    change = current - first
    vals = [d["count"] for d in week]
    
    # Price statistics
    listings = profile_data.get("current_listings", [])
    prices = [l["price"] for l in listings if l.get("price") and l["price"] > 0]
    
    # NEW: Promoted statistics
    promoted_count = sum(1 for l in listings if l.get("is_promoted"))
    promoted_pct = round(promoted_count / len(listings) * 100, 1) if listings else 0
    
    # Promotion breakdown
    promo_breakdown = {}
    for l in listings:
        if l.get("is_promoted"):
            ptype = l.get("promotion_type", 'unknown')
            promo_breakdown[ptype] = promo_breakdown.get(ptype, 0) + 1
    
    # Promoted trend (first vs last in week)
    promoted_trend = 0
    if len(week) >= 2:
        first_promoted_pct = week[0].get("promoted_percentage", 0)
        last_promoted_pct = week[-1].get("promoted_percentage", 0)
        promoted_trend = last_promoted_pct - first_promoted_pct
    
    return {
        "current": current,
        "change": change,
        "min_count": min(vals),
        "max_count": max(vals),
        "avg_price": round(sum(prices) / len(prices)) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "total_listings": len(listings),
        "new_24h": len([l for l in listings if is_new_listing(l)]),
        # NEW: Promoted stats
        "promoted_count": promoted_count,
        "promoted_pct": promoted_pct,
        "promoted_breakdown": promo_breakdown,
        "promoted_trend": promoted_trend,
    }


def is_new_listing(listing):
    """Check if listing is newer than 24h."""
    if not listing.get("first_seen"):
        return False
    try:
        fs = datetime.strptime(listing["first_seen"], "%Y-%m-%d %H:%M:%S")
        return fs > datetime.now() - timedelta(days=1)
    except:
        return False


# ─── HTML Report Builder ───────────────────────────────────────────────────

def build_report_html():
    """Build analytics-focused HTML email report."""
    if not os.path.exists(JSON_PATH):
        return "<p>Brak danych — plik JSON nie istnieje.</p>"

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    today = datetime.now()
    week_ago = today - timedelta(days=7)
    week_ago_str = week_ago.strftime("%Y-%m-%d")
    last_scan = data.get("last_scan", "Brak danych")

    # ─── HTML Header ───
    html = f"""
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            color: #1e293b;
            background: #f1f5f9;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
        }}
        h1 {{
            color: #0f172a;
            border-bottom: 4px solid #3b82f6;
            padding-bottom: 15px;
            margin-top: 0;
            font-size: 28px;
        }}
        h2 {{
            color: #334155;
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 20px;
            border-left: 4px solid #3b82f6;
            padding-left: 12px;
        }}
        .info-bar {{
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 16px 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .info-bar p {{
            margin: 6px 0;
            font-size: 14px;
            color: #475569;
        }}
        .info-bar strong {{
            color: #1e293b;
        }}
        .stats-grid {{
            display: table;
            width: 100%;
            table-layout: fixed;
            border-spacing: 12px 0;
            margin: 20px 0;
        }}
        .stat-card {{
            display: table-cell;
            background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            vertical-align: top;
            width: 25%;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
            color: #3b82f6;
            margin: 8px 0;
        }}
        .stat-label {{
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}
        .stat-change {{
            font-size: 14px;
            font-weight: 600;
            margin-top: 8px;
        }}
        .stat-change.up {{ color: #10b981; }}
        .stat-change.down {{ color: #ef4444; }}
        .stat-change.neutral {{ color: #64748b; }}
        .chart-container {{
            margin: 30px 0;
            text-align: center;
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #e5e7eb;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            font-size: 14px;
        }}
        th {{
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
            color: white;
            padding: 12px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        th:first-child {{
            border-top-left-radius: 8px;
        }}
        th:last-child {{
            border-top-right-radius: 8px;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid #e5e7eb;
        }}
        tr:nth-child(even) {{
            background: #f8fafc;
        }}
        tr:hover {{
            background: #eff6ff;
        }}
        a {{
            color: #3b82f6;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .price {{
            font-weight: 700;
            color: #0f172a;
            font-size: 15px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 700;
        }}
        .badge-up {{ background: #d1fae5; color: #065f46; }}
        .badge-down {{ background: #fee2e2; color: #991b1b; }}
        .badge-same {{ background: #f1f5f9; color: #64748b; }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            color: #64748b;
            font-size: 13px;
            text-align: center;
        }}
        .footer a {{
            color: #3b82f6;
            font-weight: 600;
        }}
        .profile-section {{
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px dashed #e5e7eb;
        }}
        .promo-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            background: #fef3c7;
            color: #92400e;
        }}
        .promo-featured {{ background: #fef3c7; color: #92400e; }}
        .promo-top {{ background: #dbeafe; color: #1e40af; }}
        .promo-highlight {{ background: #d1fae5; color: #065f46; }}
        .insight-box {{
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 16px 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .insight-box ul {{
            margin: 8px 0;
            padding-left: 20px;
        }}
        .insight-box li {{
            margin: 8px 0;
            color: #334155;
            line-height: 1.6;
        }}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>🔍 SZPERACZ OLX — Raport analityczny</h1>
        
        <div class="info-bar">
            <p><strong>📅 Okres:</strong> {week_ago.strftime('%d.%m.%Y')} – {today.strftime('%d.%m.%Y')}</p>
            <p><strong>🕒 Ostatni scan:</strong> {last_scan}</p>
            <p><strong>📊 Tryb raportu:</strong> Analityka z trendami tygodniowymi</p>
        </div>
    """

    # ─── PROMOTED ANALYSIS SECTION ───
    html += '<h2>🎯 Analiza promocji</h2>'
    html += '''
    <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr style="background:#f1f5f9;">
            <th style="padding:12px;text-align:left;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">Profil</th>
            <th style="padding:12px;text-align:center;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">Promowane</th>
            <th style="padding:12px;text-align:center;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">% Promowanych</th>
            <th style="padding:12px;text-align:center;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">Trend (7 dni)</th>
            <th style="padding:12px;text-align:left;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">Typ dominujący</th>
        </tr>
    '''
    
    profiles_data = data.get("profiles", {})
    promo_insights = []
    
    for pk, pd in profiles_data.items():
        label = pd.get("label", pk)
        dc = pd.get("daily_counts", [])
        week = [d for d in dc if d.get("date", "") >= week_ago_str]
        
        if not week:
            continue
        
        latest = week[-1]
        total = latest.get("count", 0)
        promoted = latest.get("promoted_count", 0)
        pct = latest.get("promoted_percentage", 0)
        
        # Calculate trend
        trend_html = '—'
        if len(week) >= 2:
            first_pct = week[0].get("promoted_percentage", 0)
            trend_diff = pct - first_pct
            if trend_diff > 5:
                trend_html = f'<span style="color:#059669;font-weight:700;">+{trend_diff:.1f}pp ↑</span>'
            elif trend_diff < -5:
                trend_html = f'<span style="color:#dc2626;font-weight:700;">{trend_diff:.1f}pp ↓</span>'
            else:
                trend_html = '<span style="color:#64748b;">stabilny</span>'
        
        # Dominant type
        breakdown = latest.get("promotion_breakdown", {})
        dominant_str = '—'
        if breakdown:
            dominant = max(breakdown.items(), key=lambda x: x[1])
            type_badge_class = {
                'featured': 'promo-featured',
                'top_ad': 'promo-top',
                'highlight': 'promo-highlight'
            }.get(dominant[0], 'promo-badge')
            dominant_str = f'<span class="promo-badge {type_badge_class}">{dominant[0]} ({dominant[1]})</span>'
        
        html += f'''
        <tr>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;"><strong>{label}</strong></td>
            <td style="padding:10px;text-align:center;border-bottom:1px solid #e5e7eb;">{promoted} / {total}</td>
            <td style="padding:10px;text-align:center;border-bottom:1px solid #e5e7eb;font-weight:700;color:#3b82f6;font-size:15px;">{pct}%</td>
            <td style="padding:10px;text-align:center;border-bottom:1px solid #e5e7eb;">{trend_html}</td>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{dominant_str}</td>
        </tr>
        '''
        
        # Generate insights
        avg_pct = sum(d.get("promoted_percentage", 0) for d in week) / len(week) if week else 0
        if avg_pct > 50:
            promo_insights.append(f"<strong>{label}</strong> stosuje agresywną strategię promocyjną (średnio {avg_pct:.0f}% promowanych)")
        elif avg_pct < 10 and total > 5:
            promo_insights.append(f"<strong>{label}</strong> nie inwestuje w promocje (tylko {avg_pct:.0f}%)")
        
        if len(week) >= 2 and trend_diff > 15:
            promo_insights.append(f"<strong>{label}</strong> znacząco zwiększył inwestycję w promocje (+{trend_diff:.0f}pp w tydzień)")
    
    html += '</table>'
    
    # Insights box
    if promo_insights:
        html += '''
        <div class="insight-box">
            <h3 style="margin:0 0 12px 0;color:#1e40af;font-size:16px;">💡 Insights</h3>
            <ul style="margin:0;padding-left:20px;">
        '''
        for insight in promo_insights[:5]:  # Max 5 insights
            html += f'<li>{insight}</li>'
        html += '</ul></div>'
    
    # ─── Competitor Ranking ───
    html += '<h2>🏆 Ranking konkurencji (% promowanych)</h2>'
    
    # Calculate rankings
    rankings = []
    for pk, pd in profiles_data.items():
        dc = pd.get("daily_counts", [])
        week = [d for d in dc if d.get("date", "") >= week_ago_str]
        if not week:
            continue
        
        avg_pct = sum(d.get("promoted_percentage", 0) for d in week) / len(week)
        total = week[-1].get("count", 0)
        
        # Assign tier
        if avg_pct >= 60:
            tier = "🔥 Aggressive"
            tier_color = "#dc2626"
        elif avg_pct >= 30:
            tier = "⚡ Moderate"
            tier_color = "#f59e0b"
        elif avg_pct >= 10:
            tier = "💡 Light"
            tier_color = "#3b82f6"
        else:
            tier = "🌱 Organic"
            tier_color = "#059669"
        
        rankings.append({
            'label': pd.get("label", pk),
            'pct': avg_pct,
            'tier': tier,
            'tier_color': tier_color,
            'total': total
        })
    
    rankings.sort(key=lambda x: x['pct'], reverse=True)
    
    html += '''
    <table style="width:100%;border-collapse:collapse;margin:20px 0;">
        <tr style="background:#f1f5f9;">
            <th style="padding:12px;text-align:center;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;width:60px;">Miejsce</th>
            <th style="padding:12px;text-align:left;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">Profil</th>
            <th style="padding:12px;text-align:center;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">% Promowanych</th>
            <th style="padding:12px;text-align:left;font-size:13px;color:#475569;border-bottom:2px solid #cbd5e1;">Strategia</th>
        </tr>
    '''
    
    medals = ['🥇', '🥈', '🥉']
    for i, rank in enumerate(rankings[:10], 1):  # Top 10
        medal = medals[i-1] if i <= 3 else f'{i}.'
        html += f'''
        <tr>
            <td style="padding:10px;text-align:center;border-bottom:1px solid #e5e7eb;font-size:18px;">{medal}</td>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;"><strong>{rank['label']}</strong></td>
            <td style="padding:10px;text-align:center;border-bottom:1px solid #e5e7eb;font-weight:700;color:#3b82f6;font-size:16px;">{rank['pct']:.1f}%</td>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;"><span style="color:{rank['tier_color']};font-weight:700;">{rank['tier']}</span></td>
        </tr>
        '''
    
    html += '</table>'

    # ─── Profile Analytics Sections ───
    for pk, pd in profiles_data.items():
        label = pd.get("label", pk)
        stats = calculate_weekly_stats(pd, week_ago_str)
        
        if not stats:
            continue
        
        html += f'<div class="profile-section">'
        html += f'<h2>📌 {label}</h2>'
        
        # Stats Grid
        change_class = "up" if stats["change"] > 0 else "down" if stats["change"] < 0 else "neutral"
        change_symbol = "↑" if stats["change"] > 0 else "↓" if stats["change"] < 0 else "="
        change_sign = "+" if stats["change"] > 0 else ""
        
        html += f'''
        <table class="stats-grid" cellpadding="0" cellspacing="0">
            <tr>
                <td class="stat-card">
                    <div class="stat-label">Aktualna liczba</div>
                    <div class="stat-value">{stats["current"]}</div>
                    <div class="stat-change {change_class}">{change_sign}{stats["change"]} {change_symbol} (7 dni)</div>
                </td>
                <td class="stat-card">
                    <div class="stat-label">Zakres (tydzień)</div>
                    <div class="stat-value" style="font-size:24px;">{stats["min_count"]} – {stats["max_count"]}</div>
                    <div class="stat-change neutral">min / max</div>
                </td>
                <td class="stat-card">
                    <div class="stat-label">Średnia cena</div>
                    <div class="stat-value" style="font-size:28px;">{stats["avg_price"]} zł</div>
                    <div class="stat-change neutral">{stats["min_price"]} – {stats["max_price"]} zł</div>
                </td>
                <td class="stat-card">
                    <div class="stat-label">Nowe (24h)</div>
                    <div class="stat-value" style="color:#10b981;">{stats["new_24h"]}</div>
                    <div class="stat-change neutral">z {stats["total_listings"]} aktywnych</div>
                </td>
            </tr>
        </table>
        '''
        
        # Chart
        chart_base64 = generate_trend_chart(pd, label, days=7)
        if chart_base64:
            html += f'''
            <div class="chart-container">
                <img src="{chart_base64}" alt="{label} trend chart">
            </div>
            '''
        
        # Listings Table (top 10 most recent)
        listings = sorted(
            pd.get("current_listings", []),
            key=lambda x: x.get("first_seen", ""),
            reverse=True
        )[:10]  # Top 10
        
        if listings:
            html += f'''
            <h3 style="color:#475569;font-size:16px;margin-top:30px;">
                🏠 Najnowsze ogłoszenia ({len(listings)} z {stats["total_listings"]})
            </h3>
            <table>
                <tr>
                    <th>Tytuł</th>
                    <th style="text-align:center;width:50px;">🎯</th>
                    <th>Cena</th>
                    <th style="text-align:center;">Data publikacji</th>
                </tr>
            '''
            
            for listing in listings:
                title = listing.get("title", "—")
                url = listing.get("url", "#")
                price = f'{listing["price"]} zł' if listing.get("price") else "—"
                pub_date = listing.get("published", listing.get("date_text", "—"))
                
                # Promoted badge
                promoted_badge = ''
                if listing.get("is_promoted"):
                    promo_type = listing.get("promotion_type", 'unknown')
                    emoji = {
                        'featured': '⭐',
                        'top_ad': '🔝',
                        'highlight': '✨'
                    }.get(promo_type, '🎯')
                    promoted_badge = f'<span style="font-size:16px;" title="{promo_type}">{emoji}</span>'
                else:
                    promoted_badge = '<span style="color:#cbd5e1;">—</span>'
                
                # Highlight promoted rows
                row_style = 'background:#eff6ff;' if listing.get("is_promoted") else ''
                
                html += f'''
                <tr style="{row_style}">
                    <td><a href="{url}" target="_blank">{title}</a></td>
                    <td style="text-align:center;">{promoted_badge}</td>
                    <td><span class="price">{price}</span></td>
                    <td style="text-align:center;color:#64748b;">{pub_date}</td>
                </tr>
                '''
            
            html += '</table>'
        
        html += '</div>'  # End profile-section
    
    # ─── Footer ───
    html += f"""
        <div class="footer">
            <p>🤖 Wygenerowano automatycznie przez <strong>SZPERACZ OLX</strong></p>
            <p>{today.strftime('%d.%m.%Y %H:%M')} • W załączniku pełne dane w Excel</p>
            <p><a href="https://github.com/Bonaventura-EW/SZPERACZ" target="_blank">GitHub Repository</a></p>
        </div>
    </div>
    </body>
    </html>
    """
    
    return html


# ─── Email Sender ───────────────────────────────────────────────────────────

def send_report():
    """Send weekly email report with analytics."""
    if not EMAIL_PASSWORD:
        log.error("EMAIL_PASSWORD not set!")
        return False

    today = datetime.now()
    subject = f"📊 SZPERACZ OLX — Raport analityczny ({today.strftime('%d.%m.%Y')})"

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    
    # Build and attach HTML
    log.info("Building HTML report...")
    html_content = build_report_html()
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # Attach Excel
    if os.path.exists(EXCEL_PATH):
        try:
            with open(EXCEL_PATH, "rb") as f:
                part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = f'szperacz_olx_{today.strftime("%Y%m%d")}.xlsx'
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)
            log.info(f"Excel attached: {filename}")
        except Exception as e:
            log.warning(f"Could not attach Excel: {e}")

    # Send
    try:
        log.info("Connecting to SMTP server...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        log.info(f"✅ Email sent successfully to {RECEIVER_EMAIL}")
        return True
    except smtplib.SMTPAuthenticationError:
        log.error("❌ SMTP auth failed. Check EMAIL_PASSWORD (App Password required).")
        return False
    except Exception as e:
        log.error(f"❌ Email failed: {e}")
        return False


# ─── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("SZPERACZ OLX — Weekly Email Report")
    log.info("=" * 60)
    send_report()
