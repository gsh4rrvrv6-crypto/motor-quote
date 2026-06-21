import streamlit as st
import pandas as pd
import json
import os
import uuid
from datetime import date, datetime
from collections import Counter

st.set_page_config(
    page_title="Motor Quote Comparison",
    page_icon="🚗",
    layout="wide"
)

def fmt_date(d):
    """Format a date object or string as DD/MM/YY."""
    if isinstance(d, date):
        return d.strftime("%d/%m/%y")
    return str(d) if d else ""

def today_str():
    return date.today().strftime("%d/%m/%y")

# The underwriter behind each brand — the company that holds the risk and pays claims
UNDERWRITERS = {
    "GIO": "AAI Limited (Suncorp Group)",
    "AAMI": "AAI Limited (Suncorp Group)",
    "Suncorp": "AAI Limited (Suncorp Group)",
    "APIA": "AAI Limited (Suncorp Group)",
    "Shannons": "AAI Limited (Suncorp Group)",
    "Bingle": "AAI Limited (Suncorp Group)",
    "NRMA": "Insurance Australia Group (IAG)",
    "ROLLiN'": "Insurance Australia Group (IAG)",
    "WFI": "Insurance Australia Group (IAG)",
    "RACQ": "Insurance Australia Group (IAG)",
    "BOQ": "Insurance Australia Group (IAG)",
    "RACV": "Insurance Manufacturers of Australia (IAG/RACV JV)",
    "ANZ": "CGU (IAG)",
    "Bendigo Bank": "CGU (IAG)",
    "Budget Direct": "Auto & General",
    "Qantas": "Auto & General",
    "Coles": "Auto & General",
    "ING": "Auto & General",
    "Australia Post": "Auto & General",
    "Kogan": "Auto & General",
    "Woolworths": "Hollard",
    "Real Insurance": "Hollard",
    "Australian Seniors": "Hollard",
    "CBA": "Hollard",
    "Huddle": "Hollard",
    "Ozicare": "Hollard",
    "TrueCover": "Hollard",
    "Everyday": "Hollard",
    "Allianz": "Allianz",
    "Westpac": "Allianz",
    "St.George": "Allianz",
    "BankSA": "Allianz",
    "Bank of Melbourne": "Allianz",
    "NAB": "Allianz",
    "HSBC": "Allianz",
    "TIO": "Allianz",
    "RAA": "Allianz",
    "Beyond Bank": "Allianz",
    "QBE": "QBE",
    "Stella": "QBE",
    "Elders": "QBE",
    "ALDI": "RACQ Insurance (via Honey)",
    "KOBA": "Pacific International Insurance",
    "RAC": "RAC Insurance (WA)",
    "RACT": "RACT Insurance",
    "Bupa": "Bupa",
    "BMW": "Allianz",
    "Mercedes-Benz": "Allianz",
    "Australian Unity": "Australian Unity",
    "ahm": "Medibank / ahm",
    "Over Fifty": "Hollard",
    "pd.com.au": "pd.com.au",
    "UbiCar": "UbiCar",
    "Carpeesh": "Carpeesh",
    "Blue Badge": "Blue Badge Insurance",
    "National Seniors": "Hollard",
    "Ryno": "Ryno Insurance",
    "Hume": "Hume Bank",
    "Club 4x4": "Club 4x4",
}

# AFCA complaints received per underwriter group — FY2024-25 Datacube
# NOTE: counts largely reflect company size, not service quality. Update annually.
AFCA_COMPLAINTS = {
    "AAI Limited (Suncorp Group)": "5,343 (down from 5,883)",
    "Insurance Australia Group (IAG)": "3,444 (down from 3,592)",
    "CGU (IAG)": "3,444 (IAG group total)",
    "Allianz": "1,625 (down from 1,736)",
    "QBE": "1,588 (down from 1,619)",
    "RACQ Insurance": "1,075 (up from 888)",
    "RACQ Insurance (via Honey)": "1,075 (RACQ group total)",
    "Auto & General": "3,032 (up from 2,940)",
}

# Platform mapping for smart batching (same-platform insurers are grouped together)
PLATFORMS = {
    "AAI / Suncorp": ["GIO", "AAMI", "Suncorp", "APIA", "Bingle", "Shannons"],
    "IAG": ["NRMA", "ROLLiN'", "WFI"],
    "Auto & General": ["Budget Direct", "Qantas", "Coles", "ING"],
    "Allianz": ["Allianz", "Westpac", "St.George", "NAB", "HSBC", "TIO"],
    "Hollard": ["Woolworths", "Real Insurance", "Australian Seniors", "CBA", "Huddle"],
    "QBE": ["QBE", "Stella", "Elders"],
    "CGU / IAG": ["ANZ", "Bendigo Bank"],
    "RACQ": ["RACQ", "BOQ", "ALDI"],
    "Other": ["KOBA", "RACV", "RAA", "RAC", "RACT"],
}

def build_context(v, d):
    """Build the vehicle/driver context string from session state dicts."""
    vehicle_str = f"{v.get('year','')} {v.get('make','')} {v.get('model','')} {v.get('variant','')}".strip()
    usage_str = ", ".join(v.get("usage", [])) if v.get("usage") else "Private"
    overnight_addr = f"{v.get('overnight_address','')} {v.get('overnight_suburb','')} {v.get('overnight_postcode','')}".strip()
    day_addr = f"{v.get('day_suburb','')} {v.get('day_postcode','')}".strip()
    d2_block = ""
    if d.get("d2_name"):
        d2_block = f"\n- Additional driver: {d.get('d2_name','')}, DOB {d.get('d2_dob','')}, {d.get('d2_gender','')}, {d.get('d2_licence','Full Australian')} licence, claims: {d.get('d2_claims','None')}"
    return f"""Vehicle: {vehicle_str}
Registration state: {v.get('rego_state','NSW')}
Registration number: {v.get('rego','')}
Cover type: {v.get('cover_type','Comprehensive')}
Sum insured: {v.get('sum_insured','Market Value')}
Annual kilometres: {v.get('annual_kms','')}
Overnight parking: {overnight_addr}
Daytime parking: {day_addr}
Usage: {usage_str}
Financed: {v.get('finance','No')}
Policy start date: {v.get('start_date','')}
Basic excess: ${v.get('excess',500)}
Previous insurer: {v.get('previous_insurer','')}
Main driver: {d.get('d1_name','')}, DOB {d.get('d1_dob','')}, {d.get('d1_gender','')}, {d.get('d1_licence','Full Australian')} licence, claims: {d.get('d1_claims','None')}{d2_block}"""
INSURER_INFO = {
    "GIO": ("https://www.gio.com.au/car-insurance.html", "Same platform as AAMI"),
    "AAMI": ("https://www.aami.com.au/car-insurance/get-quote.html", ""),
    "NRMA": ("https://www.nrma.com.au/car-insurance", "Quote portal opens in a new tab at insurance.nrma.com.au — click 'Continue without logging in'"),
    "Budget Direct": ("https://www.budgetdirect.com.au/car-insurance/get-quote.html", "Asks for overnight address BEFORE rego lookup — this is normal"),
    "Allianz": ("https://www.allianz.com.au/car-insurance/", ""),
    "QBE": ("https://www.qbe.com/au/car-insurance", ""),
    "Suncorp": ("https://www.suncorp.com.au/insurance/car.html", "Same platform family as GIO/AAMI"),
    "APIA": ("https://www.apia.com.au/car-insurance.html", "Designed for over-50s — if age eligibility blocks the quote, note it and skip"),
    "Shannons": ("https://www.shannons.com.au/request-a-quote/", "Enthusiast insurer — may hand off to a consultant; submit and note 'callback requested'"),
    "Qantas": ("https://insurance.qantas.com/car-insurance", "Same platform as Budget Direct — overnight address comes first; skip Frequent Flyer number"),
    "Coles": ("https://www.coles.com.au/insurance/car-insurance", "Same platform as Budget Direct; 15% online discount should apply — skip Flybuys number"),
    "Woolworths": ("https://insurance.woolworths.com.au/car-insurance.html", "Skip Everyday Rewards number"),
    "Real Insurance": ("https://www.realinsurance.com.au/car-insurance", "If annual kms are under 15,000 also note the Pay As You Drive price"),
    "Bingle": ("https://www.bingle.com.au", "Short stripped-back quote flow"),
    "ROLLiN'": ("https://www.rollininsurance.com.au", "Prices monthly — report monthly AND annual equivalent (monthly x 12)"),
    "Huddle": ("https://www.huddle.com.au/car-insurance", ""),
    "ALDI": ("https://www.aldiinsurance.com.au/car/", "Comprehensive only — no third party options, no roadside add-on"),
    "ING": ("https://www.ing.com.au/insurance/car-insurance.html", "Same platform as Budget Direct — do not log in"),
    "CBA": ("https://www.commbank.com.au/insurance/car-insurance.html", "Use the guest quote option — do NOT log in to NetBank"),
    "Australian Seniors": ("https://www.seniors.com.au/car-insurance", "Designed for over-50s — if age eligibility blocks the quote, note it and skip"),
    "Stella": ("https://www.stellainsurance.com.au", "Comprehensive only; doesn't cover all postcodes — if blocked, note it and skip"),
    "KOBA": ("https://www.kobainsurance.com.au", "Pay-per-km — report upfront cost, per-km rate AND the annual estimate"),
    "TIO": ("https://www.tiofi.com.au", "NT vehicles only — if blocked, note it and skip"),
    "WFI": ("https://www.wfi.com.au/quotes", "Callback model — submit the request form, note 'callback requested'"),
    "Elders": ("https://www.eldersinsurance.com.au/personal-insurance/car", "Callback model — submit the request form, note 'callback requested'"),
    "Westpac": ("https://www.westpac.com.au/personal-banking/insurance/car-insurance/", "Quote as guest — do not log in"),
    "St.George": ("https://www.stgeorge.com.au/personal/insurance/car-insurance", "Quote as guest — same Allianz product as Westpac"),
    "NAB": ("https://www.nab.com.au/personal/insurance/car", "Quote as guest; ~10% online discount should apply"),
    "ANZ": ("https://www.anz.com.au/personal/insurance/car-insurance/", "Quote as guest"),
    "Bendigo Bank": ("https://www.bendigobank.com.au/personal/insurance/car/", "Not available for VIC-garaged vehicles — if blocked, note it and skip"),
    "BOQ": ("https://www.boq.com.au/personal/insurance/", "Comprehensive only; portal may open at insurance.boq.com.au"),
    "HSBC": ("https://www.hsbc.com.au/insurance/products/car/", "Quote as guest; ~10% online discount should apply"),
    "RAA": ("https://www.raa.com.au/insurance/car-insurance", "SA vehicles only — skip membership number; if blocked, note and skip"),
    "RAC": ("https://rac.com.au/car-motorcycle/car-insurance", "WA vehicles only — skip membership number; if blocked, note and skip"),
    "RACV": ("https://www.racv.com.au/insurance/car-insurance.html", "VIC vehicles only — skip membership number; if blocked, note and skip"),
    "RACQ": ("https://www.racq.com.au/insurance/car-insurance", "QLD vehicles only — skip membership number; if blocked, note and skip"),
    "RACT": ("https://www.ract.com.au/insurance/car-insurance", "TAS vehicles only — skip membership number; if blocked, note and skip"),
    "Australia Post": ("https://auspost.com.au/insurance/car-insurance", "Underwritten by Auto & General — may redirect to Budget Direct platform"),
    "Kogan": ("https://www.kogan.com/au/insurance/car-insurance/", "Underwritten by Auto & General"),
    "Bupa": ("https://www.bupa.com.au/car-insurance", "May no longer offer new car insurance policies — if blocked, note and skip"),
    "BMW": ("https://www.bmwfinance.com.au/insurance", "Dealer insurance underwritten by Allianz"),
    "Mercedes-Benz": ("https://www.mercedes-benzfinancialservices.com.au/insurance", "Dealer insurance underwritten by Allianz"),
    "Australian Unity": ("https://www.australianunity.com.au/insurance/car-insurance", ""),
    "ahm": ("https://www.ahm.com.au/car-insurance", "Part of Medibank group"),
    "Ozicare": ("https://www.ozicare.com.au/car-insurance", "Underwritten by Hollard"),
    "TrueCover": ("https://www.truecover.com.au/car-insurance", "Underwritten by Hollard"),
    "Over Fifty": ("https://www.overfifty.com.au/car-insurance", "Designed for over-50s; underwritten by Hollard"),
    "Everyday": ("https://www.everyday.com.au/car-insurance", "Underwritten by Hollard"),
    "pd.com.au": ("https://www.pd.com.au/car-insurance", ""),
    "UbiCar": ("https://www.ubicar.com.au", "Pay-how-you-drive insurer — may have limited availability"),
    "Carpeesh": ("https://www.carpeesh.com.au", ""),
    "Beyond Bank": ("https://www.beyondbank.com.au/insurance/car-insurance.html", "Underwritten by Allianz"),
    "Blue Badge": ("https://www.bluebadgeinsurance.com.au", "Disability insurance specialist"),
    "National Seniors": ("https://nationalseniors.com.au/services/insurance/car-insurance", "Underwritten by Hollard"),
    "Ryno": ("https://www.rynoinsurance.com.au", "Specialist vehicle insurer"),
    "Hume": ("https://www.humebank.com.au/insurance/car-insurance", ""),
    "Club 4x4": ("https://www.club4x4.com.au", "4WD and off-road vehicle specialist"),
}

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size:2rem; font-weight:700; color:#1a1a2e; margin-bottom:0.2rem; }
    .sub-header { color:#666; font-size:0.95rem; margin-bottom:2rem; }
    .section-title { font-size:1.1rem; font-weight:600; color:#1a1a2e; padding-bottom:6px; margin-bottom:1rem; }
    .quote-card { background:#f8f9ff; border:1px solid #e0e4ff; border-radius:12px; padding:1.2rem; margin-bottom:1rem; }
    .best-value { background:#f0fff4; border:2px solid #48bb78; border-radius:12px; padding:1.2rem; margin-bottom:1rem; }
    .badge-best { background:#48bb78; color:white; font-size:0.7rem; font-weight:700; padding:2px 8px; border-radius:20px; text-transform:uppercase; letter-spacing:0.5px; }
    .price-big { font-size:1.8rem; font-weight:700; color:#1a1a2e; }
    .price-sub { font-size:0.85rem; color:#666; }
    .stButton > button { background-color:#1a1a2e; color:white; border:none; border-radius:8px; padding:0.5rem 1.5rem; font-weight:600; }
    .stButton > button:hover { background-color:#2d2d4e; }
    .date-hint { font-size:0.75rem; color:#999; margin-top:-12px; margin-bottom:8px; }
    .brand-card {
        border-radius:8px; padding:10px 6px; text-align:center; font-weight:700;
        height:40px; display:flex; align-items:center; justify-content:center;
        margin-bottom:6px;
    }
    .brand-off { background:#f0f0f0; color:#333; }
    .brand-on { color:#fff; }
    .brand-label { font-size:0.65rem; color:#888; font-weight:400; margin-top:2px; }
    /* Make checkbox fill entire card area — whole tile is the button */
    [data-testid="stCheckbox"] { margin-bottom:-48px; position:relative; z-index:10; opacity:0; height:40px !important; min-height:40px !important; max-height:40px !important; overflow:hidden; }
    [data-testid="stCheckbox"] label { cursor:pointer; height:40px !important; width:100% !important; display:block !important; position:absolute; top:0; left:0; right:0; bottom:0; }
    [data-testid="stCheckbox"] label span { font-size:0 !important; line-height:0 !important; width:100% !important; display:block !important; height:100% !important; }
    [data-testid="stCheckbox"] label svg { display:none !important; }
    [data-testid="stCheckbox"] label > div:first-child { display:none !important; }
    [data-testid="stCheckbox"] label > div { width:100% !important; height:100% !important; }
    [data-testid="stCheckbox"] > div { width:100% !important; height:100% !important; }
    /* Force every column element to uniform size */
    [data-testid="stColumn"] > div { padding-top:0 !important; }
    [data-testid="stColumn"] [data-testid="stCheckbox"] + div { margin-top:0 !important; padding-top:0 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding:0 !important; }
    [data-testid="stColumn"] [data-testid="element-container"] { margin:0 !important; padding:0 !important; }
    /* Group title spacing — closer to tiles below */
    .group-label { font-size:1.44rem; color:#999; margin-top:28px; margin-bottom:8px; padding:0; line-height:1; font-weight:700; }
    /* Force all columns to align content to top */
    [data-testid="stHorizontalBlock"] { align-items:flex-start !important; }
    [data-testid="stColumn"] { vertical-align:top !important; }
    /* Remove extra bottom space in tabs */
    [data-testid="stTabPanel"] { padding-bottom:0 !important; }
    [data-testid="stTabPanel"] > div { padding-bottom:0 !important; }
    [data-testid="stVerticalBlock"] { gap:0.5rem !important; }
    .main .block-container { padding-bottom:0 !important; }
    /* Remove horizontal lines above footer */
    [data-testid="stTabPanel"] hr { display:none !important; }
    footer { display:none !important; }
    footer hr { display:none !important; }
    footer::before { display:none !important; }
    [data-testid="stBottom"] { display:none !important; }
    [data-testid="stBottomBlockContainer"] { display:none !important; }
    #MainMenu { display:none !important; }
    header [data-testid="stToolbar"] { display:none !important; }
    [data-testid="stHeader"] { display:none !important; height:0 !important; }
    [data-testid="stAppViewBlockContainer"], .main .block-container { padding-top:1rem !important; padding-bottom:1rem !important; }
    .stApp [data-testid="stMainBlockContainer"] { padding-top:1rem !important; padding-bottom:1rem !important; }
    [data-testid="stBottomBlockContainer"] { display:none !important; height:0 !important; min-height:0 !important; }
    [data-testid="stBottom"] { display:none !important; height:0 !important; min-height:0 !important; }
    section[data-testid="stMain"] { padding-bottom:0 !important; }
    [data-testid="stStatusWidget"] { display:none !important; }
    [data-testid="manage-app-button"] { display:none !important; }
    .stAppDeployButton { display:none !important; }
</style>
""", unsafe_allow_html=True)

# Brand colours for visual cards
BRAND_COLORS = {
    "GIO": ("#003DA5", "#fff"), "AAMI": ("#E31937", "#fff"), "SUNCORP": ("#009FE3", "#fff"),
    "NRMA": ("#003DA5", "#fff"), "BUDGET DIRECT": ("#00A651", "#fff"), "ALLIANZ": ("#003781", "#fff"),
    "QBE": ("#003DA5", "#fff"), "APIA": ("#6B2D6B", "#fff"), "BINGLE": ("#FF6600", "#fff"),
    "SHANNONS": ("#1B3D6F", "#fff"), "ROLLIN'": ("#FF3366", "#fff"), "HUDDLE": ("#4A90D9", "#fff"),
    "ALDI": ("#00205B", "#fff"), "KOBA": ("#2DD4BF", "#1a1a2e"), "STELLA": ("#D4458B", "#fff"),
    "QANTAS": ("#E0001B", "#fff"), "COLES": ("#E01A2B", "#fff"), "WOOLWORTHS": ("#125B1E", "#fff"),
    "REAL INSURANCE": ("#0066CC", "#fff"), "ING": ("#FF6200", "#fff"), "CBA": ("#FFCC00", "#1a1a2e"),
    "AUSTRALIAN SENIORS": ("#1B6F5F", "#fff"), "WESTPAC": ("#DA1710", "#fff"),
    "ST.GEORGE": ("#00823B", "#fff"), "NAB": ("#C8102E", "#fff"), "ANZ": ("#007DBA", "#fff"),
    "BENDIGO BANK": ("#B5121B", "#fff"), "BOQ": ("#004B87", "#fff"), "HSBC": ("#DB0011", "#fff"),
    "TIO": ("#003781", "#fff"), "WFI": ("#1B5E20", "#fff"), "ELDERS": ("#D32F2F", "#fff"),
    "RAA": ("#FFB300", "#1a1a2e"), "RAC": ("#0057B8", "#fff"), "RACV": ("#003DA5", "#fff"),
    "RACQ": ("#FFB300", "#1a1a2e"), "RACT": ("#00529B", "#fff"), "BANKSA": ("#00457C", "#fff"),
    "BANK OF MELBOURNE": ("#6E1E6E", "#fff"),
    "AUSTRALIA POST": ("#DC2626", "#fff"), "KOGAN": ("#FFD700", "#1a1a2e"),
    "BUPA": ("#00A3E0", "#fff"), "BMW": ("#1C69D3", "#fff"), "MERCEDES-BENZ": ("#1A1A1A", "#fff"),
    "AUSTRALIAN UNITY": ("#00594C", "#fff"), "AHM": ("#E84393", "#fff"),
    "OZICARE": ("#2E86C1", "#fff"), "TRUECOVER": ("#27AE60", "#fff"),
    "OVER FIFTY": ("#5B2C6F", "#fff"), "EVERYDAY": ("#28B463", "#fff"),
    "PD.COM.AU": ("#E67E22", "#fff"), "UBICAR": ("#3498DB", "#fff"),
    "CARPEESH": ("#1ABC9C", "#fff"), "BEYOND BANK": ("#004D40", "#fff"),
    "BLUE BADGE": ("#1565C0", "#fff"), "NATIONAL SENIORS": ("#0D47A1", "#fff"),
    "RYNO": ("#E74C3C", "#fff"), "HUME": ("#388E3C", "#fff"), "CLUB 4X4": ("#4E342E", "#fff"),
}

# ── Session state init ────────────────────────────────────────────────────────
if "quotes" not in st.session_state:
    st.session_state.quotes = []
if "vehicle" not in st.session_state:
    st.session_state.vehicle = {}
if "drivers" not in st.session_state:
    st.session_state.drivers = {}
if "selected_insurers" not in st.session_state:
    st.session_state.selected_insurers = set()

# ── Cross-session quote sync (lets batch runs deliver quotes automatically) ──
SYNC_DIR = "/tmp/mqc_sync"
os.makedirs(SYNC_DIR, exist_ok=True)

def _sync_path(code):
    return os.path.join(SYNC_DIR, f"{code}.json")

def sync_write(code, new_quotes):
    try:
        existing = []
        if os.path.exists(_sync_path(code)):
            with open(_sync_path(code)) as f:
                existing = json.load(f)
        existing.extend(new_quotes)
        with open(_sync_path(code), "w") as f:
            json.dump(existing, f, default=str)
    except Exception:
        pass

def sync_pull(code):
    try:
        if os.path.exists(_sync_path(code)):
            with open(_sync_path(code)) as f:
                return json.load(f)
    except Exception:
        pass
    return []

def quote_fp(q):
    return (q.get("insurer"), q.get("annual_premium"), q.get("quote_ref"))

def quote_flags(q, target_excess=None):
    """Sanity checks on a quote — returns a list of warnings worth reviewing."""
    flags = []
    ap = q.get("annual_premium", 0) or 0
    if 0 < ap < 300:
        flags.append("Premium unusually low — double-check the amount")
    elif ap > 5000:
        flags.append("Premium unusually high — double-check the amount")
    ex = q.get("excess", 0) or 0
    if not ex:
        flags.append("No excess recorded")
    elif target_excess and abs(ex - int(target_excess)) >= 50:
        flags.append(f"Excess ${ex:,} differs from your target ${int(target_excess):,} — not a like-for-like comparison")
    return flags

def _detect_app_url():
    try:
        host = st.context.headers.get("host", "")
        if host and "localhost" not in host and "0.0.0.0" not in host:
            return f"https://{host}"
    except Exception:
        pass
    return ""

qp_sync = st.query_params.get("sync", "")
if "sync_code" not in st.session_state:
    st.session_state.sync_code = qp_sync or uuid.uuid4().hex[:6].upper()
elif qp_sync and st.session_state.sync_code != qp_sync:
    st.session_state.sync_code = qp_sync

if "imported_fps" not in st.session_state:
    st.session_state.imported_fps = {quote_fp(q) for q in st.session_state.quotes}

_new_synced = 0
for _q in sync_pull(st.session_state.sync_code):
    if quote_fp(_q) not in st.session_state.imported_fps:
        st.session_state.quotes.append(_q)
        st.session_state.imported_fps.add(quote_fp(_q))
        _new_synced += 1
if _new_synced:
    st.toast(f"🔄 {_new_synced} new quote{'s' if _new_synced != 1 else ''} synced in from your batch runs")

# ── Sticky top bar CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .sticky-bar { position:sticky; top:0; z-index:999; background:white; padding:6px 0 8px 0;
                  border-bottom:1px solid #e8e8e8; margin-bottom:12px; }
    /* Freeze save/upload row at top */
    [data-testid="stMainBlockContainer"] > div:first-child { position:sticky; top:0; z-index:998; background:white; padding-bottom:4px; border-bottom:1px solid #eee; }
    /* Selectbox selected option — charcoal */
    [data-testid="stSelectbox"] [data-baseweb="select"] { color:#333 !important; }
    /* Hide file uploader helper text and grey box */
    [data-testid="stFileUploader"] section > div:last-child { display:none !important; }
    [data-testid="stFileUploader"] small { display:none !important; }
    [data-testid="stFileUploader"] section { border:none !important; padding:0 !important; background:none !important; }
    [data-testid="stFileUploader"] section > div { background:none !important; border:none !important; }
    [data-testid="stFileUploader"] { background:none !important; }
    [data-testid="stFileUploader"] section > button span { font-size:0 !important; line-height:0 !important; }
    [data-testid="stFileUploader"] section > button::before { content:"📂 Upload previous session"; font-size:0.85rem; font-weight:600; }
    [data-testid="stFileUploader"] section > button {
        background:#f8f9fa !important; color:#333 !important; border:1px solid #ddd !important;
        border-radius:8px !important; font-weight:600 !important; font-size:0.85rem !important;
        padding:0.4rem 1rem !important; width:100% !important;
    }
    [data-testid="stFileUploader"] section > button:hover {
        background:#e9ecef !important; border-color:#ccc !important;
    }
    /* Consistent save/restore button style */
    .session-bar button, .session-bar [data-testid="stDownloadButton"] button {
        background:#f8f9fa !important; color:#333 !important; border:1px solid #ddd !important;
        border-radius:8px !important; font-weight:600 !important; font-size:0.85rem !important;
        padding:0.4rem 1rem !important; height:42px !important; min-width:120px !important;
    }
    .session-bar button:hover, .session-bar [data-testid="stDownloadButton"] button:hover {
        background:#e9ecef !important; border-color:#ccc !important;
    }
    /* Uniform save/upload/restore button sizing */
    [data-testid="stDownloadButton"] button,
    [data-testid="stFileUploader"] section > button,
    [data-testid="stBaseButton-secondary"] {
        height:42px !important; min-width:120px !important; width:100% !important;
        padding:0.4rem 1rem !important; font-size:0.85rem !important;
        background:#f8f9fa !important; color:#333 !important;
        border:1px solid #ddd !important; border-radius:8px !important; font-weight:600 !important;
    }
    [data-testid="stDownloadButton"] button:hover,
    [data-testid="stFileUploader"] section > button:hover,
    [data-testid="stBaseButton-secondary"]:hover {
        background:#e9ecef !important; border-color:#ccc !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Session save / restore (top bar) ─────────────────────────────────────────
session_data = {
    "vehicle": st.session_state.vehicle,
    "drivers": st.session_state.drivers,
    "quotes": st.session_state.quotes,
    "selected_insurers": sorted(st.session_state.selected_insurers),
}
col_save, col_restore_file, col_restore_btn = st.columns([1, 1, 1])
with col_save:
    st.download_button(
        "💾 Save",
        data=json.dumps(session_data, indent=2, default=str),
        file_name=f"motor_quotes_{date.today().strftime('%d%m%y')}.json",
        mime="application/json",
        width="stretch",
    )
with col_restore_file:
    restore_file = st.file_uploader("Restore", type=["json"], key="restore_upload", label_visibility="collapsed")
with col_restore_btn:
    if restore_file is not None and st.button("↩️ Restore", width="stretch"):
        try:
            data = json.loads(restore_file.read().decode("utf-8"))
            st.session_state.vehicle = data.get("vehicle", {})
            st.session_state.drivers = data.get("drivers", {})
            st.session_state.quotes = data.get("quotes", [])
            restored_sel = set(data.get("selected_insurers", []))
            st.session_state.selected_insurers = restored_sel
            for k in list(st.session_state.keys()):
                if k.startswith("sel_"):
                    st.session_state[k] = k[4:] in restored_sel
            for ins in restored_sel:
                st.session_state[f"sel_{ins}"] = True
            st.session_state.imported_fps = {quote_fp(q) for q in st.session_state.quotes}
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't read that file: {e}")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🚗 Motor Quote Comparison</div>', unsafe_allow_html=True)

_DISCLAIMER = '<div style="font-size:0.7rem;color:#aaa;margin-top:2rem;padding-top:0.5rem">⚠️ This tool is for comparison purposes only and does not constitute financial advice. Always read the Product Disclosure Statement (PDS) before making a decision. Consider seeking independent financial advice.</div><div style="height:2.5rem"></div>'

tab_help, tab1, tab2, tab3 = st.tabs(["📖 Instructions", "📋 Vehicle & Drivers", "📝 Enter Quotes", "📊 Compare"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 0 — Instructions
# ════════════════════════════════════════════════════════════════════════════
with tab_help:
    st.markdown('<div class="section-title" style="margin-top:1.5rem">What You Need</div>', unsafe_allow_html=True)
    st.markdown("""
- A **paid Claude account** — sign up at [claude.ai](https://claude.ai)
- The **[Claude in Chrome extension](https://chromewebstore.google.com/detail/claude-ai/ppmhkbzfgnlphjgaaomgfnkknhijaggh)** — this is what lets Claude fill in forms in your browser
""")


    st.markdown('<div class="section-title" style="margin-top:1.5rem">Step by Step</div>', unsafe_allow_html=True)

    st.markdown('**1.** Right click on this tab and select "Add Tab to New Group"')
    st.markdown("**2.** Open **[claude.ai](https://claude.ai)**")

    # Reserve space for steps 3-7 (filled after grid renders so selection is current)
    steps_placeholder = st.container()

    # ── Insurer selection grid (grouped by underwriter, row-aligned) ──────────
    st.markdown('<div class="section-title" style="margin-top:1.5rem">Select Your Insurers</div>', unsafe_allow_html=True)

    insurer_groups_ordered = [
        ("Suncorp Group", ["GIO", "AAMI", "Suncorp", "APIA", "Bingle"]),
        ("IAG", ["NRMA", "RACV", "ANZ", "Bendigo Bank", "RACQ", "BOQ", "ROLLiN'"]),
        ("Allianz", ["Allianz", "Westpac", "St.George", "BankSA", "NAB", "HSBC", "TIO",
                     "Beyond Bank", "BMW", "Mercedes-Benz", "RAA"]),
        ("QBE", ["QBE", "Stella"]),
        ("Auto & General", ["Budget Direct", "Qantas", "Coles", "ING", "Australia Post", "Kogan"]),
        ("Hollard", ["Real Insurance", "Woolworths", "Australian Seniors", "CBA", "Huddle",
                     "Ozicare", "TrueCover", "Everyday", "Over Fifty", "National Seniors"]),
        ("Other", ["ALDI", "Bupa", "Australian Unity", "ahm", "pd.com.au", "UbiCar", "Carpeesh",
                   "Blue Badge", "Ryno", "Hume", "Club 4x4", "RAC", "RACT", "KOBA"]),
    ]

    all_selectable_insurers = []
    for _, members in insurer_groups_ordered:
        all_selectable_insurers.extend(members)

    n_cols = 7
    SELECTION_CAP = 10
    for group_name, group_insurers in insurer_groups_ordered:
        st.markdown(f'<div class="group-label">{group_name}</div>', unsafe_allow_html=True)
        for row_start in range(0, len(group_insurers), n_cols):
            row_slice = group_insurers[row_start:row_start + n_cols]
            cols = st.columns(n_cols)
            for col_idx in range(n_cols):
                with cols[col_idx]:
                    if col_idx < len(row_slice):
                        ins = row_slice[col_idx]
                        bg, _ = BRAND_COLORS.get(ins.upper(), ("#666", "#fff"))
                        is_selected = st.checkbox(
                            ins, key=f"sel_{ins}",
                            value=ins in st.session_state.selected_insurers
                        )
                        if is_selected:
                            # Enforce the cap — only add if under the limit or already in
                            if ins in st.session_state.selected_insurers or len(st.session_state.selected_insurers) < SELECTION_CAP:
                                st.session_state.selected_insurers.add(ins)
                                show_on = True
                            else:
                                # At cap — don't add; tile shows as off even though box is ticked
                                show_on = False
                        else:
                            st.session_state.selected_insurers.discard(ins)
                            show_on = False
                        fsize = "0.68rem" if len(ins) > 14 else ("0.72rem" if len(ins) > 10 else ("0.78rem" if len(ins) > 7 else "0.85rem"))
                        if show_on:
                            st.markdown(f'<div class="brand-card brand-on" style="background:{bg};font-size:{fsize}">{ins}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="brand-card brand-off" style="font-size:{fsize}">{ins}</div>', unsafe_allow_html=True)
                    else:
                        pass

    if len(st.session_state.selected_insurers) >= SELECTION_CAP:
        st.caption(f"⚠️ Maximum of {SELECTION_CAP} insurers reached — deselect one to choose another.")

    st.markdown("<div style='margin-top:1.5rem'></div>", unsafe_allow_html=True)
    st.caption("Youi, Shannons, WFI and Elders are not included — these brands require you to get a quote over the phone.")

    # ── Prompts (always visible, built from current selection) ──────────────
    n_selected = len(st.session_state.selected_insurers)

    master_app_url = _detect_app_url()
    master_sync_url = (f"{master_app_url}/?sync={st.session_state.sync_code}"
                       if master_app_url else "the Motor Quote Comparison app tab")

    # Build ordered insurer list — all in one batch (max 10)
    ordered_selected = []
    for platform, members in PLATFORMS.items():
        for m in members:
            if m in st.session_state.selected_insurers and m not in ordered_selected:
                ordered_selected.append(m)
    for s in st.session_state.selected_insurers:
        if s not in ordered_selected:
            ordered_selected.append(s)

    batches = [ordered_selected] if ordered_selected else []

    # ── Vehicle & Drivers data (filled by the prefill prompt) ────────────
    v = st.session_state.vehicle
    d = st.session_state.drivers

    # ── Prefill prompt (sidebar — reads docs, fills Vehicle & Drivers tab) ─
    prefill_prompt = f"""Using the Claude in Chrome extension, fill in my vehicle and driver details.

STEP 1 — GET MY DETAILS FROM THE CLAUDE CHAT
My vehicle and driver details have already been extracted and are listed in the main Claude chat conversation open in this same browser window (the regular claude.ai tab, not this sidebar). Read them from there. The details include: vehicle year, make, model, variant, colour, years owned, odometer reading, rego number + state, cover type, sum insured (Market/Agreed), annual kms, overnight street address + suburb + postcode, basic excess, current insurer, main driver name/DOB(DD/MM/YY)/gender, and any additional driver. If you can't find them in the chat, tell me and stop — do not guess.

STEP 2 — FILL THE APP
Go to: {master_sync_url}
Click the "Vehicle & Drivers" tab. Type each detail into the matching field. For dropdowns, pick the closest option. Leave anything missing blank. The details save automatically.

When done, tell me the tab is filled so I can check it, then run the quote prompt."""

    # ── Quote prompt (sidebar — reads filled tab, quotes insurers) ───────
    import base64 as _b64
    _prefill_b64 = _b64.b64encode(prefill_prompt.encode()).decode()

    batch_prompts = []
    for batch_idx, batch in enumerate(batches):
        batch_lines = []
        for i, ins in enumerate(batch, 1):
            if ins in INSURER_INFO:
                url, note = INSURER_INFO[ins]
                note_str = f" — {note}" if note else ""
                batch_lines.append(f"{i}. {ins}: {url}{note_str}")
        batch_list = "\n".join(batch_lines)

        bp = f"""Using the Claude in Chrome extension, get car insurance quotes for me.

STEP 1 — READ MY DETAILS FROM THE APP
Go to: {master_sync_url}
Click the "Vehicle & Drivers" tab. Read ALL the form field values (year, make, model, variant, colour, years owned, odometer, rego, state, cover type, sum insured, annual kms, overnight address/suburb/postcode, daytime suburb/postcode, usage, excess, start date, previous insurer, driver names/DOBs/genders). These are my details — use them for every insurer quote below.

STEP 2 — QUOTE INSURERS (go straight through without pausing)
IMPORTANT: Open each insurer's website in a NEW TAB. Do NOT navigate away from the Motor Quote Comparison app tab — keep it open separately throughout.

Rules: If any Chrome extension permission prompts appear, click "Always allow this site". Address = full street, suburb, state, postcode — select from dropdown. Market Value. Modifications: None. Claims: None in 3 years. Guest/no login. ALWAYS select the ANNUAL payment option (not monthly) so the premium is the total yearly cost. If blocked, note reason, skip, next.

{batch_list}

STEP 3 — ENTER RESULTS
After all done, go back to: {master_sync_url}
"Enter Quotes" tab → paste into "Quick Add" box:
Insurer: <name> | Annual: $<amount> | Monthly: $<amount or n/a> | Excess: $<amount> | Ref: <ref> | Inclusions: <list> | Notes: <notes>
Click "Parse & Add Quotes". Go."""
        batch_prompts.append((_b64.b64encode(bp.encode()).decode(), ", ".join(batch), len(batch)))

    # ── Extract prompt (main chat — reads docs, lists details) ───────────
    extract_prompt = """I've attached my motor insurance renewal notice and/or certificate of insurance. Read them and list these details exactly as shown below so they're available for the next step:

Vehicle year:
Vehicle make:
Vehicle model:
Vehicle variant:
Vehicle colour:
Years owned:
Odometer reading (km):
Rego number:
Rego state:
Cover type:
Sum insured:
Annual kms:
Overnight street address:
Overnight suburb:
Overnight postcode:
Basic excess:
Current insurer:
Current renewal premium (annual $):
Current renewal excess:
Main driver name:
Main driver DOB (DD/MM/YY):
Main driver gender:
Additional driver name:
Additional driver DOB (DD/MM/YY):
Additional driver gender:

Fill in each line. Write "not found" for anything missing."""
    _extract_b64 = _b64.b64encode(extract_prompt.encode()).decode()

    # ── Steps (Option 1: extract in main chat → sidebar reads chat) ───────
    steps_placeholder.markdown(f'**3.** IDrag and drop your renewal notice and certificate of insurance, paste the <a href="data:text/plain;base64,{_extract_b64}" download="extract_prompt.txt">extract prompt</a>, and press run', unsafe_allow_html=True)
    steps_placeholder.markdown("**4.** Click the **Claude in Chrome extension icon** at the top right of the screen to open the Claude sidebar")
    steps_placeholder.markdown("<div style='margin-left:1.8rem;font-size:0.82rem;color:#888'>⚙️ At the top of the sidebar panel, select versions of Sonnet for best results</div>", unsafe_allow_html=True)
    steps_placeholder.markdown("<div style='margin-left:1.8rem;font-size:0.82rem;color:#888'>⚙️ At the bottom of the sidebar panel, select \"act without asking\" so Claude runs through without stopping for confirmation</div>", unsafe_allow_html=True)
    steps_placeholder.markdown(f'**5.** In the sidebar, paste the <a href="data:text/plain;base64,{_prefill_b64}" download="prefill_prompt.txt">prefill prompt</a> and press run — Claude reads the details from the chat and fills the Vehicle & Drivers tab', unsafe_allow_html=True)
    steps_placeholder.markdown("**6.** Check the **Vehicle & Drivers** tab — edit anything that's wrong or incomplete")
    steps_placeholder.markdown("**7.** Select the brands you want to quote — lower down on this page — note 2-3 selections at a time is best")

    if batch_prompts:
        b64, names, count = batch_prompts[0]
        steps_placeholder.markdown(f'**8.** Back in the sidebar, paste the <a href="data:text/plain;base64,{b64}" download="quote_prompt.txt">quote prompt</a> and press run — Claude reads your details and quotes each insurer', unsafe_allow_html=True)
    else:
        steps_placeholder.markdown("**8.** Back in the sidebar, paste the quote prompt and press run *(select brands below first)*")
    steps_placeholder.markdown("<div style='margin-left:1.8rem;font-size:0.82rem;color:#888'>💡 The extension will ask permission for each insurer website — always click \"Always allow this site\" to keep it running smoothly</div>", unsafe_allow_html=True)
    steps_placeholder.markdown("**9.** Claude quotes each insurer automatically")
    steps_placeholder.markdown("**10.** Results appear in the Compare tab")

    if n_selected > 0:
        steps_placeholder.info(f"✅ {n_selected} insurer{'s' if n_selected != 1 else ''} selected — estimated run time roughly {n_selected * 4}–{n_selected * 8} minutes")

    st.markdown(_DISCLAIMER, unsafe_allow_html=True)

# TAB 1 — Vehicle & Drivers
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">Vehicle Details</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.number_input("Year", min_value=1990, max_value=2030,
                               value=st.session_state.vehicle.get("year", 2020), step=1)
        make = st.text_input("Make", value=st.session_state.vehicle.get("make", ""))
        model = st.text_input("Model", value=st.session_state.vehicle.get("model", ""))
        colour = st.text_input("Colour", value=st.session_state.vehicle.get("colour", ""))
    with col2:
        variant = st.text_input("Variant / Series", value=st.session_state.vehicle.get("variant", ""))
        rego = st.text_input("Registration Number", value=st.session_state.vehicle.get("rego", ""))
        rego_state = st.selectbox("Rego State",
                                  ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                                  index=["NSW","VIC","QLD","WA","SA","TAS","ACT","NT"].index(
                                      st.session_state.vehicle.get("rego_state", "NSW")))
        ownership_years = st.number_input("Years Owned", min_value=0, max_value=50,
                                          value=st.session_state.vehicle.get("ownership_years", 0), step=1)
    with col3:
        cover_type = st.selectbox("Cover Type",
                                  ["Comprehensive", "Third Party Fire & Theft", "Third Party Only"],
                                  index=["Comprehensive","Third Party Fire & Theft","Third Party Only"].index(
                                      st.session_state.vehicle.get("cover_type", "Comprehensive")))
        sum_insured = st.selectbox("Sum Insured Type", ["Market Value", "Agreed Value"],
                                   index=["Market Value","Agreed Value"].index(
                                       st.session_state.vehicle.get("sum_insured", "Market Value")))
        annual_kms = st.selectbox("Annual Kilometres",
                                  ["Under 10,000", "10,000 – 15,000", "15,000 – 20,000",
                                   "20,000 – 25,000", "Over 25,000"],
                                  index=["Under 10,000","10,000 – 15,000","15,000 – 20,000",
                                         "20,000 – 25,000","Over 25,000"].index(
                                      st.session_state.vehicle.get("annual_kms", "15,000 – 20,000")))
        odometer = st.number_input("Odometer Reading (km)", min_value=0, max_value=1000000,
                                   value=st.session_state.vehicle.get("odometer", 0), step=1000)

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Parking & Usage</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        overnight_address = st.text_input("Overnight Street Address", value=st.session_state.vehicle.get("overnight_address", ""))
        overnight_suburb = st.text_input("Overnight Parking Suburb", value=st.session_state.vehicle.get("overnight_suburb", ""))
        overnight_postcode = st.text_input("Overnight Postcode", value=st.session_state.vehicle.get("overnight_postcode", ""))
    with col2:
        day_suburb = st.text_input("Daytime Parking Suburb", value=st.session_state.vehicle.get("day_suburb", ""))
        day_postcode = st.text_input("Daytime Postcode", value=st.session_state.vehicle.get("day_postcode", ""))
    with col3:
        usage = st.selectbox("Vehicle Usage", ["Private", "Public"],
                              index=["Private", "Public"].index(
                                  st.session_state.vehicle.get("usage", "Private") if isinstance(st.session_state.vehicle.get("usage"), str) else "Private"))
        finance = st.selectbox("Financed?", ["No", "Yes"],
                               index=["No","Yes"].index(st.session_state.vehicle.get("finance", "No")))

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Policy Details</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.text_input("Policy Start Date (DD/MM/YY)",
                                   value=st.session_state.vehicle.get("start_date", today_str()))
        previous_insurer = st.text_input("Current / Previous Insurer", value=st.session_state.vehicle.get("previous_insurer", ""))
    with col2:
        excess = st.number_input("Basic Excess ($)", min_value=0, max_value=5000,
                                 value=st.session_state.vehicle.get("excess", 500), step=50)
        renewal_premium = st.number_input("Current Renewal Premium ($/yr)", min_value=0, max_value=20000,
                                          value=st.session_state.vehicle.get("renewal_premium", 0), step=10,
                                          help="The annual premium on your renewal notice — shown as a baseline to compare new quotes against")
    with col3:
        renewal_excess = st.number_input("Current Renewal Excess ($)", min_value=0, max_value=5000,
                                         value=st.session_state.vehicle.get("renewal_excess", 0), step=50,
                                         help="The excess on your current renewal notice")

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Drivers</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Main Driver**")
        d1_name = st.text_input("Name", key="d1_name", value=st.session_state.drivers.get("d1_name", ""))
        d1_dob = st.text_input("Date of Birth (DD/MM/YY)", key="d1_dob",
                               value=st.session_state.drivers.get("d1_dob", ""))
        d1_gender = st.selectbox("Gender", ["Female", "Male", "Other"], key="d1_gender",
                                 index=["Female","Male","Other"].index(
                                     st.session_state.drivers.get("d1_gender", "Female")))
        d1_licence = st.selectbox("Licence Type",
                                  ["Full Australian", "Learner", "Provisional P1", "Provisional P2", "International"],
                                  key="d1_licence",
                                  index=["Full Australian","Learner","Provisional P1","Provisional P2","International"].index(
                                      st.session_state.drivers.get("d1_licence", "Full Australian")))
        d1_claims = st.selectbox("Claims in last 3 years", ["None", "1", "2", "3+"], key="d1_claims",
                                 index=["None","1","2","3+"].index(
                                     st.session_state.drivers.get("d1_claims", "None")))

    with col2:
        st.markdown("**Additional Driver** *(optional)*")
        d2_name = st.text_input("Name", key="d2_name", value=st.session_state.drivers.get("d2_name", ""))
        d2_dob = st.text_input("Date of Birth (DD/MM/YY)", key="d2_dob",
                               value=st.session_state.drivers.get("d2_dob", ""))
        d2_gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="d2_gender",
                                 index=["Male","Female","Other"].index(
                                     st.session_state.drivers.get("d2_gender", "Male")))
        d2_licence = st.selectbox("Licence Type",
                                  ["Full Australian", "Learner", "Provisional P1", "Provisional P2", "International"],
                                  key="d2_licence",
                                  index=["Full Australian","Learner","Provisional P1","Provisional P2","International"].index(
                                      st.session_state.drivers.get("d2_licence", "Full Australian")))
        d2_claims = st.selectbox("Claims in last 3 years", ["None", "1", "2", "3+"], key="d2_claims",
                                 index=["None","1","2","3+"].index(
                                     st.session_state.drivers.get("d2_claims", "None")))

    # Auto-save vehicle and driver details
    st.session_state.vehicle = {
        "year": year, "make": make, "model": model, "variant": variant,
        "colour": colour, "ownership_years": ownership_years, "odometer": odometer,
        "rego": rego, "rego_state": rego_state, "cover_type": cover_type,
        "sum_insured": sum_insured, "annual_kms": annual_kms,
        "overnight_address": overnight_address, "overnight_suburb": overnight_suburb, "overnight_postcode": overnight_postcode,
        "day_suburb": day_suburb, "day_postcode": day_postcode,
        "usage": usage, "finance": finance,
        "start_date": start_date, "previous_insurer": previous_insurer,
        "excess": excess,
        "renewal_premium": renewal_premium, "renewal_excess": renewal_excess
    }
    st.session_state.drivers = {
        "d1_name": d1_name, "d1_dob": d1_dob, "d1_gender": d1_gender,
        "d1_licence": d1_licence, "d1_claims": d1_claims,
        "d2_name": d2_name, "d2_dob": d2_dob, "d2_gender": d2_gender,
        "d2_licence": d2_licence, "d2_claims": d2_claims,
    }
    st.caption("💾 Details are saved automatically")
    st.markdown(_DISCLAIMER, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add Quotes
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    insurers = ["GIO", "AAMI", "NRMA", "Budget Direct", "Allianz",
                "QBE", "Suncorp", "APIA", "Shannons", "Qantas", "Coles",
                "Woolworths", "Real Insurance", "Bingle", "ROLLiN'", "Huddle",
                "ALDI", "ING", "CBA", "Australian Seniors",
                "Stella", "KOBA", "TIO", "WFI", "Elders", "Westpac", "St.George", "BankSA",
                "Bank of Melbourne", "NAB", "ANZ", "Bendigo Bank", "BOQ", "HSBC",
                "RAA", "RAC", "RACV", "RACQ", "RACT",
                "Australia Post", "Kogan", "Bupa", "BMW", "Mercedes-Benz",
                "Australian Unity", "ahm", "Ozicare", "TrueCover", "Over Fifty",
                "Everyday", "pd.com.au", "UbiCar", "Carpeesh", "Beyond Bank",
                "Blue Badge", "National Seniors", "Ryno", "Hume", "Club 4x4", "Other"]

    # ── Quick add: paste results from Claude ─────────────────────────────────
    st.markdown('<div class="section-title">⚡ Quick Add — Paste Results from Claude</div>', unsafe_allow_html=True)
    st.caption("Paste the RESULTS summaries from your Get Quotes batch runs — each line is parsed and added automatically.")

    paste_text = st.text_area(
        "Paste results here:",
        height=120,
        key="paste_results",
        placeholder="Insurer: AAMI | Annual: $842.50 | Monthly: $74.20 | Excess: $750 | Ref: Q12345 | Inclusions: roadside, windscreen | Rating: 4.5 | Notes: online discount applied",
        label_visibility="collapsed",
    )

    def _money(s):
        try:
            return float(s.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            return 0.0

    if st.button("➕ Parse & Add Quotes", width="stretch", key="parse_add"):
        added, failed, new_quotes = [], [], []
        for line in paste_text.splitlines():
            line = line.strip().lstrip("-•*").strip()
            if "insurer" not in line.lower() or "|" not in line:
                continue
            try:
                fields = {}
                for part in line.split("|"):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        fields[k.strip().lower()] = v.strip()
                name = fields.get("insurer", "")
                match = next((i for i in insurers if i.lower() == name.lower()), name)
                annual = _money(fields.get("annual", "0"))
                if not match or annual <= 0:
                    failed.append(line[:60])
                    continue
                monthly_raw = fields.get("monthly", "")
                monthly = 0.0 if "n/a" in monthly_raw.lower() else _money(monthly_raw)
                inc = fields.get("inclusions", "").lower()
                rating_raw = fields.get("rating", "")
                try:
                    rating_val = float(rating_raw.replace("/5", "").replace("stars", "").strip())
                    rating_val = rating_val if 0 < rating_val <= 5 else None
                except (ValueError, AttributeError):
                    rating_val = None
                q = {
                    "insurer": match,
                    "annual_premium": annual,
                    "monthly_premium": monthly,
                    "excess": int(_money(fields.get("excess", "0"))),
                    "cover": "Comprehensive",
                    "sum_type": "Market Value",
                    "quote_ref": fields.get("ref", ""),
                    "valid_until": today_str(),
                    "roadside": "roadside" in inc,
                    "hire_car": "hire" in inc,
                    "windscreen": "windscreen" in inc,
                    "no_claims": "ncd" in inc or "no claims" in inc,
                    "online_discount": "online" in inc,
                    "rating": rating_val,
                    "notes": fields.get("notes", ""),
                }
                if quote_fp(q) not in st.session_state.imported_fps:
                    st.session_state.quotes.append(q)
                    st.session_state.imported_fps.add(quote_fp(q))
                    new_quotes.append(q)
                added.append(match)
            except Exception:
                failed.append(line[:60])
        if new_quotes:
            sync_write(st.session_state.sync_code, new_quotes)
        if added:
            st.success(f"✅ Added {len(added)} quote{'s' if len(added) != 1 else ''}: {', '.join(added)} — see the **Compare** tab.")
            checks = []
            for nq in new_quotes:
                nflags = quote_flags(nq, st.session_state.vehicle.get("excess"))
                if nflags:
                    checks.append(f"**{nq['insurer']}** — {'; '.join(nflags)}")
            if checks:
                st.warning("⚠️ Worth checking: " + " · ".join(checks))
        if failed:
            st.warning(f"⚠️ Couldn't parse {len(failed)} line{'s' if len(failed) != 1 else ''}: " + "; ".join(failed))
        if not added and not failed:
            st.info("No result lines found — each line needs to start with 'Insurer:' and use | separators.")

    col_r1, col_r2 = st.columns([1, 3])
    with col_r1:
        st.button("🔄 Refresh", key="refresh_quotes", width="stretch")
    with col_r2:
        st.caption("Batch runs deliver quotes here automatically — hit Refresh if you're waiting on one.")

    if st.session_state.quotes:
        st.markdown('<div class="section-title" style="margin-top:2rem">Quotes Entered</div>', unsafe_allow_html=True)
        for i, q in enumerate(st.session_state.quotes):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{q['insurer']}**  `{q['quote_ref']}`")
            with col2:
                st.markdown(f"${q['annual_premium']:,.2f} / year")
            with col3:
                st.markdown(f"Excess: ${q['excess']:,}")
            with col4:
                if st.button("🗑", key=f"del_{i}", help="Remove this quote"):
                    st.session_state.quotes.pop(i)
                    st.rerun()

    st.markdown(_DISCLAIMER, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Compare
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.quotes:
        st.info("💡 No quotes yet — add some in the **Enter Quotes** tab first.")
    else:
        quotes = st.session_state.quotes
        sorted_quotes = sorted(quotes, key=lambda x: x["annual_premium"])
        best = sorted_quotes[0]
        v = st.session_state.vehicle
        target_excess = v.get("excess") if v else None

        if v:
            vehicle_str = f"{v.get('year','')} {v.get('make','')} {v.get('model','')} {v.get('variant','')}".strip()
            st.markdown(
                f"<div style='background:#f0f4ff;border-radius:10px;padding:0.8rem 1.2rem;"
                f"margin-bottom:1.5rem;font-size:0.9rem;color:#333'>"
                f"🚗 <strong>{vehicle_str}</strong> &nbsp;·&nbsp; "
                f"{v.get('cover_type','Comprehensive')} &nbsp;·&nbsp; "
                f"{v.get('sum_insured','Market Value')} &nbsp;·&nbsp; "
                f"Start: {v.get('start_date', '—')}"
                f"</div>",
                unsafe_allow_html=True
            )

        prices = [q["annual_premium"] for q in quotes]
        renewal_premium = v.get("renewal_premium", 0) if v else 0
        renewal_excess = v.get("renewal_excess", 0) if v else 0
        renewal_insurer = v.get("previous_insurer", "") if v else ""

        if renewal_premium and renewal_premium > 0:
            # Renewal is the baseline — saving = renewal minus cheapest new quote
            saving = renewal_premium - min(prices)
            renewal_label = renewal_insurer or "Current renewal"
            st.markdown(
                f"<div style='background:#fff7ed;border:1px solid #fdba74;border-radius:10px;"
                f"padding:0.8rem 1.2rem;margin-bottom:1.2rem;font-size:0.9rem;color:#333'>"
                f"🔄 <strong>Your current renewal — {renewal_label}:</strong> "
                f"${renewal_premium:,.2f}/year"
                + (f" &nbsp;·&nbsp; Excess ${renewal_excess:,}" if renewal_excess else "")
                + "</div>",
                unsafe_allow_html=True
            )
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Quotes Compared", len(quotes))
            col2.metric("Current Renewal", f"${renewal_premium:,.2f}")
            col3.metric("Cheapest Quote", f"${min(prices):,.2f}")
            col4.metric("Saving vs Renewal", f"${saving:,.2f}",
                        delta=f"-{(saving/renewal_premium*100):.0f}%" if saving > 0 else None,
                        delta_color="normal")
        else:
            saving = max(prices) - min(prices)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Quotes Compared", len(quotes))
            col2.metric("Lowest Premium", f"${min(prices):,.2f}")
            col3.metric("Highest Premium", f"${max(prices):,.2f}")
            col4.metric("Max Saving", f"${saving:,.2f}")

        st.markdown('<div class="section-title">Quote Breakdown</div>', unsafe_allow_html=True)
        st.caption("Each quote shows the underwriter — the insurance company that actually holds the risk and pays your claims. Brands sharing an underwriter are often variations of the same policy under different branding.")

        with st.expander("ℹ️ About the AFCA complaint numbers"):
            st.markdown("""
AFCA (the Australian Financial Complaints Authority) publishes complaint data for every insurer in its public **[Datacube](https://data.afca.org.au)**, updated monthly.

**Read the numbers with care:** complaint volumes largely reflect company size — the biggest insurers naturally receive the most complaints, so a high count is not by itself a sign of poor claims handling, and a small insurer's low count is not proof of great service. That's also why these aren't converted into star ratings: without complaints-per-policy data (which isn't published), a star formula would simply rank insurers by size.

Figures shown are complaints received in FY2024-25 at underwriter group level. For underwriters without a figure here, or for resolution rates and outcomes, search the firm in the [AFCA Datacube](https://data.afca.org.au).
""")

        uw_counts = Counter(UNDERWRITERS.get(q["insurer"]) for q in quotes if UNDERWRITERS.get(q["insurer"]))
        shared = {u: c for u, c in uw_counts.items() if c > 1}
        if shared:
            shared_str = " · ".join(f"**{u}** sits behind {c} of your quotes" for u, c in shared.items())
            st.info(f"💡 {shared_str}. These are likely the same underlying policy priced differently — compare their inclusions closely.")

        flagged = {}
        for q in quotes:
            qf = quote_flags(q, target_excess)
            if qf:
                flagged[q["insurer"]] = qf
        ins_counts = Counter(q["insurer"] for q in quotes)
        dups = [i for i, c in ins_counts.items() if c > 1]
        if dups:
            flagged_dups = ", ".join(f"**{d}** (x{ins_counts[d]})" for d in dups)
            st.warning(f"⚠️ Duplicate quotes for {flagged_dups} — delete the extras in the **Enter Quotes** tab so the comparison isn't skewed.")
        if flagged:
            st.warning("⚠️ **Worth checking:** " + " · ".join(f"**{k}** — {'; '.join(fl)}" for k, fl in flagged.items()))

        cols = st.columns(min(len(sorted_quotes), 3))
        for i, q in enumerate(sorted_quotes):
            col = cols[i % 3]
            with col:
                is_best = (i == 0)
                card_class = "best-value" if is_best else "quote-card"
                badge = '<span class="badge-best">Best Value</span><br>' if is_best else ""
                saving_vs_best = q["annual_premium"] - best["annual_premium"]
                saving_str = (f'<span style="color:#e53e3e;font-size:0.8rem">+${saving_vs_best:,.2f} more</span>'
                              if saving_vs_best > 0 else
                              '<span style="color:#48bb78;font-size:0.8rem">✓ Lowest price</span>')
                monthly_str = (f'<div class="price-sub">${q["monthly_premium"]:,.2f}/month</div>'
                               if q["monthly_premium"] > 0 else "")
                inclusions = []
                if q["roadside"]: inclusions.append("Roadside")
                if q["hire_car"]: inclusions.append("Hire Car")
                if q["windscreen"]: inclusions.append("Windscreen")
                if q["no_claims"]: inclusions.append("NCD")
                if q["online_discount"]: inclusions.append("Online discount")
                inc_str = " · ".join(inclusions) if inclusions else "None noted"
                ref_str = (f'<div style="font-size:0.75rem;color:#888;margin-top:4px">Ref: {q["quote_ref"]}</div>'
                           if q["quote_ref"] else "")
                notes_str = (f'<div style="font-size:0.8rem;color:#666;margin-top:8px;border-top:1px solid #e0e0e0;padding-top:8px">{q["notes"]}</div>'
                             if q["notes"] else "")
                uw = UNDERWRITERS.get(q["insurer"], "")
                uw_str = (f'<div style="font-size:0.72rem;color:#999;margin-bottom:6px">Underwritten by {uw}</div>'
                          if uw else "")
                card_flags = quote_flags(q, target_excess)
                flag_str = "".join(f'<div style="font-size:0.72rem;color:#d97706;margin-top:6px">⚠️ {cf}</div>'
                                   for cf in card_flags)
                rv = q.get("rating")
                rating_str = (f'<div style="font-size:0.78rem;color:#f59e0b;margin-bottom:4px">{"★" * int(rv)}{"½" if rv % 1 >= 0.5 else ""} {rv}/5</div>'
                              if rv else "")
                afca = AFCA_COMPLAINTS.get(uw, "")
                afca_str = (f'<div style="font-size:0.7rem;color:#aaa;margin-bottom:4px">AFCA complaints FY24-25: {afca}</div>'
                            if afca else "")

                st.markdown(f"""
                <div class="{card_class}">
                    {badge}
                    <div style="font-size:1.1rem;font-weight:700;margin-bottom:2px">{q['insurer']}</div>
                    {uw_str}
                    {rating_str}
                    {afca_str}
                    <div class="price-big">${q['annual_premium']:,.2f}<span style="font-size:1rem;font-weight:400">/yr</span></div>
                    {monthly_str}
                    {saving_str}
                    <div style="margin-top:12px;font-size:0.82rem;color:#555">
                        <div>📋 <strong>Excess:</strong> ${q['excess']:,}</div>
                        <div>🛡️ <strong>Cover:</strong> {q['cover']}</div>
                        <div>💎 <strong>Sum Insured:</strong> {q['sum_type']}</div>
                        <div>✅ <strong>Includes:</strong> {inc_str}</div>
                        <div style="color:#888;font-size:0.75rem">Valid until: {q['valid_until']}</div>
                    </div>
                    {flag_str}
                    {ref_str}
                    {notes_str}
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:2rem">Full Comparison Table</div>', unsafe_allow_html=True)

        table_data = []
        if renewal_premium and renewal_premium > 0:
            table_data.append({
                "Insurer": f"🔄 {renewal_insurer or 'Current renewal'} (your renewal)",
                "Underwriter": UNDERWRITERS.get(renewal_insurer, "—"),
                "AFCA FY25": AFCA_COMPLAINTS.get(UNDERWRITERS.get(renewal_insurer, ""), "—"),
                "Annual ($)": f"${renewal_premium:,.2f}",
                "Monthly ($)": "—",
                "Excess ($)": f"${renewal_excess:,}" if renewal_excess else "—",
                "Sum Insured": "—",
                "Inclusions": "—",
                "Quote Ref": "—",
                "Valid Until": "—",
                "⚠ Checks": "current policy",
            })
        for q in sorted_quotes:
            inclusions = []
            if q["roadside"]: inclusions.append("Roadside")
            if q["hire_car"]: inclusions.append("Hire Car")
            if q["windscreen"]: inclusions.append("Windscreen")
            table_data.append({
                "Insurer": q["insurer"],
                "Underwriter": UNDERWRITERS.get(q["insurer"], "—"),
                "AFCA FY25": AFCA_COMPLAINTS.get(UNDERWRITERS.get(q["insurer"], ""), "—"),
                "Annual ($)": f"${q['annual_premium']:,.2f}",
                "Monthly ($)": f"${q['monthly_premium']:,.2f}" if q["monthly_premium"] > 0 else "—",
                "Excess ($)": f"${q['excess']:,}",
                "Sum Insured": q["sum_type"],
                "Inclusions": ", ".join(inclusions) if inclusions else "—",
                "Quote Ref": q["quote_ref"] or "—",
                "Valid Until": q["valid_until"],
                "⚠ Checks": "; ".join(quote_flags(q, target_excess)) or "—",
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, width="stretch", hide_index=True)

    st.markdown(_DISCLAIMER, unsafe_allow_html=True)
