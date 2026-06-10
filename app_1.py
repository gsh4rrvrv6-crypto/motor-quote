import streamlit as st
import pandas as pd
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
    "RACV": "Insurance Manufacturers of Australia (IAG/RACV JV)",
    "ANZ": "CGU (IAG)",
    "Bendigo Bank": "CGU (IAG)",
    "RACQ": "RACQ Insurance",
    "BOQ": "RACQ Insurance",
    "ALDI": "RACQ Insurance (via Honey)",
    "Budget Direct": "Auto & General",
    "Qantas": "Auto & General",
    "Coles": "Auto & General",
    "ING": "Auto & General",
    "Woolworths": "Hollard",
    "Real Insurance": "Hollard",
    "Australian Seniors": "Hollard",
    "CommBank": "Hollard",
    "Huddle": "Hollard",
    "Allianz": "Allianz",
    "Westpac": "Allianz",
    "St.George": "Allianz",
    "BankSA": "Allianz",
    "Bank of Melbourne": "Allianz",
    "NAB": "Allianz",
    "HSBC": "Allianz",
    "TIO": "Allianz",
    "QBE": "QBE",
    "Stella": "QBE",
    "Elders": "QBE",
    "KOBA": "Pacific International Insurance",
    "WFI": "Insurance Australia Group (IAG)",
    "RAA": "RAA Insurance",
    "RAC": "RAC Insurance (WA)",
    "RACT": "RACT Insurance",
}

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

tab_help, tab4, tab1, tab2, tab3 = st.tabs(["📖 Instructions", "🤖 Get Quotes", "📋 Vehicle & Drivers", "📝 Enter Quotes", "📊 Compare"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 0 — Instructions
# ════════════════════════════════════════════════════════════════════════════
with tab_help:
    with st.expander("📋 How This Tool Works", expanded=True):
        st.markdown("""
Compare car insurance quotes from **35+ Australian insurers** side by side. The workflow:

1. **📋 Vehicle & Drivers** — enter your car, driver and policy details once, then hit **Save Details**. You can auto-fill this from your renewal notice (see below).
2. **🤖 Get Quotes** — for each insurer, copy the ready-made automation prompt into a Claude chat. Claude opens that insurer's website, fills in the quote form using your saved details, and reports back the price.
3. **📝 Enter Quotes** — enter each premium, excess and inclusions as you receive them.
4. **📊 Compare** — see every quote side by side with the best value highlighted, and download the comparison as a CSV.
""")

    st.markdown('<div class="section-title" style="margin-top:1.5rem">What You Need</div>', unsafe_allow_html=True)
    st.markdown("""
- A **Claude account** — sign up free at [claude.ai](https://claude.ai)
- The **[Claude in Chrome extension](https://chromewebstore.google.com/detail/claude-ai/ppmhkbzfgnlphjgaaomgfnkknhijaggh)** — this is what lets Claude fill in forms in your browser

You can also skip the automation entirely: visit each insurer's website yourself, get quotes manually, and just use the **Enter Quotes** and **Compare** tabs.
""")

    st.markdown('<div class="section-title" style="margin-top:1.5rem">📄 Auto-Fill Your Details from a Document</div>', unsafe_allow_html=True)

    with st.expander("✨ Auto-fill from your renewal notice or insurance slip", expanded=False):

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

        st.markdown("""1. Open **[claude.ai](https://claude.ai)** in another tab · 2. Upload your document · 3. Copy & paste the prompt below · 4. Claude fills in the form for you""")
        st.text_area("Prompt to copy:", value=chrome_prefill_prompt, height=100, label_visibility="collapsed")

# ════════════════════════════════════════════════════════════════════════════
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
        st.success("✅ Details saved! Head to the **Get Quotes** tab to start getting prices.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add Quotes
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">Add a Quote</div>', unsafe_allow_html=True)
    st.caption("Enter the details from each insurer quote you've obtained.")

    insurers = ["GIO", "AAMI", "NRMA", "Budget Direct", "Allianz",
                "QBE", "Suncorp", "APIA", "Shannons", "Qantas", "Coles",
                "Woolworths", "Real Insurance", "Bingle", "ROLLiN'", "Huddle",
                "ALDI", "ING", "CommBank", "Australian Seniors",
                "Stella", "KOBA", "TIO", "WFI", "Elders", "Westpac", "St.George", "BankSA",
                "Bank of Melbourne", "NAB", "ANZ", "Bendigo Bank", "BOQ", "HSBC",
                "RAA", "RAC", "RACV", "RACQ", "RACT", "Other"]

    with st.form("add_quote_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            insurer = st.selectbox("Insurer", insurers)
            custom_insurer = st.text_input("If 'Other', enter name")
            annual_premium = st.number_input("Annual Premium ($)", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            monthly_premium = st.number_input("Monthly Premium ($) — if offered", min_value=0.0, step=0.01, format="%.2f")
            quote_excess = st.number_input("Excess ($)", min_value=0, step=50, value=0)
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
        st.info("💡 No quotes yet — add some in the **Enter Quotes** tab first.")
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
        st.caption("Each quote shows the underwriter — the insurance company that actually holds the risk and pays your claims. Brands sharing an underwriter are often variations of the same policy under different branding.")

        uw_counts = Counter(UNDERWRITERS.get(q["insurer"]) for q in quotes if UNDERWRITERS.get(q["insurer"]))
        shared = {u: c for u, c in uw_counts.items() if c > 1}
        if shared:
            shared_str = " · ".join(f"**{u}** sits behind {c} of your quotes" for u, c in shared.items())
            st.info(f"💡 {shared_str}. These are likely the same underlying policy priced differently — compare their inclusions closely.")

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

                st.markdown(f"""
                <div class="{card_class}">
                    {badge}
                    <div style="font-size:1.1rem;font-weight:700;margin-bottom:2px">{q['insurer']}</div>
                    {uw_str}
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
                "Underwriter": UNDERWRITERS.get(q["insurer"], "—"),
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
        st.caption("Copy a prompt below into a new Claude chat (with the Chrome extension active) — Claude fills out that insurer's quote form automatically and reports back the price. Full setup steps are in the 📖 Instructions tab.")

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
            "QBE": {
                "url": "https://www.qbe.com/au/car-insurance",
                "notes": "",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from QBE.

Go to: https://www.qbe.com/au/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to qbe.com/au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Select market value (not agreed value)
- If asked about modifications, select None
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "APIA": {
                "url": "https://www.apia.com.au/car-insurance.html",
                "notes": "Part of Suncorp Group — same platform family as GIO/AAMI. Designed for over-50s; eligibility criteria may apply.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from APIA.

Go to: https://www.apia.com.au/car-insurance.html

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- APIA shares the same platform as GIO and AAMI — address format: enter suburb name and select from dropdown
- APIA is designed for over-50s — if an eligibility question blocks the quote, stop and let me know
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "Shannons": {
                "url": "https://www.shannons.com.au/request-a-quote/",
                "notes": "⚠️ Enthusiast insurer (Suncorp Group). The online form often hands off to a consultant — pricing may come via a call on 13 46 46. Geared to motoring enthusiasts; standard vehicles may not be eligible.",
                "prompt": f"""Using the Claude in Chrome extension, please start a comprehensive car insurance quote from Shannons.

Go to: https://www.shannons.com.au/request-a-quote/

Fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Important notes:
- Shannons is an enthusiast insurer — the online flow may hand off to their Online Assistant or offer a call with a consultant instead of showing a price on screen
- Complete the form as far as possible; if it asks to connect you to a consultant or requests a phone call, accept and let me know
- If asked about at-fault claims, select None in the last 3 years

If a premium is shown on screen, tell me the annual premium, excess, quote reference number, and inclusions. If pricing requires a call, let me know that the form was submitted."""
            },
            "Qantas": {
                "url": "https://insurance.qantas.com/car-insurance",
                "notes": "Underwritten by Auto & General (same as Budget Direct and Coles) — quote flow is similar. Earns Qantas Points; have your Frequent Flyer number handy.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Qantas Insurance.

Go to: https://insurance.qantas.com/car-insurance

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow". Qantas uses the same underlying platform as Budget Direct, so the overnight address may be asked for BEFORE the rego lookup — this is normal.

{context}

Notes:
- Address format: enter full address including state and postcode e.g. "Lane Cove NSW 2066"
- Select market value (not agreed value)
- If asked for a Qantas Frequent Flyer number, skip it or leave blank unless I've given you one
- Apply any online discount if offered
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any points offer shown, and what inclusions are listed."""
            },
            "Coles": {
                "url": "https://www.coles.com.au/insurance/car-insurance",
                "notes": "Underwritten by Auto & General (same as Budget Direct and Qantas). 15% online discount on first-year premium for new policies bought online.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Coles Insurance.

Go to: https://www.coles.com.au/insurance/car-insurance

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow". Coles uses the same underlying platform as Budget Direct, so the overnight address may be asked for BEFORE the rego lookup — this is normal.

{context}

Notes:
- Address format: enter full address including state and postcode e.g. "Lane Cove NSW 2066"
- Select market value (not agreed value)
- A 15% online discount should apply automatically for new policies — confirm it's reflected in the price
- If asked for a Flybuys number, skip it or leave blank unless I've given you one
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, whether the online discount was applied, and what inclusions are listed."""
            },
            "Woolworths": {
                "url": "https://insurance.woolworths.com.au/car-insurance.html",
                "notes": "Underwritten by Hollard. Check for Everyday Rewards discounts.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Woolworths Insurance.

Go to: https://insurance.woolworths.com.au/car-insurance.html

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to insurance.woolworths.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Select market value (not agreed value)
- If asked for an Everyday Rewards card number, skip it or leave blank unless I've given you one
- Apply any online discount if offered
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any discounts applied, and what inclusions are listed."""
            },
            "Real Insurance": {
                "url": "https://www.realinsurance.com.au/car-insurance",
                "notes": "Underwritten by Hollard. Offers Pay As You Drive — worth comparing if annual kilometres are low.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Real Insurance.

Go to: https://www.realinsurance.com.au/car-insurance

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Select market value (not agreed value)
- Real Insurance offers a "Pay As You Drive" option for low-kilometre drivers — if the annual kilometres above are under 15,000, also note the Pay As You Drive price if it's shown
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed — and the Pay As You Drive price if applicable."""
            },
            "Suncorp": {
                "url": "https://www.suncorp.com.au/insurance/car.html",
                "notes": "Part of Suncorp Group — same platform family as GIO and AAMI.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Suncorp.

Go to: https://www.suncorp.com.au/insurance/car.html

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to suncorp.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Suncorp shares the same platform family as GIO and AAMI — address format: enter suburb name and select from dropdown
- Select market value (not agreed value)
- If asked about modifications, select None
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "RACV": {
                "url": "https://www.racv.com.au/insurance/car-insurance.html",
                "notes": "Victorian motoring club. Same underwriter as NRMA (IAG joint venture) — quote flow may be similar. Generally for vehicles garaged in Victoria.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from RACV.

Go to: https://www.racv.com.au/insurance/car-insurance.html

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to racv.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- RACV generally insures vehicles garaged in Victoria — if the form says the location isn't eligible, stop and let me know
- If prompted to log in, look for a "Continue without logging in" or guest option (RACV shares its underwriter with NRMA)
- If asked for an RACV membership number, skip it or leave blank unless I've given you one
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "RACQ": {
                "url": "https://www.racq.com.au/insurance/car-insurance",
                "notes": "Queensland motoring club — generally for vehicles garaged in QLD. Member discounts may apply.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from RACQ.

Go to: https://www.racq.com.au/insurance/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to racq.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- RACQ generally insures vehicles garaged in Queensland — if the form says the location isn't eligible, stop and let me know
- If asked for an RACQ membership number, skip it or leave blank unless I've given you one
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any member discounts applied, and what inclusions are listed."""
            },
            "RAA": {
                "url": "https://www.raa.com.au/insurance/car-insurance",
                "notes": "South Australian motoring club — generally for vehicles garaged in SA. Member discounts may apply.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from RAA.

Go to: https://www.raa.com.au/insurance/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to raa.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- RAA generally insures vehicles garaged in South Australia — if the form says the location isn't eligible, stop and let me know
- If asked for an RAA membership number, skip it or leave blank unless I've given you one
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any member discounts applied, and what inclusions are listed."""
            },
            "RAC": {
                "url": "https://rac.com.au/car-motorcycle/car-insurance",
                "notes": "Western Australian motoring club — car insurance only for vehicles garaged in WA. Member discounts may apply.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from RAC (WA).

Go to: https://rac.com.au/car-motorcycle/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to rac.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- RAC only insures vehicles garaged in Western Australia — if the form says the location isn't eligible, stop and let me know
- If asked for an RAC membership number, skip it or leave blank unless I've given you one
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any member discounts applied, and what inclusions are listed."""
            },
            "Bingle": {
                "url": "https://www.bingle.com.au",
                "notes": "Suncorp Group's online-only budget brand — short quote flow, minimal options, no phone support.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Bingle.

Go to: https://www.bingle.com.au

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Bingle is a stripped-back online-only brand — the quote flow is short with fewer questions than most insurers
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "ROLLiN'": {
                "url": "https://www.rollininsurance.com.au",
                "notes": "IAG brand. Subscription-style cover — pricing is shown monthly with no annual lock-in.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from ROLLiN'.

Go to: https://www.rollininsurance.com.au

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- ROLLiN' prices its cover as a monthly subscription rather than an annual premium
- Select market value if the option is offered
- If asked about at-fault claims, select None in the last 3 years

Once the final price is shown, tell me the monthly premium, the annual equivalent (monthly times 12), excess, quote reference number, and what inclusions are listed."""
            },
            "Huddle": {
                "url": "https://www.huddle.com.au/car-insurance",
                "notes": "Online insurer with a fast quote flow.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Huddle.

Go to: https://www.huddle.com.au/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to huddle.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Select market value (not agreed value) if the option is offered
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "ALDI": {
                "url": "https://www.aldiinsurance.com.au/car/",
                "notes": "Distributed with Honey Insurance. Comprehensive cover only — no third party options and no roadside assistance add-on.",
                "prompt": f"""Using the Claude in Chrome extension, please get a car insurance quote from ALDI Insurance.

Go to: https://www.aldiinsurance.com.au/car/

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- ALDI only offers Comprehensive cover — there are no third party options
- ALDI does not offer roadside assistance, so don't look for it as an add-on
- Select market value if the option is offered
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "ING": {
                "url": "https://www.ing.com.au/insurance/car-insurance.html",
                "notes": "Underwritten by Auto & General (same as Budget Direct) — quote flow is similar. You don't need to be an ING customer.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from ING.

Go to: https://www.ing.com.au/insurance/car-insurance.html

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to ing.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow". ING uses the same underlying platform as Budget Direct, so the overnight address may be asked for BEFORE the rego lookup — this is normal.

{context}

Notes:
- You don't need to be an ING banking customer — do not log in
- Address format: enter full address including state and postcode e.g. "Lane Cove NSW 2066"
- Select market value (not agreed value)
- Apply any online discount if offered
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any discounts applied, and what inclusions are listed."""
            },
            "CommBank": {
                "url": "https://www.commbank.com.au/insurance/car-insurance.html",
                "notes": "Underwritten by Hollard. You don't need to be a CommBank customer — use the guest quote option rather than logging in to NetBank.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from CommBank.

Go to: https://www.commbank.com.au/insurance/car-insurance.html

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to commbank.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Do NOT log in to NetBank — look for the option to get a quote as a guest / without logging in
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "Australian Seniors": {
                "url": "https://www.seniors.com.au/car-insurance",
                "notes": "Same stable as Real Insurance (Hollard). Designed for over-50s — eligibility criteria may apply. Seniors discount available.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Australian Seniors.

Go to: https://www.seniors.com.au/car-insurance

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Australian Seniors is designed for over-50s — if an age eligibility question blocks the quote, stop and let me know
- Select market value (not agreed value)
- Note any seniors discount applied to the price
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any discounts applied, and what inclusions are listed."""
            },
            "RACT": {
                "url": "https://www.ract.com.au/insurance/car-insurance",
                "notes": "Tasmanian motoring club — generally for vehicles garaged in TAS. Member discounts may apply.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from RACT.

Go to: https://www.ract.com.au/insurance/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to ract.com.au and navigate to Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- RACT generally insures vehicles garaged in Tasmania — if the form says the location isn't eligible, stop and let me know
- If asked for an RACT membership number, skip it or leave blank unless I've given you one
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any member discounts applied, and what inclusions are listed."""
            },
            "Stella": {
                "url": "https://www.stellainsurance.com.au",
                "notes": "Women-focused brand (open to everyone), QBE-underwritten. Comprehensive only. Doesn't cover all postcodes. Sign-up discount of 5–25% currently running.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Stella.

Go to: https://www.stellainsurance.com.au

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Stella only offers Comprehensive cover
- Stella doesn't cover all postcodes — if the form says the location isn't covered, stop and let me know
- A new-customer discount may apply — note whether it's reflected in the price
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, any discount applied, and what inclusions are listed."""
            },
            "KOBA": {
                "url": "https://www.kobainsurance.com.au",
                "notes": "Pay-per-km cover — an upfront fixed cost while parked plus cents per km driven, measured by a small device they post out. Best for low-km drivers.",
                "prompt": f"""Using the Claude in Chrome extension, please get a pay-per-km comprehensive car insurance quote from KOBA.

Go to: https://www.kobainsurance.com.au

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- KOBA's pricing is split: an upfront fixed cost covering the car while parked, plus a per-km rate while driving
- The quote shows three numbers: the upfront fixed cost, the per-km rate, and an annual estimate
- A small device (the KOBA Rider) gets posted out and plugs in under the dash to measure kms
- If asked about at-fault claims, select None in the last 3 years

Once the quote is shown, tell me all three numbers — the upfront fixed cost, the per-km rate, and the annual estimate — plus the excess and quote reference. The annual estimate is the figure to use for comparison."""
            },
            "TIO": {
                "url": "https://www.tiofi.com.au",
                "notes": "Northern Territory insurer (Allianz-owned) — primarily for NT vehicles.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from TIO.

Go to: https://www.tiofi.com.au

Navigate to Car Insurance, click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- TIO primarily insures vehicles in the Northern Territory — if the form says the location isn't eligible, stop and let me know
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "Westpac": {
                "url": "https://www.westpac.com.au/personal-banking/insurance/car-insurance/",
                "notes": "Underwritten by Allianz. You don't need to be a Westpac customer — don't log in.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Westpac.

Go to: https://www.westpac.com.au/personal-banking/insurance/car-insurance/

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Do NOT log in to Westpac online banking — the quote works as a guest
- Westpac car insurance is provided by Allianz, so the quote flow may resemble Allianz's
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "St.George": {
                "url": "https://www.stgeorge.com.au/personal/insurance/car-insurance",
                "notes": "Westpac Group brand — same Allianz product as Westpac. BankSA and Bank of Melbourne are identical.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from St.George.

Go to: https://www.stgeorge.com.au/personal/insurance/car-insurance

Click Get a quote and fill in all fields using the details below. If the page doesn't load, go to stgeorge.com.au and navigate to Insurance then Car Insurance. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Do NOT log in — the quote works as a guest
- St.George car insurance is provided by Allianz (same as Westpac)
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "NAB": {
                "url": "https://www.nab.com.au/personal/insurance/car",
                "notes": "Underwritten by Allianz. Up to 10% off the first year for new comprehensive policies bought online.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from NAB.

Go to: https://www.nab.com.au/personal/insurance/car

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Do NOT log in to NAB internet banking — the quote works as a guest
- An online discount of up to 10% should apply for new comprehensive policies — confirm it's reflected in the price
- NAB car insurance is issued by Allianz
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, whether the online discount was applied, and what inclusions are listed."""
            },
            "ANZ": {
                "url": "https://www.anz.com.au/personal/insurance/car-insurance/",
                "notes": "Underwritten by CGU (IAG).",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from ANZ.

Go to: https://www.anz.com.au/personal/insurance/car-insurance/

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Do NOT log in to ANZ internet banking — the quote works as a guest
- ANZ car insurance is issued by CGU (part of IAG)
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "Bendigo Bank": {
                "url": "https://www.bendigobank.com.au/personal/insurance/car/",
                "notes": "Underwritten by CGU (IAG). Not available for vehicles garaged in Victoria.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from Bendigo Bank.

Go to: https://www.bendigobank.com.au/personal/insurance/car/

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Bendigo Bank car insurance is not available for vehicles garaged in Victoria — if the form says the location isn't eligible, stop and let me know
- Do NOT log in to Bendigo internet banking — the quote works as a guest
- Issued by CGU (part of IAG); there's a standard Comprehensive and a top-tier Comprehensive Plus — quote the standard Comprehensive unless I say otherwise
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "BOQ": {
                "url": "https://www.boq.com.au/personal/insurance/",
                "notes": "Underwritten by RACQ Insurance. Comprehensive only.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from BOQ.

Go to: https://www.boq.com.au/personal/insurance/

Click Get a quote for Car Insurance and fill in all fields using the details below. The quote portal may open at insurance.boq.com.au — that's normal. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- BOQ only offers Comprehensive cover
- Do NOT log in to BOQ internet banking — the quote works as a guest
- BOQ car insurance is issued by RACQ Insurance
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, and what inclusions are listed."""
            },
            "HSBC": {
                "url": "https://www.hsbc.com.au/insurance/products/car/",
                "notes": "Underwritten by Allianz. Up to 10% off the first year for new comprehensive policies bought online.",
                "prompt": f"""Using the Claude in Chrome extension, please get a comprehensive car insurance quote from HSBC.

Go to: https://www.hsbc.com.au/insurance/products/car/

Click Get a quote and fill in all fields using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Do NOT log in to HSBC online banking — the quote works as a guest
- HSBC car insurance is issued by Allianz
- An online discount of up to 10% should apply for new comprehensive policies — confirm it's reflected in the price
- Select market value (not agreed value)
- If asked about at-fault claims, select None in the last 3 years

Once the final premium is shown, tell me the annual premium, excess, quote reference number, whether the online discount was applied, and what inclusions are listed."""
            },
            "WFI": {
                "url": "https://www.wfi.com.au/quotes",
                "notes": "⚠️ WFI (IAG) uses an agent/callback model — no price is shown online. The form requests a callback from your local area manager.",
                "prompt": f"""Using the Claude in Chrome extension, please submit a car insurance quote request to WFI.

Go to: https://www.wfi.com.au/quotes

Fill in the callback request form using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- WFI does not show a price online — this form requests a callback from a local area manager who will discuss pricing
- Fill in all contact and vehicle fields as accurately as possible
- If asked for a preferred contact time, select the next available business hours slot

Once the form is submitted, let me know it's done and that WFI will be in contact with a quote."""
            },
            "Elders": {
                "url": "https://www.eldersinsurance.com.au/personal-insurance/car",
                "notes": "⚠️ Underwritten by QBE. Elders uses a local agent/callback model — no price is shown online. Request triggers a callback from a local Elders agent.",
                "prompt": f"""Using the Claude in Chrome extension, please submit a car insurance quote request to Elders Insurance.

Go to: https://www.eldersinsurance.com.au/personal-insurance/car

Click "Request a quote" and fill in the form using the details below. If any permission prompts appear from the Chrome extension, select "Always allow".

{context}

Notes:
- Elders does not show a price online — a local Elders Insurance agent will contact you to discuss pricing
- Elders is underwritten by QBE Insurance
- Fill in all contact and vehicle fields as accurately as possible

Once the form is submitted, let me know it's done and that an Elders agent will be in contact."""
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

