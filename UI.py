"""
UI.py — WillowStrike: an English-willow cricket bat store (Streamlit UI prototype)
==================================================================================

Run it:
    pip install streamlit pandas          # Streamlit 1.50 or newer
    streamlit run UI.py

Demo login:  demo@willowstrike.example  /  demo123

What's inside
    • Home page      – hero banner, trust badges, series tiles, featured bats, grade guide
    • Shop           – English willow bats only, with search / series / grade / sweet-spot / price filters
    • Product popup  – "Choose options" dialog: size, weight, handle, add-ons, quantity
    • Cart/Checkout  – quantity edit, coupons (WILLOW10, FIRSTBAT), address, delivery, payment choice
    • Login/Sign-up  – salted PBKDF2 password hashing, validation, forgot-password screen
    • My Account     – orders, bulk quotes, support tickets, profile and password change
    • Bulk Purchase  – editable order table, tiered discounts, team customisation, live quote
    • Support        – chat assistant, raise a ticket (with photo upload), track order, FAQs, policies

This is a front-end prototype: data lives in memory (st.cache_resource) and resets when
the server restarts. Swap get_db() for a real database when you add a backend.

Optional dark theme — create .streamlit/config.toml next to this file containing:
    [theme]
    base = "dark"
    primaryColor = "#D7263D"
"""

import base64
import datetime as dt
import hashlib
import random
import re
import secrets
from functools import lru_cache

import pandas as pd
import streamlit as st

# ════════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG & BRAND
# ════════════════════════════════════════════════════════════════════════════════
BRAND_A, BRAND_B = "WILLOW", "STRIKE"          # change your brand name here
BRAND = BRAND_A.title() + BRAND_B.title()
SUPPORT_PHONE = "1800-000-0000"                # placeholder contact details
SUPPORT_EMAIL = "support@willowstrike.example"
WHATSAPP = "+91 00000 00000"

st.set_page_config(
    page_title=f"{BRAND} | English Willow Cricket Bats",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ════════════════════════════════════════════════════════════════════════════════
#  CATALOGUE  (English willow only)
# ════════════════════════════════════════════════════════════════════════════════
SERIES = {
    "Titan":    {"tag": "Players' grade · huge edges",   "c1": "#111111", "c2": "#E9B44C",
                 "bg": "linear-gradient(135deg,#0d0d0d 0%,#3b2f12 100%)"},
    "Heritage": {"tag": "Vintage shapes · classic feel", "c1": "#F3E9D2", "c2": "#7A1F2B",
                 "bg": "linear-gradient(135deg,#3d1016 0%,#7a1f2b 100%)"},
    "Storm":    {"tag": "Power hitting · low middle",    "c1": "#0B1F4B", "c2": "#3FA7FF",
                 "bg": "linear-gradient(135deg,#071430 0%,#12407a 100%)"},
    "Legacy":   {"tag": "Balanced all-rounder",          "c1": "#D7263D", "c2": "#FFFFFF",
                 "bg": "linear-gradient(135deg,#4a0b14 0%,#b31b30 100%)"},
    "Club":     {"tag": "Value willow for league play",  "c1": "#1F5130", "c2": "#9BE15D",
                 "bg": "linear-gradient(135deg,#0e2a18 0%,#2f6b3f 100%)"},
    "Academy":  {"tag": "Junior sizes · light pick-up",  "c1": "#E8711A", "c2": "#171717",
                 "bg": "linear-gradient(135deg,#5a2a06 0%,#e8711a 100%)"},
}

GRADES = ["Grade 1+", "Grade 1", "Grade 2", "Grade 3", "Grade 4"]

SIZE_LABEL = {
    "SH": "Short Handle (SH)", "LH": "Long Handle (LH)", "Harrow": "Harrow",
    "Size 6": "Size 6", "Size 5": "Size 5", "Size 4": "Size 4",
}
SENIOR_SIZES = ["SH", "LH", "Harrow"]
JUNIOR_SIZES = ["Size 4", "Size 5", "Size 6", "Harrow"]
SENIOR_WEIGHTS = ["Light (2lb 7oz – 2lb 9oz)", "Medium (2lb 9oz – 2lb 11oz)", "Heavy (2lb 11oz – 2lb 13oz)"]
JUNIOR_WEIGHTS = ["Light (2lb 0oz – 2lb 2oz)", "Standard (2lb 2oz – 2lb 5oz)"]

ADDONS = {
    "Pro knocking-in (6 hrs)": 1200,
    "Anti-scuff sheet fitted": 299,
    "Toe guard": 199,
    "Extra grip": 249,
    "Name engraving": 499,
}


def _p(pid, name, series, grade, mrp, off, grains, edge, spine, sweet, handle,
       badge, stock, desc, junior=False):
    return dict(
        id=pid, name=name, series=series, grade=grade, mrp=mrp, off=off,
        grains=grains, edge=edge, spine=spine, sweet=sweet, handle=handle,
        badge=badge, stock=stock, desc=desc,
        sizes=JUNIOR_SIZES if junior else SENIOR_SIZES,
        weights=JUNIOR_WEIGHTS if junior else SENIOR_WEIGHTS,
    )


PRODUCTS = [
    _p("WS-T01", "Titan Players Edition", "Titan", "Grade 1+", 42999, 15, "12–14", "40–42 mm", "66 mm", "Mid", "Round",
       "Pro choice", 4, "Our flagship cleft: hand-selected, unbleached Grade 1+ willow with a full spine and thick "
       "edges for players who want maximum ping off the middle."),
    _p("WS-T02", "Titan Elite", "Titan", "Grade 1", 34999, 15, "10–12", "39–41 mm", "64 mm", "Mid", "Round",
       "Bestseller", 12, "Grade 1 performance with a slightly lighter pick-up. The mid sweet spot suits front- and "
       "back-foot players alike."),
    _p("WS-H01", "Heritage 1975 Vintage", "Heritage", "Grade 1", 31999, 12, "10–12", "37–39 mm", "60 mm", "Mid", "Oval",
       "Limited", 3, "Old-school shape with a gentle bow and an oval handle: classic feel in the hands, modern "
       "performance off the middle."),
    _p("WS-H02", "Heritage Classic", "Heritage", "Grade 2", 22999, 15, "8–10", "37–39 mm", "61 mm", "Mid", "Oval",
       None, 15, "Traditional profile in Grade 2 willow, beautifully balanced for touch players who time the ball."),
    _p("WS-S01", "Storm Thunder XL", "Storm", "Grade 1", 36999, 10, "9–12", "42–44 mm", "68 mm", "Low", "Round",
       "New", 8, "Massive edges and a low middle, built for T20 power hitting and full-length deliveries."),
    _p("WS-S02", "Storm Power", "Storm", "Grade 2", 24899, 15, "8–10", "40–42 mm", "65 mm", "Low", "Round",
       "Bestseller", 20, "Big-hitting profile in Grade 2 willow. Great value for aggressive openers."),
    _p("WS-S03", "Storm Blast", "Storm", "Grade 3", 15499, 15, "6–8", "38–40 mm", "62 mm", "Low", "Round",
       None, 25, "The Storm shape at a club-friendly price, with plenty of meat low down for drives."),
    _p("WS-L01", "Legacy Pro", "Legacy", "Grade 2", 19999, 15, "8–10", "38–40 mm", "62 mm", "Mid", "Round",
       None, 18, "A balanced all-rounder with a forgiving middle and a light, easy pick-up."),
    _p("WS-L02", "Legacy Edge", "Legacy", "Grade 2", 21499, 12, "8–10", "39–41 mm", "63 mm", "High", "Round",
       None, 10, "High middle for bouncy tracks and back-foot strokeplay: cuts, pulls and punches."),
    _p("WS-L03", "Legacy Balance", "Legacy", "Grade 3", 13999, 15, "6–8", "37–39 mm", "60 mm", "Mid", "Round",
       None, 30, "Dependable Grade 3 English willow for weekend and league cricketers."),
    _p("WS-C01", "Club Match", "Club", "Grade 4", 9499, 20, "5–7", "36–38 mm", "58 mm", "Mid", "Round",
       "Value pick", 40, "Genuine English willow for your first leather-ball season, without the premium price."),
    _p("WS-C02", "Club Practice", "Club", "Grade 4", 7999, 20, "5–7", "35–37 mm", "57 mm", "Mid", "Round",
       None, 50, "Tough, durable willow for nets and practice sessions. A favourite for academy kit bags."),
    _p("WS-A01", "Academy Junior Pro", "Academy", "Grade 3", 8999, 10, "6–8", "32–35 mm", "52 mm", "Mid", "Round",
       "Junior", 22, "Proper English willow scaled down for juniors, with a light pick-up to build good technique.",
       junior=True),
    _p("WS-A02", "Academy Junior Club", "Academy", "Grade 4", 6499, 10, "5–7", "31–33 mm", "50 mm", "Mid", "Round",
       None, 35, "An affordable junior English willow bat for young cricketers moving up to the leather ball.",
       junior=True),
]
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}
PRODUCT_BY_NAME = {p["name"]: p for p in PRODUCTS}


def sale_price(p):
    return round(p["mrp"] * (1 - p["off"] / 100))


PMIN = (min(sale_price(p) for p in PRODUCTS) // 1000) * 1000
PMAX = ((max(sale_price(p) for p in PRODUCTS) // 1000) + 1) * 1000

GRADE_GUIDE = pd.DataFrame([
    {"Grade": "Grade 1+", "Straight grains": "12+", "Appearance": "Unbleached, virtually blemish-free",
     "Best for": "Professional / elite"},
    {"Grade": "Grade 1", "Straight grains": "10–12", "Appearance": "Minimal marks, very even colour",
     "Best for": "State & serious club players"},
    {"Grade": "Grade 2", "Straight grains": "8–10", "Appearance": "A few small speckles or butterfly marks",
     "Best for": "Regular club cricket"},
    {"Grade": "Grade 3", "Straight grains": "6–8", "Appearance": "Visible blemishes, some heartwood",
     "Best for": "Weekend & league cricket"},
    {"Grade": "Grade 4", "Straight grains": "5–7", "Appearance": "Heartwood and colour variation",
     "Best for": "Practice, juniors, budget"},
])

SIZE_GUIDE = pd.DataFrame([
    {"Bat size": "Size 4", "Player height (approx.)": "4'3\" – 4'6\"", "Typical age": "8–10"},
    {"Bat size": "Size 5", "Player height (approx.)": "4'6\" – 4'9\"", "Typical age": "10–11"},
    {"Bat size": "Size 6", "Player height (approx.)": "4'9\" – 5'1\"", "Typical age": "11–13"},
    {"Bat size": "Harrow", "Player height (approx.)": "5'1\" – 5'5\"", "Typical age": "13–15"},
    {"Bat size": "Short Handle (SH)", "Player height (approx.)": "5'5\" – 6'1\"", "Typical age": "Adult"},
    {"Bat size": "Long Handle (LH)", "Player height (approx.)": "6'1\" and above", "Typical age": "Adult"},
])

# Bulk purchase pricing: extra discount on top of the online sale price
BULK_TIERS = [(100, 0.15, "Platinum"), (50, 0.12, "Gold"), (25, 0.08, "Silver"), (10, 0.05, "Bronze")]
BULK_MIN_QTY = 10
BULK_CUSTOM = {
    "Team logo laser engraving": 350,
    "Player name engraving": 250,
    "Custom sticker design (min. 25 bats)": 600,
    "Pro knocking-in & oiling": 900,
    "Padded bat cover with team logo": 450,
}

COUPONS = {
    "WILLOW10": {"type": "pct", "value": 10, "min": 0, "desc": "10% off your order"},
    "FIRSTBAT": {"type": "flat", "value": 1000, "min": 15000, "desc": "₹1,000 off orders above ₹15,000"},
}

ORDER_STEPS = ["Order placed", "Packed", "Shipped", "Out for delivery", "Delivered"]

STATES = ["Andhra Pradesh", "Assam", "Bihar", "Chandigarh", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jammu & Kashmir", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
          "Maharashtra", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
          "Uttar Pradesh", "Uttarakhand", "West Bengal"]

FAQS = [
    ("What makes English willow different from Kashmir willow?",
     "English willow (Salix alba caerulea) is lighter, softer and more fibrous, so it compresses better on impact "
     "and gives a bigger 'ping'. It needs knocking-in before use, while Kashmir willow is harder and heavier."),
    ("Do I need to knock in my bat?",
     "Yes. A new English willow bat needs 4–6 hours of knocking-in with a mallet, plus a light coat of raw linseed "
     "oil on the face and edges. Choose our Pro knocking-in add-on and we'll do it for you before dispatch."),
    ("How do I choose the right size?",
     "Most adults use a Short Handle (SH). Players over about 6'1\" usually prefer a Long Handle (LH). See the "
     "size guide below for junior sizes."),
    ("Does a higher grade mean a better bat?",
     "Grade is mainly about appearance: grain count, straightness and blemishes. Performance depends just as much "
     "on pressing and shape, so a well-made Grade 2 can outperform a poorly pressed Grade 1."),
    ("How long does delivery take?",
     "Orders are dispatched within 24–48 hours. Standard delivery (free) takes 4–6 working days; Express "
     "(₹299) takes 1–2 working days in metro cities."),
    ("What does the bat warranty cover?",
     "A 1-year limited warranty covers manufacturing defects such as handle failure or a split along the grain. "
     "Surface cracks, toe damage from moisture or yorkers, and misuse are not covered."),
    ("Can I return a bat?",
     "Unused bats in original condition (stickers intact, not knocked-in or oiled) can be returned within 7 days "
     "of delivery. Customised or engraved bats can't be returned."),
    ("Do you offer bulk or academy pricing?",
     f"Yes. Orders of {BULK_MIN_QTY}+ bats get an extra 5–15% off, free shipping and optional team branding. "
     "Use the Bulk Purchase page to build a quote."),
]

TESTIMONIALS = [  # placeholder content for the prototype; replace with real customer feedback
    ("Club cricketer · Mumbai", "The Titan Elite picked up beautifully and the pre-knocked option meant I could play "
                                "the same weekend."),
    ("Academy coach · Pune", "Ordered 40 Club Practice bats for our academy. The bulk quote was quick and the team "
                             "logo engraving looked sharp."),
    ("Opening batter · Bengaluru", "Storm Power has huge edges for the price. Support helped me pick the right weight "
                                   "over chat."),
]

CHAT_RULES = [
    (["ship", "deliver", "dispatch", "courier"],
     "📦 Orders are dispatched within 24–48 hours. **Standard** delivery is free (4–6 working days) and "
     "**Express** is ₹299 (1–2 working days in metro cities)."),
    (["warranty", "crack", "broke", "broken", "split", "damage"],
     "🛡️ Every bat has a **1-year limited warranty** against manufacturing defects (handle failure, splits along "
     "the grain). Raise a ticket in the *Raise a Ticket* tab with category **Warranty claim** and attach photos."),
    (["return", "refund", "replace", "exchange"],
     "↩️ Unused bats can be returned within **7 days** of delivery in original condition. Customised bats are "
     "non-returnable. Raise a *Return / Replacement* ticket to start."),
    (["knock", "oil", "linseed", "prepare", "new bat"],
     "🔨 English willow needs **4–6 hours of knocking-in** plus a light coat of raw linseed oil. Add "
     "**Pro knocking-in (₹1,200)** in the product options and we'll prepare it before dispatch."),
    (["bulk", "academy", "team", "club order", "school", "corporate", "wholesale"],
     f"🏟️ Bulk orders start at **{BULK_MIN_QTY} bats** with an extra **5–15% off**, free shipping and team "
     "branding. Head to the **Bulk Purchase** page to build an instant quote."),
    (["size", "height", "harrow", "short handle", "long handle", "junior"],
     "📏 Most adults use **Short Handle (SH)**; players over about 6'1\" usually go **Long Handle (LH)**. "
     "Harrow suits roughly 5'1\"–5'5\". The full size guide is in the FAQs tab."),
    (["grade", "grain", "difference", "which bat"],
     "🌳 Grades run from **Grade 1+** (12+ straight grains, no blemishes) to **Grade 4** (heartwood and colour "
     "variation). Grade mostly reflects looks; pressing and shape drive performance."),
    (["weight", "heavy", "light", "pick up", "pickup"],
     "⚖️ Most players are comfortable at **2lb 9oz – 2lb 11oz** (Medium). Go Light for quick hands and back-foot "
     "play, Heavy if you're strong and like to hit through the line."),
    (["track", "status", "where is my order", "order id"],
     "🔎 Use the **Track Order** tab and enter your order ID (for example *WS-100245*)."),
    (["pay", "upi", "cod", "cash", "emi", "card"],
     "💳 We accept UPI, cards, net banking, and cash on delivery for orders up to ₹20,000."),
    (["hi", "hello", "hey", "namaste"],
     "Hi there! 👋 Ask me about bat sizes, grades, weights, shipping, warranty or bulk orders."),
]


# ════════════════════════════════════════════════════════════════════════════════
#  IN-MEMORY "DATABASE"  (shared across browser sessions while the server runs)
# ════════════════════════════════════════════════════════════════════════════════
def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()


@st.cache_resource
def get_db():
    db = {"users": {}, "orders": [], "tickets": [], "quotes": [], "subscribers": set()}
    salt = secrets.token_hex(8)
    db["users"]["demo@willowstrike.example"] = {
        "name": "Demo Player", "phone": "9876543210", "salt": salt,
        "pw": hash_pw("demo123", salt), "joined": "2026-01-10",
    }
    db["orders"].append({
        "id": "WS-100245", "email": "demo@willowstrike.example",
        "date": (dt.date.today() - dt.timedelta(days=3)).isoformat(),
        "items": "Titan Elite (SH, Medium) × 1", "qty": 1, "total": 29749,
        "status": "Shipped", "payment": "UPI", "delivery": "Standard", "city": "Gurugram",
    })
    return db


DB = get_db()

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


# ════════════════════════════════════════════════════════════════════════════════
#  STYLES
# ════════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
:root { --ws-red:#D7263D; --ws-dark:#171717; --ws-gold:#E9B44C; }
.block-container { padding-top: 0.8rem; padding-bottom: 0; max-width: 1280px; }
header[data-testid="stHeader"] { display: none; }   /* remove to bring back Streamlit's top bar */
#MainMenu, footer { visibility: hidden; }

.ws-announce { background: var(--ws-dark); color:#fff; text-align:center; padding:8px 12px; font-size:.82rem;
  letter-spacing:.12em; border-radius:8px; margin-bottom:12px; }
.ws-announce b { color: var(--ws-gold); }
.ws-logo { font-weight:900; font-size:1.7rem; letter-spacing:.04em; line-height:1.05; }
.ws-logo span { color: var(--ws-red); }
.ws-tag { font-size:.66rem; letter-spacing:.28em; opacity:.65; font-weight:700; text-transform:uppercase; }

.ws-hero { background: radial-gradient(circle at 85% 40%, rgba(215,38,61,.45), transparent 45%),
  linear-gradient(135deg,#121212 0%,#2a0d12 60%,#5a0f1c 100%); color:#fff; border-radius:18px;
  padding:40px 48px; display:flex; align-items:center; justify-content:space-between; gap:24px;
  flex-wrap:wrap; margin:8px 0 14px; }
.ws-hero .ws-h1 { color:#fff; font-size:2.7rem; line-height:1.08; margin:6px 0 12px; font-weight:900; padding:0; }
.ws-hero p { color:#e6e6e6; font-size:1.05rem; max-width:580px; margin-bottom:10px; }
.ws-kicker { color: var(--ws-gold); letter-spacing:.22em; font-size:.78rem; font-weight:800; }
.ws-hero img { width:330px; max-width:100%; }
.ws-chip { display:inline-block; border:1px solid rgba(255,255,255,.35); padding:4px 12px; border-radius:999px;
  margin:6px 6px 0 0; font-size:.78rem; color:#fff; }

.ws-section { font-weight:900; font-size:1.55rem; margin:28px 0 2px; letter-spacing:.01em; }
.ws-section span { color: var(--ws-red); }
.ws-sub { opacity:.7; margin-bottom:12px; font-size:.95rem; }
.ws-crumb { font-size:.8rem; opacity:.6; margin-top:6px; }

.ws-trust { border:1px solid rgba(215,38,61,.28); background:rgba(215,38,61,.06); border-radius:12px;
  padding:14px 16px; height:100%; }
.ws-trust .i { font-size:1.5rem; }
.ws-trust b { display:block; margin-top:2px; }
.ws-trust small { opacity:.75; }

.ws-tile { position:relative; border-radius:12px; display:flex; align-items:center; justify-content:center;
  overflow:hidden; }
.ws-badge { position:absolute; top:10px; left:10px; background:#fff; color:#171717; font-size:.66rem;
  font-weight:800; padding:3px 9px; border-radius:999px; letter-spacing:.06em; text-transform:uppercase; }
.ws-save { position:absolute; top:10px; right:10px; background:var(--ws-red); color:#fff; font-size:.68rem;
  font-weight:800; padding:3px 9px; border-radius:999px; }
.ws-grade { position:absolute; bottom:10px; left:10px; background:rgba(0,0,0,.55); color:#fff; font-size:.68rem;
  font-weight:700; padding:3px 9px; border-radius:999px; letter-spacing:.04em; }
.ws-price { color:var(--ws-red); font-weight:800; font-size:1.15rem; }
.ws-mrp { color:#8a8a8a; text-decoration:line-through; font-size:.88rem; margin-left:8px; }
.ws-from { font-size:.72rem; opacity:.7; margin-right:4px; }
.ws-stock { font-size:.75rem; color:#2e9e5b; font-weight:700; }
.ws-stock.low { color:#e07b00; }

.ws-series { height:118px; border-radius:12px; padding:14px 16px; color:#fff; display:flex;
  flex-direction:column; justify-content:flex-end; margin-bottom:6px; }
.ws-series b { font-size:1.25rem; letter-spacing:.03em; }
.ws-series small { opacity:.85; }

.ws-band { background:linear-gradient(90deg,#171717,#3a0b14); color:#fff; border-radius:14px; padding:24px 28px;
  margin:10px 0 8px; }
.ws-band .ws-h3 { color:#fff; margin:0 0 6px; font-size:1.3rem; font-weight:800; }
.ws-band p { color:#ddd; margin:0; }

.ws-review { border:1px solid rgba(128,128,128,.25); border-radius:12px; padding:16px 18px; height:100%; }
.ws-review .q { font-size:1.6rem; color:var(--ws-red); line-height:1; }
.ws-review small { opacity:.65; }

.ws-contact { border:1px solid rgba(128,128,128,.25); border-radius:12px; padding:14px 16px; height:100%; }
.ws-contact .i { font-size:1.4rem; }
.ws-contact small { opacity:.7; }

.ws-total { display:flex; justify-content:space-between; padding:4px 0; font-size:.95rem; }
.ws-total.big { font-size:1.2rem; font-weight:900; border-top:1px solid rgba(128,128,128,.3);
  padding-top:10px; margin-top:6px; }
.ws-total .neg { color:#2e9e5b; }

.ws-track { display:flex; align-items:flex-start; margin:18px 0 6px; }
.ws-step { display:flex; flex-direction:column; align-items:center; width:92px; flex-shrink:0; text-align:center; }
.ws-dot { width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-weight:800; border:2px solid #bbb; color:#999; }
.ws-dot.done { background:var(--ws-red); border-color:var(--ws-red); color:#fff; }
.ws-step .l { font-size:.75rem; margin-top:6px; opacity:.85; }
.ws-line { flex:1; height:3px; background:#ccc; margin-top:16px; }
.ws-line.done { background:var(--ws-red); }

.ws-footer { background:#171717; color:#cfcfcf; border-radius:16px 16px 0 0; padding:34px 40px 18px;
  margin-top:26px; display:grid; grid-template-columns:2fr 1fr 1fr 1.3fr; gap:24px; }
.ws-footer .ws-h4 { color:#fff; font-size:.82rem; letter-spacing:.14em; text-transform:uppercase; margin:0 0 10px;
  padding:0; }
.ws-footer ul { padding:0; margin:0; }
.ws-footer li { list-style:none; color:#cfcfcf; font-size:.86rem; line-height:1.95; }
.ws-footer p { color:#bdbdbd; font-size:.86rem; }
.ws-footer .ws-logo { color:#fff; }
.ws-social span { display:inline-block; border:1px solid #444; border-radius:999px; padding:3px 10px;
  margin:4px 6px 0 0; font-size:.75rem; color:#ddd; }
.ws-bottom { background:#0e0e0e; color:#9a9a9a; font-size:.76rem; padding:12px 40px; display:flex;
  justify-content:space-between; flex-wrap:wrap; gap:8px; border-radius:0 0 16px 16px; margin-bottom:18px; }

@media (max-width: 900px) {
  .ws-footer { grid-template-columns:1fr 1fr; padding:26px 22px; }
  .ws-hero { padding:28px 24px; }
  .ws-hero .ws-h1 { font-size:1.9rem; }
}
</style>
"""


# ════════════════════════════════════════════════════════════════════════════════
#  SMALL HELPERS
# ════════════════════════════════════════════════════════════════════════════════
def md(html: str):
    """Render raw HTML; strips indentation/blank lines so Markdown doesn't turn it into a code block."""
    st.markdown("\n".join(line.strip() for line in html.splitlines() if line.strip()), unsafe_allow_html=True)


def inr(x) -> str:
    """Indian-style currency format: 123456 -> ₹1,23,456"""
    x = int(round(x))
    sign, s = ("-" if x < 0 else ""), str(abs(x))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"{sign}₹{s}"


@lru_cache(maxsize=64)
def bat_img(series: str, angle: int = -32) -> str:
    """Original SVG illustration of an English willow bat, coloured by series. Returns a data URI."""
    c1, c2 = SERIES[series]["c1"], SERIES[series]["c2"]
    label = series.upper()
    fs = min(16, 84 / (len(label) * 0.74))
    grains = "".join(
        f'<line x1="{x}" y1="98" x2="{x}" y2="232" stroke="#B8955A" stroke-width="0.8" opacity="0.4"/>'
        for x in range(133, 170, 5))
    grip = "".join(
        f'<line x1="143" y1="{y}" x2="157" y2="{y + 6}" stroke="rgba(0,0,0,0.28)" stroke-width="2"/>'
        for y in range(-8, 72, 7))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 250" width="300" height="250">
<defs><linearGradient id="w" x1="0" x2="1">
<stop offset="0" stop-color="#E2C88E"/><stop offset="0.5" stop-color="#F7E9C6"/><stop offset="1" stop-color="#D6B574"/>
</linearGradient></defs>
<ellipse cx="150" cy="238" rx="92" ry="7" fill="rgba(0,0,0,0.28)"/>
<g transform="rotate({angle} 150 125)">
<rect x="143" y="-12" width="14" height="92" rx="6" fill="{c2}"/>{grip}
<path d="M143 78 L157 78 Q171 84 173 98 L127 98 Q129 84 143 78 Z" fill="url(#w)"/>
<rect x="127" y="96" width="46" height="140" rx="9" fill="url(#w)"/>{grains}
<rect x="127" y="108" width="46" height="94" fill="{c1}"/>
<rect x="127" y="108" width="46" height="4" fill="{c2}"/><rect x="127" y="198" width="46" height="4" fill="{c2}"/>
<text x="150" y="155" transform="rotate(-90 150 155)" text-anchor="middle" dominant-baseline="middle"
 font-family="Arial Black, Arial, Helvetica, sans-serif" font-weight="900" font-size="{fs:.1f}" fill="{c2}"
 letter-spacing="1.5">{label}</text>
<rect x="127" y="214" width="46" height="9" fill="{c1}"/>
</g></svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def tile_html(p, height=190) -> str:
    s = SERIES[p["series"]]
    badge = f'<div class="ws-badge">{p["badge"]}</div>' if p["badge"] else ""
    save = f'<div class="ws-save">Save {p["off"]}%</div>' if p["off"] else ""
    return (f'<div class="ws-tile" style="background:{s["bg"]};height:{height}px">{badge}{save}'
            f'<div class="ws-grade">{p["grade"]} · English Willow</div>'
            f'<img src="{bat_img(p["series"])}" style="height:{height - 16}px" alt="{p["name"]}"></div>')


def price_html(p, prefix=True) -> str:
    frm = '<span class="ws-from">From</span>' if prefix else ""
    return (f'<div>{frm}<span class="ws-price">{inr(sale_price(p))}</span>'
            f'<span class="ws-mrp">{inr(p["mrp"])}</span></div>')


def stock_html(p) -> str:
    if p["stock"] <= 5:
        return f'<span class="ws-stock low">● Only {p["stock"]} left</span>'
    return '<span class="ws-stock">● In stock · ships in 48 hrs</span>'


def section(title: str, accent: str = "", sub: str = ""):
    md(f'<div class="ws-section">{title} <span>{accent}</span></div>')
    if sub:
        md(f'<div class="ws-sub">{sub}</div>')


def user():
    email = st.session_state.user
    return (email, DB["users"][email]) if email else (None, None)


def cart_count() -> int:
    return sum(i["qty"] for i in st.session_state.cart)


def new_id(prefix: str, digits: int = 6) -> str:
    return f"{prefix}-{random.randint(10 ** (digits - 1), 10 ** digits - 1)}"


# ════════════════════════════════════════════════════════════════════════════════
#  SESSION STATE & CALLBACKS
# ════════════════════════════════════════════════════════════════════════════════
FILTER_DEFAULTS = {"f_search": "", "f_series": [], "f_grade": [], "f_sweet": [],
                   "f_price": (PMIN, PMAX), "f_sort": "Featured"}


def init_state():
    defaults = {
        "page": "home", "user": None, "cart": [], "coupon": None, "checkout_open": False,
        "after_login": None, "flash": None, "celebrate": False, "my_tickets": [],
        "chat": [{"role": "assistant", "content": f"Hi! 👋 I'm the {BRAND} bat assistant. Ask me about sizes, "
                                                  "grades, weights, knocking-in, delivery, warranty or bulk orders."}],
        "bulk_df": pd.DataFrame([
            {"Bat model": "Storm Power", "Size": "SH", "Weight": "Medium", "Qty": 15},
            {"Bat model": "Club Practice", "Size": "Harrow", "Weight": "Light", "Qty": 10},
        ]),
        **FILTER_DEFAULTS,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def go(page: str):
    st.session_state.page = page


def require_login(return_to: str):
    st.session_state.after_login = return_to
    st.session_state.page = "login"


def shop_series(name: str):
    for k, v in FILTER_DEFAULTS.items():
        st.session_state[k] = v
    st.session_state.f_series = [name]
    st.session_state.page = "shop"


def reset_filters():
    for k, v in FILTER_DEFAULTS.items():
        st.session_state[k] = v


def logout():
    st.session_state.user = None
    st.session_state.checkout_open = False
    st.session_state.flash = "You've been logged out."
    st.session_state.page = "home"


def set_qty(uid: str):
    for i in st.session_state.cart:
        if i["uid"] == uid:
            i["qty"] = int(st.session_state[f"q_{uid}"])


def remove_item(uid: str):
    st.session_state.cart = [i for i in st.session_state.cart if i["uid"] != uid]


def ask_bot(text: str):
    st.session_state.chat.append({"role": "user", "content": text})
    t = text.lower()
    reply = next((r for keys, r in CHAT_RULES if any(re.search(rf"\b{re.escape(k)}", t) for k in keys)), None)
    if reply is None:
        reply = (f"I couldn't find an answer to that. Please raise a ticket in the **Raise a Ticket** tab, or call "
                 f"**{SUPPORT_PHONE}** (Mon–Sat, 10am–7pm). A specialist will get back to you within 24 hours.")
    st.session_state.chat.append({"role": "assistant", "content": reply})


# ════════════════════════════════════════════════════════════════════════════════
#  LAYOUT: HEADER & FOOTER
# ════════════════════════════════════════════════════════════════════════════════
def header():
    md('<div class="ws-announce">🏏 <b>NEW SEASON CLEFTS HAVE LANDED</b> · FREE DELIVERY ACROSS INDIA · '
       'EXTRA 5–15% OFF ON BULK ORDERS</div>')
    logo_col, nav_col = st.columns([1.35, 4.65], vertical_alignment="center")
    with logo_col:
        md(f'<div class="ws-logo">🏏 {BRAND_A}<span>{BRAND_B}</span>'
           f'<div class="ws-tag">English Willow Specialists</div></div>')
    with nav_col:
        email, u = user()
        page = st.session_state.page
        items = [
            ("home", "Home", "🏠"),
            ("shop", "Shop Bats", "🏏"),
            ("bulk", "Bulk Purchase", "📦"),
            ("support", "Support", "💬"),
            ("cart", f"Cart ({cart_count()})", "🛒"),
            ("account" if email else "login", (u["name"].split()[0] if email else "Login"), "👤" if email else "🔐"),
        ]
        cols = st.columns(len(items))
        for col, (target, label, icon) in zip(cols, items):
            active = page == target or (target == "account" and page == "account")
            col.button(f"{icon} {label}", key=f"nav_{target}", on_click=go, args=(target,),
                       type="primary" if active else "secondary", width="stretch")


def newsletter():
    with st.container(border=True):
        a, b, c = st.columns([2.2, 2.4, 1], vertical_alignment="center")
        a.markdown("**📬 Join the Willow Club** — early access to new clefts, restocks and member-only offers.")
        email = b.text_input("Email", placeholder="you@example.com", label_visibility="collapsed", key="nl_email")
        if c.button("Subscribe", type="primary", width="stretch", key="nl_btn"):
            if EMAIL_RE.match(email or ""):
                DB["subscribers"].add(email.lower())
                st.toast("You're in! Welcome to the Willow Club. 🏏")
            else:
                st.toast("Please enter a valid email address.", icon="⚠️")


def footer():
    newsletter()
    md(f"""
    <div class="ws-footer">
      <div>
        <div class="ws-logo">🏏 {BRAND_A}<span>{BRAND_B}</span></div>
        <p>Hand-picked English willow cricket bats, pressed and shaped by master bat-makers.
        From Grade 1+ players' bats to junior academy willow.</p>
        <div class="ws-social"><span>Instagram</span><span>YouTube</span><span>Facebook</span><span>X</span>
        <span>LinkedIn</span></div>
      </div>
      <div><div class="ws-h4">Shop</div><ul>
        <li>Titan Series</li><li>Heritage Series</li><li>Storm Series</li><li>Legacy Series</li>
        <li>Club Series</li><li>Academy (Junior)</li></ul></div>
      <div><div class="ws-h4">Help</div><ul>
        <li>Bulk Purchase</li><li>Track Your Order</li><li>Bat Warranty</li><li>Returns &amp; Replacements</li>
        <li>Shipping Policy</li><li>FAQs</li></ul></div>
      <div><div class="ws-h4">Contact</div><ul>
        <li>📞 {SUPPORT_PHONE}</li><li>✉️ {SUPPORT_EMAIL}</li><li>💬 WhatsApp {WHATSAPP}</li>
        <li>🕙 Mon–Sat, 10am – 7pm IST</li></ul></div>
    </div>
    <div class="ws-bottom">
      <span>© {dt.date.today().year} {BRAND}. All rights reserved. Prices in INR (₹), inclusive of GST.</span>
      <span>Terms · Privacy Policy · Shipping · Refunds</span>
    </div>""")


# ════════════════════════════════════════════════════════════════════════════════
#  PRODUCT CARD & OPTIONS DIALOG
# ════════════════════════════════════════════════════════════════════════════════
@st.dialog("Choose your bat", width="large")
def options_dialog(pid: str):
    p = PRODUCT_BY_ID[pid]
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        md(tile_html(p, height=300))
        st.markdown("##### Specifications")
        st.dataframe(pd.DataFrame({
            "Spec": ["Willow", "Grade", "Grains", "Edge", "Spine", "Sweet spot", "Handle"],
            "Value": ["English willow", p["grade"], p["grains"], p["edge"], p["spine"], p["sweet"], p["handle"]],
        }), hide_index=True, width="stretch")
    with right:
        st.subheader(p["name"])
        st.caption(f"{p['series']} Series · SKU {p['id']}")
        md(price_html(p, prefix=False) + stock_html(p))
        st.write(p["desc"])
        size = st.selectbox("Size", p["sizes"], format_func=SIZE_LABEL.get, key=f"dlg_size_{pid}")
        weight = st.selectbox("Weight", p["weights"], index=min(1, len(p["weights"]) - 1), key=f"dlg_weight_{pid}")
        handle = st.radio("Handle shape", ["Round", "Oval"], index=0 if p["handle"] == "Round" else 1,
                          horizontal=True, key=f"dlg_handle_{pid}")
        addons = st.multiselect("Add-ons", list(ADDONS), key=f"dlg_addons_{pid}",
                                format_func=lambda a: f"{a}  (+{inr(ADDONS[a])})")
        qty = st.number_input("Quantity", min_value=1, max_value=9, value=1, step=1, key=f"dlg_qty_{pid}")
        unit = sale_price(p) + sum(ADDONS[a] for a in addons)
        md(f'<div class="ws-total big"><span>Total</span><span>{inr(unit * qty)}</span></div>')
        if st.button("🛒 Add to cart", type="primary", width="stretch", key=f"dlg_add_{pid}"):
            st.session_state.cart.append({
                "uid": secrets.token_hex(4), "pid": pid, "name": p["name"], "size": size,
                "weight": weight.split(" (")[0], "handle": handle, "addons": addons,
                "unit": unit, "qty": int(qty),
            })
            st.session_state.flash = f"Added {p['name']} to your cart."
            st.rerun()
        st.caption(f"Need {BULK_MIN_QTY}+ bats for a team or academy? Use **Bulk Purchase** for extra discounts.")


def product_card(p, ctx: str):
    with st.container(border=True):
        md(tile_html(p))
        st.markdown(f"**{p['name']}**")
        st.caption(f"{p['series']} Series · {p['grains']} grains · {p['sweet']} sweet spot")
        md(price_html(p) + stock_html(p))
        if st.button("Choose options", key=f"{ctx}_{p['id']}", type="primary", width="stretch"):
            options_dialog(p["id"])


def product_grid(items, ncols: int, ctx: str):
    for i in range(0, len(items), ncols):
        cols = st.columns(ncols)
        for col, p in zip(cols, items[i:i + ncols]):
            with col:
                product_card(p, ctx)


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: HOME
# ════════════════════════════════════════════════════════════════════════════════
def page_home():
    md(f"""
    <div class="ws-hero">
      <div>
        <div class="ws-kicker">NEW SEASON · ENGLISH WILLOW</div>
        <div class="ws-h1">Hand-picked English willow.<br>Built to score.</div>
        <p>Grade 1+ to Grade 4 clefts, pressed and shaped by master bat-makers. Pre-knocked options,
        a 1-year bat warranty and free delivery across India.</p>
        <span class="ws-chip">Grade 1+ players' bats</span><span class="ws-chip">Pre-knocked on request</span>
        <span class="ws-chip">Academy &amp; club pricing</span>
      </div>
      <img src="{bat_img('Titan', -38)}" alt="English willow cricket bat">
    </div>""")
    a, b, _ = st.columns([1.25, 1.25, 4])
    a.button("🏏 Shop English Willow", type="primary", width="stretch", on_click=go, args=("shop",), key="hero_shop")
    b.button("📦 Bulk order enquiry", width="stretch", on_click=go, args=("bulk",), key="hero_bulk")

    st.write("")
    trust = [("🚚", "Free delivery", "On every bat, across India"),
             ("🛡️", "1-year bat warranty", "Against manufacturing defects"),
             ("🔨", "Pre-knocked option", "Match-ready out of the box"),
             ("↩️", "7-day returns", "On unused bats")]
    for col, (icon, title, sub) in zip(st.columns(4), trust):
        with col:
            md(f'<div class="ws-trust"><div class="i">{icon}</div><b>{title}</b><small>{sub}</small></div>')

    section("Shop by", "Series", "Six English willow ranges, from players' grade to junior academy bats.")
    names = list(SERIES)
    for row in range(0, len(names), 3):
        for col, name in zip(st.columns(3), names[row:row + 3]):
            s = SERIES[name]
            n = sum(p["series"] == name for p in PRODUCTS)
            with col:
                md(f'<div class="ws-series" style="background:{s["bg"]}"><b>{name.upper()} SERIES</b>'
                   f'<small>{s["tag"]} · {n} bats</small></div>')
                st.button(f"Shop {name} →", key=f"series_{name}", on_click=shop_series, args=(name,),
                          width="stretch")

    section("Featured", "Bats", "Our most-picked English willow this season.")
    featured = [p for p in PRODUCTS if p["badge"] in ("Pro choice", "Bestseller", "New", "Limited")][:4]
    product_grid(featured, 4, "home")
    st.button("View all English willow bats →", on_click=go, args=("shop",), key="home_all")

    md(f"""<div class="ws-band"><div class="ws-h3">📦 Kitting out an academy, school or club?</div>
    <p>Order {BULK_MIN_QTY}+ bats and get an extra 5–15% off, free shipping, team-logo engraving and a
    dedicated account manager.</p></div>""")
    st.button("Build a bulk quote →", type="primary", on_click=go, args=("bulk",), key="home_bulk_band")

    g, t = st.columns([1.35, 1], gap="large")
    with g:
        section("English Willow", "Grade Guide", "Grade describes the look of the willow: grains and blemishes.")
        st.dataframe(GRADE_GUIDE, hide_index=True, width="stretch")
    with t:
        section("What players", "say")
        for who, quote in TESTIMONIALS:
            md(f'<div class="ws-review" style="margin-bottom:10px"><div class="q">“</div>{quote}'
               f'<br><small>— {who}</small></div>')
        st.caption("Sample testimonials (placeholder content for this prototype).")


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: SHOP
# ════════════════════════════════════════════════════════════════════════════════
def page_shop():
    md('<div class="ws-crumb">Home / Cricket Bats / English Willow</div>')
    section("English Willow", "Cricket Bats", "Every bat is graded, pressed and hand-finished. Filter to find yours.")
    fcol, gcol = st.columns([1, 3.2], gap="large")

    with fcol:
        with st.container(border=True):
            st.markdown("**🔍 Filter bats**")
            search = st.text_input("Search", placeholder="e.g. Titan, Grade 1, Storm", key="f_search")
            series = st.multiselect("Series", list(SERIES), key="f_series")
            grades = st.multiselect("Grade", GRADES, key="f_grade")
            sweet = st.multiselect("Sweet spot", ["High", "Mid", "Low"], key="f_sweet")
            lo, hi = st.slider("Price (₹)", PMIN, PMAX, step=500, key="f_price", format="₹%d")
            sort = st.selectbox("Sort by", ["Featured", "Price: low to high", "Price: high to low",
                                            "Biggest discount", "Grade: best first"], key="f_sort")
            st.button("Reset filters", on_click=reset_filters, width="stretch", key="f_reset")
        with st.expander("📏 Size guide"):
            st.dataframe(SIZE_GUIDE, hide_index=True, width="stretch")

    items = [p for p in PRODUCTS
             if (not series or p["series"] in series)
             and (not grades or p["grade"] in grades)
             and (not sweet or p["sweet"] in sweet)
             and lo <= sale_price(p) <= hi
             and (not search or search.lower() in f"{p['name']} {p['series']} {p['grade']}".lower())]
    if sort == "Price: low to high":
        items.sort(key=sale_price)
    elif sort == "Price: high to low":
        items.sort(key=sale_price, reverse=True)
    elif sort == "Biggest discount":
        items.sort(key=lambda p: p["off"], reverse=True)
    elif sort == "Grade: best first":
        items.sort(key=lambda p: GRADES.index(p["grade"]))

    with gcol:
        st.markdown(f"**{len(items)}** English willow bat{'s' if len(items) != 1 else ''} found")
        if items:
            product_grid(items, 3, "shop")
        else:
            st.info("No bats match these filters. Try widening the price range or clearing a filter.")


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: CART & CHECKOUT
# ════════════════════════════════════════════════════════════════════════════════
def coupon_discount(subtotal: float) -> float:
    code = st.session_state.coupon
    if not code:
        return 0
    c = COUPONS[code]
    if subtotal < c["min"]:
        return 0
    return subtotal * c["value"] / 100 if c["type"] == "pct" else c["value"]


def page_cart():
    section("Your", "Cart")
    cart = st.session_state.cart
    if not cart:
        st.info("Your cart is empty. Let's find you a bat! 🏏")
        st.button("Shop English Willow", type="primary", on_click=go, args=("shop",), key="cart_empty_shop")
        return

    items_col, sum_col = st.columns([2.3, 1], gap="large")
    with items_col:
        for item in cart:
            p = PRODUCT_BY_ID[item["pid"]]
            with st.container(border=True):
                img, info, qty_c, tot_c, rm = st.columns([1, 2.6, 1, 1, 0.5], vertical_alignment="center")
                with img:
                    md(tile_html(p, height=96).replace('<div class="ws-badge">', '<div style="display:none">'))
                with info:
                    st.markdown(f"**{item['name']}**")
                    extras = f" · + {', '.join(item['addons'])}" if item["addons"] else ""
                    st.caption(f"{p['grade']} · {SIZE_LABEL[item['size']]} · {item['weight']} · "
                               f"{item['handle']} handle{extras}")
                    st.caption(f"Unit price {inr(item['unit'])}")
                with qty_c:
                    st.number_input("Qty", 1, 9, item["qty"], key=f"q_{item['uid']}", on_change=set_qty, args=(item["uid"],))
                with tot_c:
                    st.markdown(f"**{inr(item['unit'] * item['qty'])}**")
                with rm:
                    st.button("✕", key=f"rm_{item['uid']}", on_click=remove_item, args=(item["uid"],),
                              help="Remove from cart")

    subtotal = sum(i["unit"] * i["qty"] for i in cart)
    mrp_savings = sum((PRODUCT_BY_ID[i["pid"]]["mrp"] - sale_price(PRODUCT_BY_ID[i["pid"]])) * i["qty"] for i in cart)
    discount = coupon_discount(subtotal)

    with sum_col:
        with st.container(border=True):
            st.markdown("#### Order summary")
            c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
            code = c1.text_input("Coupon code", placeholder="Try WILLOW10", key="coupon_in")
            if c2.button("Apply", width="stretch", key="coupon_btn"):
                code = (code or "").strip().upper()
                if code in COUPONS and subtotal >= COUPONS[code]["min"]:
                    st.session_state.coupon = code
                    st.rerun()
                elif code in COUPONS:
                    st.warning(f"{code} needs a cart value of at least {inr(COUPONS[code]['min'])}.")
                else:
                    st.error("That coupon code isn't valid.")
            if st.session_state.coupon:
                st.success(f"**{st.session_state.coupon}** applied: {COUPONS[st.session_state.coupon]['desc']}")
            rows = [("Subtotal", inr(subtotal), "")]
            if discount:
                rows.append((f"Coupon ({st.session_state.coupon})", "−" + inr(discount), "neg"))
            rows.append(("Shipping", "FREE", "neg"))
            md("".join(f'<div class="ws-total"><span>{a}</span><span class="{c}">{b}</span></div>' for a, b, c in rows)
               + f'<div class="ws-total big"><span>Total</span><span>{inr(subtotal - discount)}</span></div>')
            st.caption(f"Inclusive of GST · You save {inr(mrp_savings + discount)} on MRP")
            email, _ = user()
            if email:
                st.button("Proceed to checkout →", type="primary", width="stretch", key="to_checkout",
                          on_click=lambda: st.session_state.update(checkout_open=True))
            else:
                st.button("🔐 Log in to checkout", type="primary", width="stretch", key="login_checkout",
                          on_click=require_login, args=("cart",))
            st.button("← Continue shopping", width="stretch", on_click=go, args=("shop",), key="cart_more")

    email, u = user()
    if email and st.session_state.checkout_open:
        checkout_form(email, u, subtotal - discount)


def checkout_form(email, u, total):
    section("Checkout", "", "Delivery details and payment")
    with st.form("checkout"):
        a, b = st.columns(2)
        name = a.text_input("Full name *", value=u["name"])
        phone = b.text_input("Mobile number *", value=u["phone"], max_chars=10)
        line1 = st.text_input("Address line 1 *", placeholder="House / flat no., street")
        line2 = st.text_input("Address line 2", placeholder="Area, landmark (optional)")
        c, d, e = st.columns(3)
        city = c.text_input("City *")
        state = d.selectbox("State *", STATES, index=STATES.index("Haryana"))
        pin = e.text_input("PIN code *", max_chars=6)
        f, g = st.columns(2)
        delivery = f.radio("Delivery", ["Standard · FREE (4–6 days)", "Express · ₹299 (1–2 days)"])
        payment = g.radio("Payment", ["UPI", "Credit / Debit card", "Net banking", "Cash on delivery"])
        st.caption("You'll be redirected to a secure payment gateway after placing the order (not connected in "
                   "this prototype).")
        submitted = st.form_submit_button("Place order", type="primary", width="stretch")

    if submitted:
        errs = []
        if not name.strip():
            errs.append("Full name is required.")
        if not re.fullmatch(r"[6-9]\d{9}", phone or ""):
            errs.append("Enter a valid 10-digit mobile number.")
        if not line1.strip() or not city.strip():
            errs.append("Address line 1 and city are required.")
        if not re.fullmatch(r"\d{6}", pin or ""):
            errs.append("Enter a valid 6-digit PIN code.")
        if payment == "Cash on delivery" and total > 20000:
            errs.append("Cash on delivery is available for orders up to ₹20,000.")
        if errs:
            for m in errs:
                st.error(m)
            return
        express = delivery.startswith("Express")
        oid = new_id("WS")
        DB["orders"].append({
            "id": oid, "email": email, "date": dt.date.today().isoformat(),
            "items": "; ".join(f"{i['name']} ({i['size']}, {i['weight']}) × {i['qty']}" for i in st.session_state.cart),
            "qty": cart_count(), "total": total + (299 if express else 0), "status": "Order placed",
            "payment": payment, "delivery": "Express" if express else "Standard", "city": city.strip(),
        })
        st.session_state.update(cart=[], coupon=None, checkout_open=False, celebrate=True, page="account",
                                flash=f"🎉 Order {oid} placed! You can track it from My Account or Support.")
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: LOGIN / SIGN-UP
# ════════════════════════════════════════════════════════════════════════════════
def finish_login(email: str):
    st.session_state.user = email
    st.session_state.page = st.session_state.after_login or "account"
    st.session_state.after_login = None
    st.session_state.flash = f"Welcome, {DB['users'][email]['name'].split()[0]}! 👋"
    st.rerun()


def page_login():
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        section("Welcome to", BRAND, "Log in to check out faster, track orders and manage bulk quotes.")
        if st.session_state.after_login:
            st.info("Please log in to continue.")
        tab_in, tab_up = st.tabs(["🔐 Log in", "✨ Create account"])

        with tab_in:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@example.com")
                pw = st.text_input("Password", type="password")
                st.checkbox("Keep me signed in", value=True)
                ok = st.form_submit_button("Log in", type="primary", width="stretch")
            if ok:
                rec = DB["users"].get((email or "").strip().lower())
                if rec and hash_pw(pw, rec["salt"]) == rec["pw"]:
                    finish_login(email.strip().lower())
                else:
                    st.error("Incorrect email or password.")
            st.caption("Demo account: **demo@willowstrike.example** / **demo123**")
            if st.button("Continue with Google", width="stretch", key="google_btn"):
                st.toast("Social login isn't connected in this UI prototype.", icon="ℹ️")
            with st.expander("Forgot password?"):
                fe = st.text_input("Registered email", key="forgot_email")
                if st.button("Send reset link", key="forgot_btn"):
                    if EMAIL_RE.match(fe or ""):
                        st.success(f"If an account exists for {fe}, a reset link is on its way.")
                    else:
                        st.error("Enter a valid email address.")

        with tab_up:
            with st.form("signup_form"):
                name = st.text_input("Full name *")
                a, b = st.columns(2)
                email = a.text_input("Email *")
                phone = b.text_input("Mobile number *", max_chars=10)
                a, b = st.columns(2)
                pw1 = a.text_input("Password * (min. 6 characters)", type="password")
                pw2 = b.text_input("Confirm password *", type="password")
                role = st.selectbox("I am a…", ["Player", "Coach", "Academy / School", "Club", "Retailer"])
                agree = st.checkbox("I agree to the Terms of Use and Privacy Policy")
                ok = st.form_submit_button("Create account", type="primary", width="stretch")
            if ok:
                email = (email or "").strip().lower()
                errs = []
                if len(name.strip()) < 2:
                    errs.append("Please enter your name.")
                if not EMAIL_RE.match(email):
                    errs.append("Enter a valid email address.")
                elif email in DB["users"]:
                    errs.append("An account with this email already exists. Try logging in.")
                if not re.fullmatch(r"[6-9]\d{9}", phone or ""):
                    errs.append("Enter a valid 10-digit mobile number.")
                if len(pw1) < 6:
                    errs.append("Password must be at least 6 characters.")
                elif pw1 != pw2:
                    errs.append("Passwords don't match.")
                if not agree:
                    errs.append("Please accept the terms to continue.")
                if errs:
                    for m in errs:
                        st.error(m)
                else:
                    salt = secrets.token_hex(8)
                    DB["users"][email] = {"name": name.strip(), "phone": phone, "salt": salt,
                                          "pw": hash_pw(pw1, salt), "joined": dt.date.today().isoformat(),
                                          "role": role}
                    finish_login(email)


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: MY ACCOUNT
# ════════════════════════════════════════════════════════════════════════════════
def page_account():
    email, u = user()
    if not email:
        require_login("account")
        st.rerun()
    top, out = st.columns([5, 1], vertical_alignment="bottom")
    with top:
        section("Hi,", u["name"].split()[0], f"{email} · member since {u['joined']}")
    out.button("Log out", on_click=logout, width="stretch", key="logout_btn")

    orders = [o for o in DB["orders"] if o["email"] == email]
    quotes = [q for q in DB["quotes"] if q["email"] == email]
    tickets = [t for t in DB["tickets"] if t["email"] == email]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Orders", len(orders))
    m2.metric("Bulk quotes", len(quotes))
    m3.metric("Support tickets", len(tickets))
    m4.metric("Items in cart", cart_count())

    t_orders, t_quotes, t_tickets, t_profile = st.tabs(["📦 Orders", "🏟️ Bulk quotes", "🎫 Tickets", "⚙️ Profile"])
    with t_orders:
        if orders:
            df = pd.DataFrame(orders)[["id", "date", "items", "total", "status", "delivery", "payment"]]
            df["total"] = df["total"].map(inr)
            df.columns = ["Order ID", "Date", "Items", "Total", "Status", "Delivery", "Payment"]
            st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
            latest = orders[-1]
            st.markdown(f"**Latest order {latest['id']}**")
            md(tracker_html(latest["status"]))
        else:
            st.info("No orders yet.")
            st.button("Start shopping", type="primary", on_click=go, args=("shop",), key="acc_shop")
    with t_quotes:
        if quotes:
            df = pd.DataFrame(quotes)[["id", "date", "org", "qty", "tier", "estimate", "status"]]
            df["estimate"] = df["estimate"].map(inr)
            df.columns = ["Quote ID", "Date", "Organisation", "Bats", "Tier", "Estimate", "Status"]
            st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
        else:
            st.info("No bulk quotes yet.")
            st.button("Build a bulk quote", on_click=go, args=("bulk",), key="acc_bulk")
    with t_tickets:
        if tickets:
            df = pd.DataFrame(tickets)[["id", "date", "category", "subject", "priority", "status"]]
            df.columns = ["Ticket ID", "Date", "Category", "Subject", "Priority", "Status"]
            st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
        else:
            st.info("No support tickets. 🎉")
    with t_profile:
        a, b = st.columns(2, gap="large")
        with a:
            with st.form("profile_form"):
                st.markdown("**Profile details**")
                nm = st.text_input("Full name", value=u["name"])
                ph = st.text_input("Mobile number", value=u["phone"], max_chars=10)
                if st.form_submit_button("Save changes", type="primary"):
                    if nm.strip() and re.fullmatch(r"[6-9]\d{9}", ph or ""):
                        u["name"], u["phone"] = nm.strip(), ph
                        st.success("Profile updated.")
                    else:
                        st.error("Enter a name and a valid 10-digit mobile number.")
        with b:
            with st.form("pw_form", clear_on_submit=True):
                st.markdown("**Change password**")
                cur = st.text_input("Current password", type="password")
                n1 = st.text_input("New password", type="password")
                n2 = st.text_input("Confirm new password", type="password")
                if st.form_submit_button("Update password"):
                    if hash_pw(cur, u["salt"]) != u["pw"]:
                        st.error("Current password is incorrect.")
                    elif len(n1) < 6 or n1 != n2:
                        st.error("New passwords must match and be at least 6 characters.")
                    else:
                        u["salt"] = secrets.token_hex(8)
                        u["pw"] = hash_pw(n1, u["salt"])
                        st.success("Password updated.")


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: BULK PURCHASE
# ════════════════════════════════════════════════════════════════════════════════
def bulk_tier(qty: int):
    for min_q, disc, name in BULK_TIERS:
        if qty >= min_q:
            return name, disc
    return None, 0.0


def page_bulk():
    md(f"""<div class="ws-band" style="padding:30px 32px">
    <div class="ws-kicker">BULK PURCHASE · B2B</div>
    <div class="ws-h3" style="font-size:1.9rem">English willow for academies, schools, clubs &amp; corporates</div>
    <p>Minimum order {BULK_MIN_QTY} bats · extra 5–15% off sale prices · free shipping · GST invoice ·
    team branding · dedicated account manager.</p></div>""")

    tiers = [(f"{BULK_MIN_QTY}–24 bats", "Bronze", "5%"), ("25–49 bats", "Silver", "8%"),
             ("50–99 bats", "Gold", "12%"), ("100+ bats", "Platinum", "15%")]
    for col, (rng, name, pct) in zip(st.columns(4), tiers):
        with col:
            md(f'<div class="ws-trust"><div class="i">🏅</div><b>{name} · extra {pct} off</b><small>{rng}</small></div>')

    left, right = st.columns([2.1, 1], gap="large")
    with left:
        section("1. Choose", "bats", "Add a row per model / size / weight. Use the + at the bottom to add rows.")
        edited = st.data_editor(
            st.session_state.bulk_df, key="bulk_editor", num_rows="dynamic", hide_index=True, width="stretch",
            column_config={
                "Bat model": st.column_config.SelectboxColumn(
                    "Bat model", options=[p["name"] for p in PRODUCTS], required=True, width="large"),
                "Size": st.column_config.SelectboxColumn(
                    "Size", options=SENIOR_SIZES + JUNIOR_SIZES[:3], required=True),
                "Weight": st.column_config.SelectboxColumn(
                    "Weight", options=["Light", "Medium", "Heavy", "Standard (junior)"], required=True),
                "Qty": st.column_config.NumberColumn("Qty", min_value=1, max_value=2000, step=1, required=True),
            },
        )
        rows = edited.dropna(subset=["Bat model", "Qty"])
        rows = rows[rows["Bat model"].isin(PRODUCT_BY_NAME.keys())]
        lines = []
        for _, r in rows.iterrows():
            p = PRODUCT_BY_NAME[r["Bat model"]]
            q = int(r["Qty"])
            if q > 0:
                lines.append({"Bat model": p["name"], "Grade": p["grade"], "Size": r["Size"] if pd.notna(r["Size"]) else "SH",
                              "Weight": r["Weight"] if pd.notna(r["Weight"]) else "Medium", "Qty": q, "Unit (sale)": sale_price(p),
                              "Line total": sale_price(p) * q})
        if lines:
            view = pd.DataFrame(lines)
            view["Unit (sale)"] = view["Unit (sale)"].map(inr)
            view["Line total"] = view["Line total"].map(inr)
            st.dataframe(view, hide_index=True, width="stretch")

        section("2. Team", "customisation", "Optional. Priced per bat across the whole order.")
        a, b = st.columns(2)
        chosen = []
        for i, (opt, cost) in enumerate(BULK_CUSTOM.items()):
            if (a if i % 2 == 0 else b).checkbox(f"{opt} (+{inr(cost)}/bat)", key=f"bc_{i}"):
                chosen.append(opt)
        c, d = st.columns(2)
        grip = c.selectbox("Grip colour", ["Black", "Red", "Navy", "White", "Team colours (add in notes)"])
        sticker = d.selectbox("Sticker colourway", ["Standard series colours", "Team colours (add in notes)",
                                                    "Monochrome"])
        logo = None
        if any(k in chosen for k in ("Team logo laser engraving", "Custom sticker design (min. 25 bats)",
                                      "Padded bat cover with team logo")):
            logo = st.file_uploader("Upload your team logo (PNG, JPG, SVG or PDF)", type=["png", "jpg", "jpeg",
                                                                                          "svg", "pdf"])

    total_qty = sum(l["Qty"] for l in lines)
    subtotal = sum(l["Line total"] for l in lines)
    tier, disc = bulk_tier(total_qty)
    bulk_off = subtotal * disc
    custom_cost = sum(BULK_CUSTOM[c] for c in chosen) * total_qty
    estimate = subtotal - bulk_off + custom_cost
    mrp_total = sum(PRODUCT_BY_NAME[l["Bat model"]]["mrp"] * l["Qty"] for l in lines)

    with right:
        st.write("")
        with st.container(border=True):
            st.markdown("#### 🧾 Live quote")
            st.metric("Total bats", total_qty, help=f"Minimum {BULK_MIN_QTY} bats for bulk pricing")
            if tier:
                st.success(f"**{tier} tier** unlocked: extra {int(disc * 100)}% off")
            else:
                st.warning(f"Add {max(0, BULK_MIN_QTY - total_qty)} more bat(s) to unlock bulk pricing.")
            nxt = next(((m, d, n) for m, d, n in reversed(BULK_TIERS) if total_qty < m), None)
            if nxt and tier:
                st.caption(f"Add {nxt[0] - total_qty} more for {nxt[2]} ({int(nxt[1] * 100)}% off).")
            rows_html = [("MRP value", inr(mrp_total), ""), ("Sale price subtotal", inr(subtotal), "")]
            if bulk_off:
                rows_html.append((f"Bulk discount ({int(disc * 100)}%)", "−" + inr(bulk_off), "neg"))
            if custom_cost:
                rows_html.append(("Customisation", inr(custom_cost), ""))
            rows_html.append(("Shipping", "FREE", "neg"))
            md("".join(f'<div class="ws-total"><span>{x}</span><span class="{c}">{y}</span></div>'
                       for x, y, c in rows_html)
               + f'<div class="ws-total big"><span>Estimate</span><span>{inr(estimate)}</span></div>')
            if total_qty:
                st.caption(f"≈ {inr(estimate / total_qty)} per bat · incl. GST · final quote within 24 hrs")

    with left:
        section("3. Organisation", "details", "We'll email a formal quotation and proforma invoice.")
        email, u = user()
        with st.form("bulk_form"):
            a, b = st.columns(2)
            org_type = a.selectbox("Organisation type *", ["Cricket academy", "School / college", "Club",
                                                           "Corporate team", "Retailer / reseller", "Other"])
            org = b.text_input("Organisation name *")
            a, b, c = st.columns(3)
            contact = a.text_input("Contact person *", value=u["name"] if u else "")
            em = b.text_input("Email *", value=email or "")
            ph = c.text_input("Mobile *", value=u["phone"] if u else "", max_chars=10)
            a, b, c = st.columns(3)
            city = a.text_input("Delivery city *")
            gstin = b.text_input("GSTIN (optional)", max_chars=15)
            need_by = c.date_input("Required by", value=dt.date.today() + dt.timedelta(days=21),
                                   min_value=dt.date.today() + dt.timedelta(days=7))
            notes = st.text_area("Notes", placeholder="Team colours, player names, delivery instructions…")
            sent = st.form_submit_button("📨 Request bulk quote", type="primary", width="stretch")
        if not email:
            st.caption("Tip: log in before submitting to track this quote under **My Account**.")

    if sent:
        errs = []
        if total_qty < BULK_MIN_QTY:
            errs.append(f"Bulk orders need at least {BULK_MIN_QTY} bats (you have {total_qty}).")
        if "Custom sticker design (min. 25 bats)" in chosen and total_qty < 25:
            errs.append("Custom sticker design needs a minimum of 25 bats.")
        if not org.strip() or not contact.strip() or not city.strip():
            errs.append("Organisation name, contact person and city are required.")
        if not EMAIL_RE.match(em or ""):
            errs.append("Enter a valid email address.")
        if not re.fullmatch(r"[6-9]\d{9}", ph or ""):
            errs.append("Enter a valid 10-digit mobile number.")
        if gstin and not re.fullmatch(r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]", gstin.upper()):
            errs.append("GSTIN format looks incorrect (e.g. 06ABCDE1234F1Z5).")
        with left:
            if errs:
                for m in errs:
                    st.error(m)
            else:
                qid = new_id("BQ", 5)
                DB["quotes"].append({
                    "id": qid, "email": email or em.strip().lower(), "date": dt.date.today().isoformat(),
                    "org": org.strip(), "org_type": org_type, "contact": contact.strip(), "phone": ph,
                    "city": city.strip(), "gstin": gstin.upper(), "need_by": need_by.isoformat(),
                    "lines": lines, "custom": chosen, "grip": grip, "sticker": sticker,
                    "logo": logo.name if logo else None, "qty": total_qty, "tier": tier,
                    "estimate": round(estimate), "notes": notes, "status": "Under review",
                })
                st.success(f"✅ Quote request **{qid}** received for {total_qty} bats (estimate {inr(estimate)}). "
                           f"Our bulk team will email {em} within 24 hours.")
                st.balloons()


# ════════════════════════════════════════════════════════════════════════════════
#  PAGE: CUSTOMER SUPPORT
# ════════════════════════════════════════════════════════════════════════════════
def tracker_html(status: str) -> str:
    idx = ORDER_STEPS.index(status) if status in ORDER_STEPS else 0
    parts = []
    for i, s in enumerate(ORDER_STEPS):
        done = "done" if i <= idx else ""
        if i:
            parts.append(f'<div class="ws-line {"done" if i <= idx else ""}"></div>')
        parts.append(f'<div class="ws-step"><div class="ws-dot {done}">{"✓" if i <= idx else i + 1}</div>'
                     f'<div class="l">{s}</div></div>')
    return f'<div class="ws-track">{"".join(parts)}</div>'


def page_support():
    section("Customer", "Support", "Real cricketers, ready to help: sizing, grades, orders, warranty and more.")
    contacts = [("📞", "Call us", SUPPORT_PHONE, "Mon–Sat, 10am–7pm"),
                ("✉️", "Email", SUPPORT_EMAIL, "Replies within 24 hrs"),
                ("💬", "WhatsApp", WHATSAPP, "Quick queries & photos"),
                ("🏬", "Bat-fitting", "Book a video call", "Find your perfect pick-up")]
    for col, (i, t, v, s) in zip(st.columns(4), contacts):
        with col:
            md(f'<div class="ws-contact"><div class="i">{i}</div><b>{t}</b><br>{v}<br><small>{s}</small></div>')
    st.write("")

    email, u = user()
    t_chat, t_ticket, t_track, t_faq, t_policy, t_mine = st.tabs(
        ["💬 Chat with us", "🎫 Raise a ticket", "📦 Track order", "❓ FAQs", "🛡️ Warranty & returns",
         "📋 My tickets"])

    with t_chat:
        box = st.container(height=380, border=True)
        with box:
            for m in st.session_state.chat:
                with st.chat_message(m["role"], avatar="🏏" if m["role"] == "assistant" else "🧑"):
                    st.markdown(m["content"])
        quick = ["Which size do I need?", "Shipping time", "Bat warranty", "Knocking-in", "Bulk orders"]
        for col, q in zip(st.columns(len(quick)), quick):
            col.button(q, key=f"qk_{q}", on_click=ask_bot, args=(q,), width="stretch")
        prompt = st.chat_input("Ask about sizes, grades, shipping, warranty…", key="chat_in")
        if prompt:
            ask_bot(prompt)
            st.rerun()

    with t_ticket:
        with st.form("ticket_form"):
            a, b = st.columns(2)
            name = a.text_input("Name *", value=u["name"] if u else "")
            em = b.text_input("Email *", value=email or "")
            a, b, c = st.columns(3)
            cat = a.selectbox("Category *", ["Order issue", "Warranty claim", "Return / Replacement",
                                             "Product / sizing query", "Bulk order", "Payment / refund", "Other"])
            oid = b.text_input("Order ID (if any)", placeholder="WS-100245")
            prio = c.selectbox("Priority", ["Normal", "High", "Urgent"])
            subj = st.text_input("Subject *")
            desc = st.text_area("Describe the issue *", height=120)
            photos = st.file_uploader("Attach photos (for warranty / damage claims)", type=["png", "jpg", "jpeg"],
                                      accept_multiple_files=True)
            sent = st.form_submit_button("Submit ticket", type="primary", width="stretch")
        if sent:
            errs = []
            if not name.strip() or not subj.strip() or len(desc.strip()) < 10:
                errs.append("Name, subject and a short description (10+ characters) are required.")
            if not EMAIL_RE.match(em or ""):
                errs.append("Enter a valid email address.")
            if cat == "Warranty claim" and not photos:
                errs.append("Warranty claims need at least one photo of the bat.")
            if errs:
                for m in errs:
                    st.error(m)
            else:
                tid = new_id("TKT", 5)
                DB["tickets"].append({
                    "id": tid, "email": email or em.strip().lower(), "name": name.strip(),
                    "date": dt.date.today().isoformat(), "category": cat, "order_id": oid.strip().upper(),
                    "priority": prio, "subject": subj.strip(), "desc": desc.strip(),
                    "photos": [p.name for p in photos or []], "status": "Open",
                })
                st.session_state.my_tickets.append(tid)
                st.success(f"🎫 Ticket **{tid}** created. We'll reply to {em} within 24 hours"
                           f"{' (urgent tickets within 4 hours)' if prio == 'Urgent' else ''}.")

    with t_track:
        a, b = st.columns([3, 1], vertical_alignment="bottom")
        oid = a.text_input("Order ID", placeholder="e.g. WS-100245", key="track_id")
        b.button("Track", type="primary", width="stretch", key="track_btn")
        st.caption("Try the sample order **WS-100245**.")
        if oid:
            order = next((o for o in DB["orders"] if o["id"].upper() == oid.strip().upper()), None)
            if order:
                st.markdown(f"**{order['id']}** · placed {order['date']} · {order['delivery']} delivery to "
                            f"{order['city']}")
                st.caption(order["items"])
                md(tracker_html(order["status"]))
                st.info(f"Current status: **{order['status']}**")
            else:
                st.error("We couldn't find that order ID. Check the confirmation email or raise a ticket.")

    with t_faq:
        for q, a in FAQS:
            with st.expander(q):
                st.write(a)
        st.markdown("##### 📏 Bat size guide")
        st.dataframe(SIZE_GUIDE, hide_index=True, width="stretch")
        st.markdown("##### 🌳 Grade guide")
        st.dataframe(GRADE_GUIDE, hide_index=True, width="stretch")

    with t_policy:
        a, b = st.columns(2, gap="large")
        with a:
            st.markdown("""
**🛡️ 1-year limited bat warranty**
- Covers manufacturing defects: handle failure, splits along the grain, splice issues
- Not covered: surface cracks, toe damage from moisture or yorkers, use with cheap or wet balls, misuse
- Bats must be knocked-in and oiled as recommended
- Claim by raising a **Warranty claim** ticket with photos of the face, back, edges and toe
""")
        with b:
            st.markdown("""
**↩️ Returns & replacements**
- Unused bats can be returned within **7 days** of delivery
- Stickers intact, not knocked-in, oiled or used
- Engraved or customised bats are non-returnable
- Refunds go to the original payment method within 5–7 working days
- Damaged in transit? Report within 48 hours with unboxing photos
""")

    with t_mine:
        mine = [t for t in DB["tickets"] if (email and t["email"] == email) or t["id"] in st.session_state.my_tickets]
        if mine:
            df = pd.DataFrame(mine)[["id", "date", "category", "subject", "priority", "status"]]
            df.columns = ["Ticket ID", "Date", "Category", "Subject", "Priority", "Status"]
            st.dataframe(df.iloc[::-1], hide_index=True, width="stretch")
        else:
            st.info("You haven't raised any tickets yet." if email else
                    "Log in to see all your tickets, or raise one in the 'Raise a ticket' tab.")


# ════════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ════════════════════════════════════════════════════════════════════════════════
PAGES = {
    "home": page_home, "shop": page_shop, "bulk": page_bulk, "support": page_support,
    "cart": page_cart, "login": page_login, "account": page_account,
}


def main():
    md(CSS)
    init_state()
    if st.session_state.flash:
        st.toast(st.session_state.flash)
        st.session_state.flash = None
    if st.session_state.celebrate:
        st.balloons()
        st.session_state.celebrate = False
    header()
    PAGES.get(st.session_state.page, page_home)()
    footer()


main()
