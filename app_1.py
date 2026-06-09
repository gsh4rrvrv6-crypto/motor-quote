import streamlit as st
import pandas as pd
from datetime import date, datetime

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

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size:2rem; font-weight:700; color:#1a1a2e; margin-bottom:0.2rem; }
    .sub-header { color:#666; font-size:0.95rem; margin-bottom:2rem; }
    .section-title { font-size:1.1rem; font-weight:600; color:#1a1a2e; border-bottom:2px solid #e8e8e8; padding-bottom:6px; margin-bottom:1rem; }
    .quote-card { background:#f8f9ff; border:1px solid #e0e4ff; border-radius:12px; padding:1.2rem; margin-bottom:1rem; }
    .best-value { background:#f0fff4; border:2px solid #48bb78; border-radius:12px; padding:1.2rem; margin-bottom:1rem; }
    .badge-best { background:#48bb78; color:white; font-size:0.7rem; font-weight:700; padding:2px 8px; border-radius:20px; text-transform:uppercase; letter-spacing:0.5px; }
    .price-big { font-size:1.8rem; font-weight:700; color:#1a1a2e; }
    .price-sub { font-size:0.85rem; color:#666; }
    .stButton > button { background-color:#1a1a2e; color:white; border:none; border-radius:8px; padding:0.5rem 1.5rem; font-weight:600; }
    .stButton > button:hover { background-color:#2d2d4e; }
    .date-hint { font-size:0.75rem; color:#999; margin-top:-12px; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "quotes" not in st.session_state:
    st.session_state.quotes = []
if "vehicle" not in st.session_state:
    st.session_state.vehicle = {}
if "drivers" not in st.session_state:
    st.session_state.drivers = {}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-header">🚗 Motor Quote Comparison</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Enter your vehicle and driver details, add quotes from each insurer, then compare side by side.</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["📋 Vehicle & Drivers", "💰 Add Quotes", "📊 Compare", "🤖 Get Quotes"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Vehicle & Drivers
# ════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Prefill via Claude in Chrome ─────────────────────────────────────────
    st.markdown('<div class="section-title">📄 Prefill from Documents <span style="font-size:0.75rem;font-weight:400;color:#888">(optional — free)</span></div>', unsafe_allow_html=True)

    with st.expander("✨ Auto-fill this form from your renewal notice or insurance slip", expanded=False):
        st.markdown("""
**This fills the form automatically — completely free.**

**What you need:** The [Claude in Chrome extension](https://chrome.google.com/webstore/detail/claude-ai/ppmhkbzfgnlphjgaaomgfnkknhijaggh) installed in your browser.

**Steps:**
1. Open **[claude.ai](https://claude.ai)** in a new tab — keep this tab open too
2. Start a new chat in Claude
3. Upload your renewal notice or insurance slip (PDF or photo)
4. Copy the prompt below and paste it into Claude with your document
5. Claude will read your document and automatically fill in this form
""")

        # Detect the app's own URL for the prompt
        try:
            from streamlit.web.server.websocket_headers import _get_websocket_headers
            app_url = "this page"
        except Exception:
            app_url = "this page"

        chrome_prefill_prompt = """I've uploaded my motor insurance renewal notice or insurance slip.

Using the Claude in Chrome extension, please:

1. Extract all the insurance details from my uploaded document
2. Switch to the Motor Quote Comparison app tab (it should be open in your browser)
3. Fill in the form fields in the "Vehicle & Drivers" tab using the details from my document

Here are the fields to fill in and where to find them in the document:
- Year, Make, Model, Variant — from the vehicle description
- Registration number and state — from the rego details
- Cover type — Comprehensive / Third Party Fire & Theft / Third Party Only
- Sum insured — Market Value or Agreed Value
- Overnight parking suburb and postcode — from the garaging address
- Basic excess — the standard/basic excess amount in dollars
- Previous insurer — the name of the insurer on this document
- Main driver name, date of birth (DD/MM/YY), gender
- Additional driver name, date of birth (DD/MM/YY), gender (if listed)

For any dropdown fields, select the closest matching option.
For any fields not found in the document, leave them blank.

If any permission prompts appear from the Chrome extension, select "Always allow".

Once all fields are filled, click the "Save Details" button at the bottom of the form."""

        st.text_area(
            "Copy this prompt into Claude (with your document attached):",
            value=chrome_prefill_prompt,
            height=220,
            label_visibility="visible"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("👉 [Open Claude.ai in a new tab](https://claude.ai)")
        with col2:
            st.markdown("👉 [Get the Chrome extension](https://chromewebstore.google.com/detail/claude-ai/ppmhkbzfgnlphjgaaomgfnkknhijaggh)")

    st.markdown("---")
    st.markdown('<div class="section-title">Vehicle Details</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.number_input("Year", min_value=1990, max_value=2030,
                               value=st.session_state.vehicle.get("year", 2020), step=1)
        make = st.text_input("Make", value=st.session_state.vehicle.get("make", ""))
        model = st.text_input("Model", value=st.session_state.vehicle.get("model", ""))
    with col2:
        variant = st.text_input("Variant / Series", value=st.session_state.vehicle.get("variant", ""))
        rego = st.text_input("Registration Number", value=st.session_state.vehicle.get("rego", ""))
        rego_state = st.selectbox("Rego State",
                                  ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
                                  index=["NSW","VIC","QLD","WA","SA","TAS","ACT","NT"].index(
                                      st.session_state.vehicle.get("rego_state", "NSW")))
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

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Parking & Usage</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        overnight_suburb = st.text_input("Overnight Parking Suburb", value=st.session_state.vehicle.get("overnight_suburb", ""))
        overnight_postcode = st.text_input("Overnight Postcode", value=st.session_state.vehicle.get("overnight_postcode", ""))
    with col2:
        day_suburb = st.text_input("Daytime Parking Suburb", value=st.session_state.vehicle.get("day_suburb", ""))
        day_postcode = st.text_input("Daytime Postcode", value=st.session_state.vehicle.get("day_postcode", ""))
    with col3:
        usage = st.multiselect("Vehicle Usage", ["Private", "Commute", "Business"],
                               default=st.session_state.vehicle.get("usage", ["Private"]))
        finance = st.selectbox("Financed?", ["No", "Yes"],
                               index=["No","Yes"].index(st.session_state.vehicle.get("finance", "No")))

    st.markdown('<div class="section-title" style="margin-top:1.5rem">Policy Details</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.text_input("Policy Start Date (DD/MM/YY)",
                                   value=st.session_state.vehicle.get("start_date", today_str()))
        previous_insurer = st.text_input("Previous Insurer", value=st.session_state.vehicle.get("previous_insurer", ""))
    with col2:
        excess = st.number_input("Basic Excess ($)", min_value=0, max_value=5000,
                                 value=st.session_state.vehicle.get("excess", 500), step=50)

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

    if st.button("💾  Save Details", use_container_width=True):
        st.session_state.vehicle = {
            "year": year, "make": make, "model": model, "variant": variant,
            "rego": rego, "rego_state": rego_state, "cover_type": cover_type,
            "sum_insured": sum_insured, "annual_kms": annual_kms,
            "overnight_suburb": overnight_suburb, "overnight_postcode": overnight_postcode,
            "day_suburb": day_suburb, "day_postcode": day_postcode,
            "usage": usage, "finance": finance,
            "start_date": start_date, "previous_insurer": previous_insurer,
            "excess": excess
        }
        st.session_state.drivers = {
            "d1_name": d1_name, "d1_dob": d1_dob, "d1_gender": d1_gender,
            "d1_licence": d1_licence, "d1_claims": d1_claims,
            "d2_name": d2_name, "d2_dob": d2_dob, "d2_gender": d2_gender,
            "d2_licence": d2_licence, "d2_claims": d2_claims,
        }
        st.success("✅ Details saved! Head to the **Add Quotes** tab to enter your insurer quotes.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add Quotes
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">Add a Quote</div>', unsafe_allow_html=True)
    st.caption("Enter the details from each insurer quote you've obtained.")

    insurers = ["GIO", "AAMI", "NRMA", "Youi", "Budget Direct", "Allianz",
                "QBE", "Suncorp", "RAA", "RACV", "RACQ", "Other"]

    with st.form("add_quote_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            insurer = st.selectbox("Insurer", insurers)
            custom_insurer = st.text_input("If 'Other', enter name")
            annual_premium = st.number_input("Annual Premium ($)", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            monthly_premium = st.number_input("Monthly Premium ($) — if offered", min_value=0.0, step=0.01, format="%.2f")
            quote_excess = st.number_input("Excess ($)", min_value=0, step=50, value=500)
            cover = st.selectbox("Cover Type", ["Comprehensive", "Third Party Fire & Theft", "Third Party Only"])
        with col3:
            sum_type = st.selectbox("Sum Insured", ["Market Value", "Agreed Value"])
            quote_ref = st.text_input("Quote Reference / Number")
            valid_until = st.text_input("Quote Valid Until (DD/MM/YY)", value=today_str())

        st.markdown("**Inclusions & Notes**")
        col1, col2 = st.columns(2)
        with col1:
            roadside = st.checkbox("Roadside Assistance included")
            hire_car = st.checkbox("Hire Car included")
            windscreen = st.checkbox("Windscreen cover included")
        with col2:
            no_claims = st.checkbox("No Claims Discount applied")
            online_discount = st.checkbox("Online discount applied")
            notes = st.text_area("Notes (e.g. exclusions, conditions)", height=80)

        submitted = st.form_submit_button("➕  Add Quote", use_container_width=True)
        if submitted:
            insurer_name = custom_insurer if insurer == "Other" and custom_insurer else insurer
            if annual_premium > 0:
                st.session_state.quotes.append({
                    "insurer": insurer_name,
                    "annual_premium": annual_premium,
                    "monthly_premium": monthly_premium,
                    "excess": quote_excess,
                    "cover": cover,
                    "sum_type": sum_type,
                    "quote_ref": quote_ref,
                    "valid_until": valid_until,
                    "roadside": roadside,
                    "hire_car": hire_car,
                    "windscreen": windscreen,
                    "no_claims": no_claims,
                    "online_discount": online_discount,
                    "notes": notes
                })
                st.success(f"✅ {insurer_name} quote added! Head to **Compare** to see the comparison.")
            else:
                st.error("Please enter an annual premium greater than $0.")

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

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Compare
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    if not st.session_state.quotes:
        st.info("💡 No quotes yet — add some in the **Add Quotes** tab first.")
    else:
        quotes = st.session_state.quotes
        sorted_quotes = sorted(quotes, key=lambda x: x["annual_premium"])
        best = sorted_quotes[0]
        v = st.session_state.vehicle

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
        saving = max(prices) - min(prices)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Quotes Compared", len(quotes))
        col2.metric("Lowest Premium", f"${min(prices):,.2f}")
        col3.metric("Highest Premium", f"${max(prices):,.2f}")
        col4.metric("Max Saving", f"${saving:,.2f}")

        st.markdown("---")
        st.markdown('<div class="section-title">Quote Breakdown</div>', unsafe_allow_html=True)

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

                st.markdown(f"""
                <div class="{card_class}">
                    {badge}
                    <div style="font-size:1.1rem;font-weight:700;margin-bottom:4px">{q['insurer']}</div>
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
                    {ref_str}
                    {notes_str}
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:2rem">Full Comparison Table</div>', unsafe_allow_html=True)

        table_data = []
        for q in sorted_quotes:
            inclusions = []
            if q["roadside"]: inclusions.append("Roadside")
            if q["hire_car"]: inclusions.append("Hire Car")
            if q["windscreen"]: inclusions.append("Windscreen")
            table_data.append({
                "Insurer": q["insurer"],
                "Annual ($)": f"${q['annual_premium']:,.2f}",
                "Monthly ($)": f"${q['monthly_premium']:,.2f}" if q["monthly_premium"] > 0 else "—",
                "Excess ($)": f"${q['excess']:,}",
                "Sum Insured": q["sum_type"],
                "Inclusions": ", ".join(inclusions) if inclusions else "—",
                "Quote Ref": q["quote_ref"] or "—",
                "Valid Until": q["valid_until"],
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                "⬇️  Download as CSV",
                data=csv,
                file_name=f"motor_quotes_{date.today().strftime('%d%m%y')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            if st.button("🗑  Clear All Quotes", use_container_width=True):
                st.session_state.quotes = []
                st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Get Quotes (automation prompts)
# ════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-title">Get Quotes Automatically</div>', unsafe_allow_html=True)

    v = st.session_state.vehicle
    d = st.session_state.drivers

    if not v:
        st.warning("⚠️ Please fill in your Vehicle & Driver details first (Tab 1), then come back here.")
    else:
        st.markdown("""
        **How this works:**
        1. Make sure you have the **Claude in Chrome** extension installed in your browser
        2. Click **Copy Prompt** next to the insurer you want
        3. Open a new Claude chat at [claude.ai](https://claude.ai)
        4. Paste the prompt and hit send — Claude will fill out the quote form automatically
        5. Come back here and enter the quoted price in the **Add Quotes** tab
        """)

        st.info("💡 Youi always delivers pricing via a phone call — they will call you with the quote rather than show it on screen.")

        st.markdown("---")

        # Build the shared vehicle/driver context block
        vehicle_str = f"{v.get('year','')} {v.get('make','')} {v.get('model','')} {v.get('variant','')}".strip()
        usage_str = ", ".join(v.get("usage", [])) if v.get("usage") else "Private"
        overnight_addr = f"{v.get('overnight_suburb','')} {v.get('overnight_postcode','')}".strip()
        day_addr = f"{v.get('day_suburb','')} {v.get('day_postcode','')}".strip()
        d2_block = ""
        if d.get("d2_name"):
            d2_block = f"""
- Additional driver: {d.get('d2_name','')}, DOB {d.get('d2_dob','')}, {d.get('d2_gender','')}, {d.get('d2_licence','Full Australian')} licence, claims: {d.get('d2_claims','None')}"""

        context = f"""Vehicle: {vehicle_str}
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

        # Define per-insurer prompts
        insurers_prompts = {
            "GIO": {
                "url": "https://www.gio.com.au/car-insurance.html",
                "notes": "Shares the same platform as AAMI. Start date field uses a calendar picker.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from GIO.

Go to: https://www.gio.com.au/car-insurance.html

Click Get a quote for Comprehensive cover, then fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Address format that works best: enter suburb name and select from dropdown
- GIO and AAMI share the same platform
- Select market value (not agreed value)
- If asked about modifications, select None
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "AAMI": {
                "url": "https://www.aami.com.au/car-insurance/get-quote.html",
                "notes": "Shares the same platform as GIO.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from AAMI.

Go to: https://www.aami.com.au/car-insurance/get-quote.html

Fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Address format that works best: enter suburb name and select from dropdown
- Select market value (not agreed value)
- If asked about modifications, select None
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "Budget Direct": {
                "url": "https://www.budgetdirect.com.au/car-insurance/get-quote.html",
                "notes": "Quote flow starts with overnight address before rego lookup. Requires 'Always allow' permission grant.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Budget Direct.

Go to: https://www.budgetdirect.com.au/car-insurance/get-quote.html

Fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow". Budget Direct asks for the overnight address BEFORE the rego lookup — this is normal.

{context}

Notes:
- Enter overnight address first when prompted, before entering rego
- Address format: enter full address including state and postcode e.g. "Lane Cove NSW 2066"
- Select market value (not agreed value)
- Apply any online discount if offered
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, monthly premium if shown, excess, quote reference number, any discounts applied, and what inclusions are listed."""
            },
            "NRMA": {
                "url": "https://www.nrma.com.au/car-insurance",
                "notes": "Opens quote portal in a new tab. Click 'Continue without logging in' when prompted. Requires 'Always allow' permission grant.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from NRMA.

Go to: https://www.nrma.com.au/car-insurance

Click Get a quote for Comprehensive cover. The quote portal will open in a new tab at insurance.nrma.com.au — switch to that tab. Click "Continue without logging in" when it appears. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Click "Continue without logging in" on the welcome screen
- Address format: enter suburb and select from the dropdown
- Select market value (not agreed value)
- Check if there is a promo code field and apply any current discount codes
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any promo codes applied, and what inclusions are listed."""
            },
            "Youi": {
                "url": "https://www.youi.com.au/car-insurance",
                "notes": "⚠️ Youi delivers pricing via phone call, not on screen. They will call you with the quote. A mobile PIN verification appears mid-quote.",
                "prompt": f"""Using the Claude in Chrome extension, please start a comprehensive car insurance quote from Youi.

Go to: https://www.youi.com.au/car-insurance

Fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Important notes:
- Youi will ask for a mobile number and send a PIN verification mid-quote — enter the PIN when it arrives
- Youi does NOT show the price on screen — they will call you on your mobile with the quote
- Make sure your mobile number is correct when entering contact details
- If asked about at-fault claims, select None in the last 3 years
- Complete the form as far as possible until they confirm they will call you

Let me know once the form is submitted and Youi has confirmed they will call with the quote."""
            },
            "Allianz": {
                "url": "https://www.allianz.com.au/car-insurance/",
                "notes": "",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Allianz.

Go to: https://www.allianz.com.au/car-insurance/

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Select market value (not agreed value)
- If asked about modifications, select None
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
        }

        for insurer_name, info in insurers_prompts.items():
            with st.expander(f"**{insurer_name}**  —  {info['url']}", expanded=False):
                if info["notes"]:
                    st.caption(f"ℹ️ {info['notes']}")
                st.text_area(
                    "Automation prompt — copy this into a new Claude chat with Chrome extension active:",
                    value=info["prompt"],
                    height=200,
                    key=f"prompt_{insurer_name}",
                    label_visibility="visible"
                )
                st.markdown(f"[Open {insurer_name} →]({info['url']})")

