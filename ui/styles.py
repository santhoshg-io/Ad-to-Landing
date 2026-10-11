CUSTOM_CSS = """
<style>
/* === BASE THEME & STRICT PALETTE (NO DARK BLUE, NO VIOLET, NO PURPLE) === */
:root {
    --bg-white: #FFFFFF;
    --primary-green: #2E7D32;
    --primary-green-light: #4CAF50;
    --primary-green-tint: #F0FDF4;
    --secondary-blue: #0288D1;
    --secondary-blue-light: #2196F3;
    --secondary-blue-tint: #F0F9FF;
    --neutral-dark: #1E293B;
    --neutral-mid: #475569;
    --neutral-light: #94A3B8;
    --border-subtle: #E2E8F0;
    --card-bg: #FFFFFF;
    --alert-red: #D32F2F;
    --alert-red-tint: #FEF2F2;
    --alert-orange: #ED6C02;
    --alert-orange-tint: #FFFBEB;
}

/* Background must be pure white */
.stApp {
    background-color: #FFFFFF !important;
    color: #1E293B !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

header[data-testid="stHeader"] {
    background-color: #FFFFFF !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #F8FAFC !important;
    border-right: 1px solid #E2E8F0 !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div {
    color: #1E293B !important;
}

/* Explicit fix for Streamlit Checkbox & Radio Labels */
div[data-testid="stCheckbox"] label,
div[data-testid="stCheckbox"] label p,
div[data-testid="stCheckbox"] label span,
div[data-baseweb="checkbox"] span {
    color: #1E293B !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

/* Clean green accent for checkboxes */
div[data-testid="stCheckbox"] input[type="checkbox"] {
    accent-color: #2E7D32 !important;
}


/* Custom Navigation & Header Bar */
.app-header {
    background: #FFFFFF;
    border-bottom: 2px solid #E2E8F0;
    padding: 18px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.brand-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #2E7D32;
    background: #F0FDF4;
    border: 1px solid #86EFAC;
    padding: 4px 12px;
    border-radius: 999px;
}

.brand-title {
    font-size: 26px;
    font-weight: 800;
    color: #1E293B;
    margin: 6px 0 2px 0;
    letter-spacing: -0.02em;
}

.brand-subtitle {
    font-size: 14px;
    color: #475569;
    margin: 0;
}

/* Primary Action Buttons strictly Fresh Green */
div.stButton > button:first-child {
    background-color: #2E7D32 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    padding: 10px 24px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(46, 125, 50, 0.2) !important;
}

div.stButton > button:first-child:hover {
    background-color: #1B5E20 !important;
    box-shadow: 0 4px 8px rgba(46, 125, 50, 0.3) !important;
    transform: translateY(-1px);
}

/* Secondary Button style */
button[kind="secondary"] {
    background-color: #FFFFFF !important;
    color: #0288D1 !important;
    border: 1px solid #0288D1 !important;
}

/* KPI Metric Cards */
.kpi-card, .metric-card {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    padding: 18px 14px !important;
    text-align: center !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04) !important;
    position: relative !important;
    overflow: hidden !important;
}

.kpi-card::before, .metric-card::before {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    height: 4px !important;
}

.kpi-card.green::before, .metric-card-green::before { background: #2E7D32 !important; }
.kpi-card.blue::before, .metric-card-blue::before { background: #0288D1 !important; }
.kpi-card.orange::before, .metric-card-orange::before { background: #ED6C02 !important; }
.kpi-card.red::before, .metric-card-red::before { background: #D32F2F !important; }

.kpi-value, .metric-val {
    font-size: 34px !important;
    font-weight: 800 !important;
    line-height: 1.15 !important;
    margin: 8px 0 !important;
}

.kpi-label, .metric-label {
    font-size: 11.5px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: #64748B !important;
}

.kpi-sub, .metric-sub {
    font-size: 12.5px !important;
    color: #475569 !important;
    margin-top: 4px !important;
}

/* Google Search Ad Simulation Preview Box */
.ad-preview-container {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px 20px;
    margin-top: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.ad-sponsor-label {
    font-size: 12px;
    font-weight: 700;
    color: #2E7D32;
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
}

.ad-url-breadcrumb {
    font-size: 12px;
    color: #475569;
    margin-bottom: 6px;
    word-break: break-all;
}

.ad-headline-preview {
    font-size: 18px;
    font-weight: 600;
    color: #0288D1;
    line-height: 1.35;
    margin-bottom: 6px;
    cursor: pointer;
}

.ad-desc-preview {
    font-size: 14px;
    color: #334155;
    line-height: 1.5;
}

/* Browser Mockup Window for HTML Landing Page */
.browser-window-bar {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-bottom: 1px solid #E2E8F0;
    border-radius: 8px 8px 0 0;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 4px;
}

.browser-dots {
    display: flex;
    gap: 6px;
    align-items: center;
}

.browser-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.browser-dot.red { background: #EF4444; }
.browser-dot.yellow { background: #F59E0B; }
.browser-dot.green { background: #10B981; }

.browser-address {
    flex: 1;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    color: #334155;
    font-family: monospace;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: 6px;
}

.browser-badge {
    font-size: 11px;
    font-weight: 700;
    color: #2E7D32;
    background: #E8F5E9;
    border: 1px solid #C8E6C9;
    padding: 2px 8px;
    border-radius: 4px;
    white-space: nowrap;
}

/* Ad Copy Specs & Breakdown Card */
.ad-breakdown-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px 16px;
    margin-top: 10px;
}

.ad-field-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 7px 0;
    border-bottom: 1px solid #F1F5F9;
    font-size: 13px;
    line-height: 1.45;
}

.ad-field-label {
    font-weight: 600;
    color: #475569;
    min-width: 95px;
    flex-shrink: 0;
}

.ad-field-value {
    color: #1E293B;
    flex-grow: 1;
    word-break: break-word;
}

.ad-char-chip {
    font-size: 11px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 8px;
    white-space: nowrap;
    flex-shrink: 0;
}

.ad-char-ok {
    background: #F0FDF4;
    color: #2E7D32;
    border: 1px solid #BBF7D0;
}

.ad-char-warn {
    background: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}

/* Section Box & Content Areas */
.content-box {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}

/* Mismatch Cards */
.mismatch-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 5px solid #ED6C02;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.mismatch-card.critical {
    border-left-color: #D32F2F;
}

.mismatch-card.moderate {
    border-left-color: #ED6C02;
}

.mismatch-card.minor {
    border-left-color: #0288D1;
}

.badge-tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 6px;
}

.badge-critical {
    background: #FEF2F2;
    color: #D32F2F;
    border: 1px solid #FECACA;
}

.badge-moderate {
    background: #FFFBEB;
    color: #B45309;
    border: 1px solid #FDE68A;
}

.badge-fold {
    background: #F0F9FF;
    color: #0288D1;
    border: 1px solid #BAE6FD;
}

.badge-verified {
    background: #F0FDF4;
    color: #166534;
    border: 1px solid #BBF7D0;
    font-weight: 700;
}

.badge-hallucination {
    background: #FEF2F2;
    color: #991B1B;
    border: 1px solid #F87171;
    font-weight: 800;
}

.badge-omission {
    background: #F8FAFC;
    color: #475569;
    border: 1px solid #CBD5E1;
}

.quote-box {
    background: #F8FAFC;
    border-left: 3px solid #0288D1;
    padding: 10px 14px;
    font-style: italic;
    font-size: 13px;
    color: #334155;
    margin: 8px 0;
    border-radius: 0 6px 6px 0;
}

.fix-box {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    padding: 12px 16px;
    border-radius: 6px;
    margin-top: 10px;
}

.fix-box-title {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    color: #2E7D32;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.fix-box-text {
    font-size: 14px;
    color: #166534;
    line-height: 1.45;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #E2E8F0;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 10px 16px;
    font-weight: 600;
    color: #64748B;
    background-color: transparent;
}

.stTabs [aria-selected="true"] {
    color: #2E7D32 !important;
    border-bottom: 3px solid #2E7D32 !important;
    background-color: #F0FDF4 !important;
}

/* Inputs & Textareas */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background-color: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    color: #1E293B !important;
    border-radius: 6px !important;
}

/* =========================================================
   MOBILE RESPONSIVENESS & UX IMPROVEMENTS
   ========================================================= */

/* Touch-friendly tap targets */
* {
    -webkit-tap-highlight-color: rgba(46, 125, 50, 0.1) !important;
    box-sizing: border-box;
}

/* Smooth scrolling */
html {
    scroll-behavior: smooth !important;
}

/* ---- GOOGLE AD CARD ---- */
.google-ad-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 14px 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    word-break: break-word;
}

.google-ad-badge-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
}

.google-ad-badge {
    font-size: 11px;
    font-weight: 700;
    color: #2E7D32;
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    padding: 1px 7px;
    border-radius: 4px;
}

.google-ad-url {
    font-size: 12px;
    color: #475569;
    word-break: break-all;
}

.google-ad-title {
    font-size: 17px;
    font-weight: 700;
    color: #0288D1;
    line-height: 1.4;
    margin-bottom: 6px;
}

.google-ad-desc {
    font-size: 13px;
    color: #334155;
    line-height: 1.55;
}

/* ---- ALERT BOXES ---- */
.alert-box {
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
    font-size: 14px;
    line-height: 1.5;
}

.alert-box-red {
    background: #FEF2F2;
    border: 1px solid #FCA5A5;
    border-left: 5px solid #D32F2F;
    color: #7F1D1D;
}

.alert-box-orange {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-left: 5px solid #ED6C02;
    color: #78350F;
}

.alert-box-green {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-left: 5px solid #2E7D32;
    color: #14532D;
}

/* ---- RESPONSIVE MEDIA QUERIES ---- */

/* Small tablets and large phones (481px - 768px) */
@media screen and (max-width: 768px) {

    /* Full-width main content on mobile */
    .main .block-container {
        padding-left: 12px !important;
        padding-right: 12px !important;
        padding-top: 8px !important;
        max-width: 100% !important;
    }

    /* Page title responsive */
    h1 {
        font-size: 20px !important;
        line-height: 1.3 !important;
    }

    h2 {
        font-size: 18px !important;
    }

    h3 {
        font-size: 16px !important;
    }

    /* Header badges stack vertically on mobile */
    div[style*="display: flex"][style*="justify-content: space-between"] {
        flex-wrap: wrap !important;
        gap: 8px !important;
    }

    /* KPI cards: 2-up grid on mobile */
    .kpi-card, .metric-card {
        padding: 14px 10px !important;
    }

    .kpi-value, .metric-val {
        font-size: 26px !important;
    }

    .kpi-label, .metric-label {
        font-size: 10px !important;
    }

    /* Ad field rows wrap on mobile */
    .ad-field-row {
        flex-wrap: wrap !important;
        gap: 4px;
    }

    .ad-field-label {
        min-width: unset !important;
        width: 100% !important;
    }

    .ad-char-chip {
        margin-left: 0 !important;
    }

    /* Browser window bar responsive */
    .browser-window-bar {
        flex-wrap: wrap !important;
        gap: 6px !important;
    }

    .browser-address {
        font-size: 11px !important;
        min-width: 0 !important;
    }

    /* Mismatch cards full width on mobile */
    .mismatch-card {
        padding: 14px 14px !important;
    }

    /* Google ad card font sizing */
    .google-ad-title {
        font-size: 15px !important;
    }

    .google-ad-desc {
        font-size: 12px !important;
    }

    /* Fix Streamlit column stacking on mobile */
    div[data-testid="column"] {
        min-width: 100% !important;
    }

    /* Fix radio buttons for horizontal layout on mobile */
    div[data-testid="stRadio"] > div {
        flex-wrap: wrap !important;
        gap: 6px !important;
    }

    /* Tab labels responsive */
    .stTabs [data-baseweb="tab"] {
        padding: 8px 10px !important;
        font-size: 12px !important;
    }

    /* Buttons full width on mobile */
    div.stButton > button:first-child {
        padding: 10px 14px !important;
        font-size: 14px !important;
    }

    /* Improve sidebar toggle visibility */
    button[data-testid="collapsedControl"] {
        background: #2E7D32 !important;
        color: white !important;
        border-radius: 0 6px 6px 0 !important;
    }

    /* Fix expander on mobile */
    details summary {
        font-size: 13px !important;
    }

    /* Number inputs better touch target */
    input[type="number"] {
        font-size: 16px !important; /* prevents iOS zoom */
    }

    /* Text inputs no zoom on focus (iOS fix) */
    input[type="text"], textarea, select {
        font-size: 16px !important;
    }
}

/* Extra small phones (max 480px) */
@media screen and (max-width: 480px) {

    .main .block-container {
        padding-left: 8px !important;
        padding-right: 8px !important;
    }

    h1 {
        font-size: 17px !important;
    }

    .kpi-value, .metric-val {
        font-size: 22px !important;
    }

    /* Fix badge row wrapping */
    div[style*="display:flex"][style*="justify-content:space-between"] {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 6px !important;
    }

    /* Tab font size */
    .stTabs [data-baseweb="tab"] {
        padding: 6px 8px !important;
        font-size: 11px !important;
    }

    /* Ad card font scaling */
    .google-ad-title {
        font-size: 14px !important;
    }

    /* Fix quote-box overflow */
    .quote-box {
        word-break: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* Fix mismatch badge overflow */
    .badge-tag {
        font-size: 10px !important;
        padding: 2px 6px !important;
    }
}

/* Large screens: max container width for readability */
@media screen and (min-width: 1400px) {
    .main .block-container {
        max-width: 1600px !important;
    }
}

/* ---- ENHANCED INTERACTIVE STATES ---- */

/* Hover animations for KPI cards */
.kpi-card:hover, .metric-card:hover {
    box-shadow: 0 6px 16px rgba(0,0,0,0.10) !important;
    transform: translateY(-2px);
    transition: all 0.2s ease !important;
}

/* Better focus states for accessibility */
input:focus, textarea:focus, select:focus {
    outline: 2px solid #2E7D32 !important;
    outline-offset: 1px !important;
    border-color: #2E7D32 !important;
}

/* Mismatch card hover */
.mismatch-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    transition: box-shadow 0.2s ease !important;
}

/* Smooth transition for all buttons */
div.stButton > button {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* ---- STREAMLIT SPINNER IMPROVEMENT ---- */
div[data-testid="stSpinner"] {
    border-radius: 8px !important;
    padding: 8px !important;
}

/* ---- PROGRESS BAR ---- */
div[data-testid="stProgress"] > div {
    background: linear-gradient(90deg, #2E7D32, #4CAF50) !important;
    border-radius: 4px !important;
}

/* ---- METRIC WIDGET ---- */
div[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    padding: 12px 14px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* ---- SIDEBAR IMPROVEMENTS ---- */
section[data-testid="stSidebar"] {
    min-width: 260px !important;
}

section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label {
    font-size: 13px !important;
    font-weight: 600 !important;
}

/* ---- EXPANDER POLISH ---- */
details {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}

details summary {
    padding: 10px 14px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    background: #F8FAFC !important;
    user-select: none;
}

details summary:hover {
    background: #F0FDF4 !important;
    color: #2E7D32 !important;
    transition: background 0.15s ease !important;
}

details[open] summary {
    border-bottom: 1px solid #E2E8F0 !important;
    color: #2E7D32 !important;
}

/* ---- OVERFLOW SAFETY ---- */
.stMarkdown, .element-container {
    overflow-wrap: break-word !important;
    word-break: break-word !important;
}

/* Fix horizontal scroll on mobile */
body {
    overflow-x: hidden !important;
}
</style>
"""
import streamlit as st

def apply_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


