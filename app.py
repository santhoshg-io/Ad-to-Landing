# Part 1: Imports and Bulk Leaderboard
import io
import json
import os
import re
import html
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    docx = None
    DOCX_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

from ui import CUSTOM_CSS, apply_custom_css
from src import (
    REGULATED_VERTICALS,
    find_dataset_paths,
    load_ads_dataset,
    extract_js_hydration_text,
    parse_landing_page_from_raw_html,
    parse_landing_page_html,
    fetch_live_url_content,
    parse_uploaded_ad_copy_file,
    normalize_text_for_search,
    verify_quote_in_landing_page,
    evaluate_compliance_exposure,
    GEMINI_AUDIT_PROMPT_TEMPLATE,
    format_landing_page_for_llm,
    call_gemini_auditor,
    generate_excel_audit_report,
    generate_docx_audit_report,
    generate_bulk_excel_report
)

st.set_page_config(
    page_title="BigBoost AI — Message Match Auditor",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_custom_css()
# Inject viewport meta for proper mobile scaling
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">', unsafe_allow_html=True)


def render_bulk_leaderboard_section(df: pd.DataFrame, snap_dir: Path, user_api_key: str, model_choice: str):
    """Render bulk dataset audit runner, portfolio KPIs, and CRO risk leaderboard."""
    st.markdown("### ⚡ Bulk Dataset Audit & CRO Risk Leaderboard")
    st.caption("Audit multiple search ad & landing page pairs simultaneously with Google Gemini. Evaluates message symmetry, checks Above-The-Fold alignment, computes wasted ad spend, flags regulated category compliance exposure, and ranks campaigns by lowest match score to surface Top Critical Risk campaigns.")

    b_col1, b_col2, b_col3, b_col4 = st.columns([1.5, 1.5, 1.2, 1.2])
    with b_col1:
        scope_options = [
            "Quick Risk Scan (First 5 Campaigns)",
            "Top Priority Batch (First 10 Campaigns)",
            "Extended Sample (First 20 Campaigns)",
            f"Full Portfolio (All {len(df)} Campaigns)"
        ]
        selected_scope = st.selectbox("Audit Scope", options=scope_options, index=0)

    with b_col2:
        st.info("🌐 **Live Destination URLs**: Anti-bot & JavaScript hydration active for all target pages.")

    with b_col3:
        bulk_monthly_spend = st.number_input(
            "Monthly Ad Spend ($)",
            min_value=500.0,
            max_value=1000000.0,
            value=10000.0,
            step=500.0,
            help="Dynamic monthly PPC budget per campaign to compute financial wasted spend."
        )

    with b_col4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        run_bulk_btn = st.button("🚀 Run Bulk Audit", use_container_width=True)

    if "First 5" in selected_scope:
        subset_df = df.head(5)
    elif "First 10" in selected_scope:
        subset_df = df.head(10)
    elif "First 20" in selected_scope:
        subset_df = df.head(20)
    else:
        subset_df = df

    if run_bulk_btn:
        if not user_api_key or not user_api_key.strip():
            st.error("Please enter a valid Google Gemini API Key in the sidebar to execute the bulk audit.")
        else:
            total_items = len(subset_df)
            bulk_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, (_, row) in enumerate(subset_df.iterrows()):
                p_id = row["pair_id"]
                adv = row["advertiser"]
                v_name = row.get("vertical", "General Commercial")
                dest_url = row.get("final_url", "")

                status_text.markdown(f"Auditing campaign **{idx+1} of {total_items}**: `{p_id}` • **{adv}**...")

                snap_file = Path(row["snapshot_file"]).name if pd.notna(row.get("snapshot_file")) and str(row.get("snapshot_file")).strip() else None
                if snap_file and snap_dir and (snap_dir / snap_file).exists():
                    parsed_p = parse_landing_page_html(snap_dir / snap_file)
                elif dest_url and not any(d in dest_url for d in [".example", "localhost", "127.0.0.1"]):
                    live_res = fetch_live_url_content(dest_url)
                    if live_res.get("success") and live_res.get("parsed"):
                        parsed_p = live_res["parsed"]
                    else:
                        parsed_p = parse_landing_page_from_raw_html("")
                else:
                    parsed_p = parse_landing_page_from_raw_html("")

                try:
                    res = call_gemini_auditor(row, parsed_p, user_api_key, model_choice)
                    m_score = int(res.get("match_score", 0))
                    fold_score = int(res.get("above_the_fold_score", 0))
                    wasted = bulk_monthly_spend * ((100.0 - m_score) / 100.0)
                    risk_tier = "Critical" if m_score < 50 else ("Moderate" if m_score <= 80 else "Low")

                    mismatches = res.get("mismatches", [])
                    crit_count = sum(1 for m in mismatches if str(m.get("severity", "")).lower() == "critical")

                    comp_exposure = evaluate_compliance_exposure(row, mismatches, parsed_p)
                    comp_flag = "⚠️ VIOLATION" if comp_exposure.get("is_regulated") and comp_exposure.get("unsupported_count", 0) > 0 else ("⚖️ Regulated" if comp_exposure.get("is_regulated") else "Standard")

                    bulk_results.append({
                        "Rank": 0,
                        "Pair ID": p_id,
                        "Advertiser": adv,
                        "Vertical": v_name,
                        "Match Score": f"{m_score}%",
                        "Score_Num": m_score,
                        "Above The Fold": f"{fold_score}%",
                        "Risk Tier": risk_tier,
                        "Monthly Waste ($)": f"${wasted:,.0f}",
                        "Waste_Num": wasted,
                        "Critical Mismatches": crit_count,
                        "Compliance Exposure": comp_flag,
                        "Primary Disconnect": res.get("score_summary", "")
                    })
                except Exception as e:
                    bulk_results.append({
                        "Rank": 0,
                        "Pair ID": p_id,
                        "Advertiser": adv,
                        "Vertical": v_name,
                        "Match Score": "ERR",
                        "Score_Num": 999,
                        "Above The Fold": "N/A",
                        "Risk Tier": "Error",
                        "Monthly Waste ($)": "$0",
                        "Waste_Num": 0,
                        "Critical Mismatches": 0,
                        "Compliance Exposure": "Error",
                        "Primary Disconnect": f"Audit Error: {str(e)}"
                    })

                progress_bar.progress((idx + 1) / total_items)

            status_text.success(f"✅ Successfully completed enterprise audit for {total_items} campaigns!")
            st.session_state["bulk_audit_results"] = bulk_results
            st.session_state["bulk_monthly_spend"] = bulk_monthly_spend

    if "bulk_audit_results" in st.session_state:
        results = st.session_state["bulk_audit_results"]
        b_df = pd.DataFrame(results)

        b_df = b_df.sort_values(by="Score_Num", ascending=True).reset_index(drop=True)
        b_df["Rank"] = [f"#{i+1}" for i in range(len(b_df))]

        valid_scores = [r["Score_Num"] for r in results if r["Score_Num"] != 999]
        valid_waste = [r["Waste_Num"] for r in results if r["Score_Num"] != 999]

        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
        total_monthly_waste = sum(valid_waste)
        annualized_waste = total_monthly_waste * 12.0

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("#### 📊 Portfolio Aggregate Financial Exposure")

        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        with mcol1:
            st.markdown(f"""
            <div class="metric-card metric-card-blue">
                <div class="metric-label">Audited Campaigns</div>
                <div class="metric-val">{len(valid_scores)}</div>
                <div class="metric-sub">Across All Selected Verticals</div>
            </div>
            """, unsafe_allow_html=True)

        with mcol2:
            st.markdown(f"""
            <div class="metric-card metric-card-blue">
                <div class="metric-label">Avg Message Match Score</div>
                <div class="metric-val">{avg_score:.1f}%</div>
                <div class="metric-sub">Portfolio Mean Symmetry</div>
            </div>
            """, unsafe_allow_html=True)

        with mcol3:
            st.markdown(f"""
            <div class="metric-card metric-card-red">
                <div class="metric-label">Monthly Wasted Spend</div>
                <div class="metric-val">${total_monthly_waste:,.0f}</div>
                <div class="metric-sub">Est. Wasted Ad Budget / Mo</div>
            </div>
            """, unsafe_allow_html=True)

        with mcol4:
            st.markdown(f"""
            <div class="metric-card metric-card-red">
                <div class="metric-label">Annualized Financial Exposure</div>
                <div class="metric-val">${annualized_waste:,.0f}</div>
                <div class="metric-sub">12-Month Projected Risk</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("#### 🏆 CRO Risk Leaderboard (Ranked by Critical Disconnect)")
        st.caption("Campaigns at the top of this leaderboard represent severe message mismatch and highest projected wasted ad spend.")

        display_cols = ["Rank", "Pair ID", "Advertiser", "Vertical", "Match Score", "Above The Fold", "Risk Tier", "Monthly Waste ($)", "Critical Mismatches", "Compliance Exposure", "Primary Disconnect"]
        st.dataframe(b_df[display_cols], use_container_width=True, hide_index=True)

        excel_bytes = generate_bulk_excel_report(b_df[display_cols])
        st.download_button(
            label="📥 Download Portfolio Leaderboard Excel Report (.xlsx)",
            data=excel_bytes,
            file_name="BigBoost_AI_Bulk_CRO_Risk_Leaderboard.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


def main():
    # --- SIDEBAR: SETTINGS & GEMINI CONFIGURATION ---
    with st.sidebar:
        st.markdown("### ⚙️ System Configuration")
        st.markdown("---")

        default_api_key = os.environ.get("GEMINI_API_KEY", "")
        if not default_api_key and "GEMINI_API_KEY" in st.secrets:
            default_api_key = st.secrets["GEMINI_API_KEY"]

        user_api_key = st.text_input(
            "Google Gemini API Key",
            value=default_api_key,
            type="password",
            help="Enter your Google Gemini API key to execute real-time audits. Get one at aistudio.google.com"
        )

        model_choice = st.selectbox(
            "Gemini Model Architecture",
            options=["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
            index=0,
            help="Select the AI reasoning engine for deterministic quote extraction and compliance analysis."
        )

        st.markdown("---")
        st.markdown("### 🏢 Enterprise Compliance")
        st.markdown("""
        <div style="font-size:12px; color:#475569; line-height:1.5;">
            <strong>Governing Frameworks:</strong><br/>
            • CFPB Regulation Z (TILA)<br/>
            • FTC Section 5 (Deceptive Ads)<br/>
            • FDA 21 CFR § 202.1<br/>
            • SEC Investment Advisers Act<br/>
            • Google Ads Misrepresentation
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.caption("BigBoost AI · Ad-to-Landing-Page Auditor v2.6 · Production")

    # --- MAIN HEADER ---
    st.markdown("""
    <div style="border-bottom: 2px solid #E2E8F0; padding-bottom: 14px; margin-bottom: 20px;">
        <div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:10px;">
            <div style="min-width:0; flex:1;">
                <h1 style="margin:0; font-size:clamp(18px,4vw,28px); font-weight:800; color:#1E293B; line-height:1.25;">
                    &#128640; BigBoost AI &#10024; Ad-to-Landing-Page Message Match Auditor
                </h1>
                <p style="margin:4px 0 0 0; font-size:clamp(11px,2vw,14px); color:#64748B; line-height:1.4;">
                    Live URL Scraper &middot; Anti-Bot &amp; JS Hydration &middot; Regulated Compliance &middot; Multi-Format Export
                </p>
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:8px; flex-shrink:0;">
                <span style="background:#F0FDF4; color:#15803D; font-weight:700; padding:5px 10px; border-radius:6px; font-size:12px; border:1px solid #BBF7D0; white-space:nowrap;">
                    &#10003; Anti-Bot Active
                </span>
                <span style="background:#F0F9FF; color:#0369A1; font-weight:700; padding:5px 10px; border-radius:6px; font-size:12px; border:1px solid #BAE6FD; white-space:nowrap;">
                    &#10003; Regulated Guard
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    ads_path, snap_dir = find_dataset_paths()
    df = load_ads_dataset(ads_path)

    mode_tab1, mode_tab2 = st.tabs([
        "🔍 Single Campaign & Live Ad Audit",
        "⚡ Bulk Portfolio Leaderboard (Batch Audit)"
    ])

    with mode_tab1:
        st.markdown("#### 📥 Ad Copy Ingestion Hub")
        st.caption("Provide search ad copy by uploading a document/spreadsheet, selecting from portfolio campaigns, or entering custom ad specs.")

        ingest_method = st.radio(
            "Ad Copy Ingestion Method",
            options=[
                "📁 Upload Ad Copy Document / Sheet (.xlsx, .csv, .docx, .txt, .json)",
                "📋 Select from Campaign Portfolio (60 Pre-loaded Pairs)",
                "✍️ Create / Customize Ad Copy Manually"
            ],
            index=0,
            horizontal=True
        )

        ingested_record: Dict[str, Any] = {}

        if "Upload Ad Copy Document" in ingest_method:
            st.markdown("<br/>", unsafe_allow_html=True)
            uploaded_ad_file = st.file_uploader(
                "Upload Ad Copy File (Excel, CSV, Word Document, Plain Text, or JSON)",
                type=["xlsx", "xls", "csv", "docx", "txt", "json"],
                help="Upload an ad copy specification sheet or document. The parser automatically extracts Headlines, Descriptions, Destination URL, Advertiser, and Vertical."
            )

            if uploaded_ad_file is not None:
                parsed_records = parse_uploaded_ad_copy_file(uploaded_ad_file.getvalue(), uploaded_ad_file.name)
                if parsed_records:
                    st.success(f"✓ Successfully ingested {len(parsed_records)} ad copy record(s) from `{uploaded_ad_file.name}`.")
                    if len(parsed_records) > 1:
                        record_labels = [f"#{i+1} • {r.get('advertiser', 'Brand')} — {r.get('headline_1', '')} | {r.get('headline_2', '')}" for i, r in enumerate(parsed_records)]
                        selected_rec_idx = st.selectbox("Select Ad Record from File", options=range(len(parsed_records)), format_func=lambda x: record_labels[x])
                        ingested_record = parsed_records[selected_rec_idx]
                    else:
                        ingested_record = parsed_records[0]
                else:
                    st.warning("Could not extract structured ad copy records from this file. You can enter details manually below.")
            else:
                st.info("👆 Upload an Excel (`.xlsx`), CSV (`.csv`), or Word Document (`.docx`) file with your Ad Copy to audit.")
                if not df.empty:
                    ingested_record = df.iloc[0].to_dict()

        elif "Select from Campaign Portfolio" in ingest_method:
            fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
            with fcol1:
                verticals = ["All Verticals"] + sorted(df["vertical"].unique().tolist())
                selected_vertical = st.selectbox("Filter by Vertical", options=verticals, key="single_filter_vertical")

            filtered_df = df if selected_vertical == "All Verticals" else df[df["vertical"] == selected_vertical]

            with fcol2:
                advertisers = ["All Brands"] + sorted(filtered_df["advertiser"].unique().tolist())
                selected_adv = st.selectbox("Filter by Brand", options=advertisers, key="single_filter_brand")

            if selected_adv != "All Brands":
                filtered_df = filtered_df[filtered_df["advertiser"] == selected_adv]

            pair_options = []
            for _, row in filtered_df.iterrows():
                p_id = row["pair_id"]
                adv = row["advertiser"]
                h1 = row["headline_1"]
                h2 = row["headline_2"]
                pair_options.append(f"{p_id} • {adv} — {h1} | {h2}")

            with fcol3:
                selected_pair_str = st.selectbox("Select Ad Pair", options=pair_options, index=0, key="single_filter_pair")

            selected_pair_id = selected_pair_str.split(" • ")[0].strip()
            selected_row_data = df[df["pair_id"] == selected_pair_id].iloc[0]
            ingested_record = selected_row_data.to_dict()

        else:
            ingested_record = {
                "pair_id": "CUSTOM_AD_01",
                "advertiser": "Custom Brand",
                "vertical": "Financial Services & Lending",
                "final_url": "https://example.com/loan-application",
                "headline_1": "Official 5.99% Fixed APR Home Loan",
                "headline_2": "Instant 24-Hour Online Pre-Approval",
                "headline_3": "Zero Hidden Fees & Fast Close",
                "description_1": "Lock in today's lowest fixed mortgage rates. Apply online in 2 minutes with no credit impact.",
                "description_2": "Compare 50+ lenders and get personalized rates. 100% transparent fee structure.",
                "path_1": "Mortgage",
                "path_2": "ApplyNow",
                "keyword": "best mortgage rates",
                "monthly_ad_spend": 15000.0,
                "cpc": 4.50
            }


        # --- DUAL-PANE INGESTION VIEW ---
        st.markdown("---")
        col_left, col_right = st.columns([1, 1], gap="medium")

        def get_field(d: Dict[str, Any], k: str, default: str = "") -> str:
            v = d.get(k, default)
            return "" if pd.isna(v) or v is None else str(v).strip()

        # LEFT COLUMN: INGESTED AD COPY & SERP PREVIEW
        with col_left:
            current_pair_id = get_field(ingested_record, 'pair_id', 'AD_01')
            st.markdown(f"#### 1. Ingested Ad Copy (`{current_pair_id}`)")

            raw_h1 = get_field(ingested_record, "headline_1", "Official Best Low Rates")
            raw_h2 = get_field(ingested_record, "headline_2", "Instant Online Approval")
            raw_h3 = get_field(ingested_record, "headline_3", "Zero Hidden Fees")
            raw_d1 = get_field(ingested_record, "description_1", "Apply online with instant verification and lowest rates guaranteed.")
            raw_d2 = get_field(ingested_record, "description_2", "Compare trusted solutions. 100% satisfaction guarantee.")
            raw_adv = get_field(ingested_record, "advertiser", "Brand Name")
            raw_vert = get_field(ingested_record, "vertical", "General Commercial")
            p1 = get_field(ingested_record, "path_1", "Apply")
            p2 = get_field(ingested_record, "path_2", "Official")
            kw = get_field(ingested_record, "keyword", "search query")
            dest_url = get_field(ingested_record, "final_url", "https://example.com")

            # Auto-sync session state whenever active pair or upload changes
            active_ad_sync_key = f"{ingest_method}_{current_pair_id}"
            vert_options = list(REGULATED_VERTICALS.keys()) + ["General Commercial"]

            if st.session_state.get("active_synced_ad_id") != active_ad_sync_key:
                st.session_state["active_synced_ad_id"] = active_ad_sync_key
                st.session_state["edit_h1"] = raw_h1
                st.session_state["edit_h2"] = raw_h2
                st.session_state["edit_h3"] = raw_h3
                st.session_state["edit_d1"] = raw_d1
                st.session_state["edit_d2"] = raw_d2
                st.session_state["edit_adv"] = raw_adv
                st.session_state["edit_vert"] = raw_vert if raw_vert in vert_options else "General Commercial"
                try:
                    st.session_state["single_monthly_spend"] = float(ingested_record.get("monthly_ad_spend", 10000.0))
                except Exception:
                    st.session_state["single_monthly_spend"] = 10000.0
                try:
                    st.session_state["single_cpc"] = float(ingested_record.get("cpc", 3.50))
                except Exception:
                    st.session_state["single_cpc"] = 3.50

            with st.expander("📝 View & Edit Ad Copy Metadata", expanded=False):
                e_h1 = st.text_input("Headline 1", key="edit_h1")
                e_h2 = st.text_input("Headline 2", key="edit_h2")
                e_h3 = st.text_input("Headline 3", key="edit_h3")
                e_d1 = st.text_area("Description 1", key="edit_d1")
                e_d2 = st.text_area("Description 2", key="edit_d2")
                e_adv = st.text_input("Brand / Advertiser", key="edit_adv")
                e_vert = st.selectbox("Vertical Classification", options=vert_options, key="edit_vert")

                ingested_record["headline_1"] = e_h1
                ingested_record["headline_2"] = e_h2
                ingested_record["headline_3"] = e_h3
                ingested_record["description_1"] = e_d1
                ingested_record["description_2"] = e_d2
                ingested_record["advertiser"] = e_adv
                ingested_record["vertical"] = e_vert

            # Dynamically reflect active edited values in SERP preview
            active_h1 = e_h1 if e_h1 is not None else raw_h1
            active_h2 = e_h2 if e_h2 is not None else raw_h2
            active_h3 = e_h3 if e_h3 is not None else raw_h3
            active_d1 = e_d1 if e_d1 is not None else raw_d1
            active_d2 = e_d2 if e_d2 is not None else raw_d2

            display_url = dest_url.replace("https://", "").replace("http://", "").rstrip("/")
            if p1:
                display_url += f"/{p1}"
            if p2:
                display_url += f"/{p2}"

            st.markdown(f"""
            <div class="google-ad-card">
                <div class="google-ad-badge-row">
                    <span class="google-ad-badge">Sponsored</span>
                    <span class="google-ad-url">{display_url}</span>
                </div>
                <div class="google-ad-title">
                    {html.escape(active_h1)} | {html.escape(active_h2)}{f' | {html.escape(active_h3)}' if active_h3 else ''}
                </div>
                <div class="google-ad-desc">
                    {html.escape(active_d1)} {html.escape(active_d2)}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("##### 💰 Campaign Budget & Traffic Modeling")
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                monthly_spend = st.number_input(
                    "Monthly PPC Budget ($)",
                    min_value=100.0,
                    max_value=1000000.0,
                    step=500.0,
                    key="single_monthly_spend"
                )
            with bcol2:
                cpc = st.number_input(
                    "Average CPC ($)",
                    min_value=0.10,
                    max_value=200.0,
                    step=0.25,
                    key="single_cpc"
                )

        # RIGHT COLUMN: DESTINATION LANDING PAGE CONTENT & LIVE PREVIEW
        with col_right:
            is_portfolio_mode = "Select from Campaign Portfolio" in ingest_method
            snap_file = Path(ingested_record.get("snapshot_file", "")).name if ingested_record.get("snapshot_file") else None
            has_snapshot = bool(snap_file and snap_dir and (snap_dir / snap_file).exists())
            target_live_url = dest_url

            if is_portfolio_mode and has_snapshot:
                # -------------------------------------------------------------
                # 1. PORTFOLIO DATASET MODE: DIRECT OFFLINE HTML WITH WEBSITE PREVIEW (NO OVERRIDE PROMPT)
                # -------------------------------------------------------------
                st.markdown(f"#### 2. Destination Landing Page (`{snap_file}`)")
                parsed_page = parse_landing_page_html(snap_dir / snap_file)

                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:10px 14px; margin-top:4px; margin-bottom:12px; font-size:12.5px; color:#166534; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                    <div>
                        <strong>✓ Offline Dataset Snapshot:</strong> <code>{snap_file}</code> · Direct Local File Access
                    </div>
                    <span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #86EFAC;">
                        📁 Zero-Latency Local DOM
                    </span>
                </div>
                """, unsafe_allow_html=True)

            else:
                # -------------------------------------------------------------
                # 2. UPLOAD / CUSTOM MODE: ASK FOR LIVE DESTINATION URL
                # -------------------------------------------------------------
                st.markdown("#### 2. Live Destination Landing Page URL & Engine")

                initial_url = dest_url if dest_url and not any(d in dest_url for d in [".example", "localhost"]) else ""
                target_live_url = st.text_input(
                    "Live Destination Landing Page URL",
                    value=initial_url,
                    placeholder="https://yourbrand.com/landing-page",
                    key="target_live_url_input",
                    help="Fetches live HTML directly over HTTP, bypasses bot blocks via Chrome 124 headers, and recovers JavaScript hydration state (Next.js/Nuxt.js/JSON-LD)."
                )

                fetch_url_btn = st.button("🔄 Fetch & Render Live URL Now", use_container_width=True)
                cache_key = f"live_fetch_{target_live_url}"

                if target_live_url and (fetch_url_btn or cache_key in st.session_state):
                    if fetch_url_btn or cache_key not in st.session_state:
                        with st.spinner(f"Fetching live URL: {target_live_url} (Bypassing bot blocks & parsing JS hydration)..."):
                            live_res = fetch_live_url_content(target_live_url)
                            st.session_state[cache_key] = live_res

                    live_res = st.session_state.get(cache_key, {})
                    if live_res.get("success") and live_res.get("parsed"):
                        parsed_page = live_res["parsed"]
                        meta = live_res.get("meta", {})
                        st.markdown(f"""
                        <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:8px 12px; margin-top:8px; margin-bottom:12px; font-size:12.5px; color:#166534; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                            <div>
                                <strong>✓ Live URL Rendered:</strong> HTTP {meta.get('status_code', 200)} OK · 
                                Framework: <code>{meta.get('framework', 'HTML')}</code> · 
                                Payload: {meta.get('size_kb', 0):.1f} KB
                            </div>
                            <span style="background:#DCFCE7; color:#15803D; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #86EFAC;">
                                🛡️ Anti-Bot Bypassed (Chrome 124)
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        parsed_page = {
                            "title": "Live Target Page",
                            "hero_text": "(Could not fetch live content)",
                            "sections_text": "(Could not fetch live content)",
                            "fine_print_text": "(No fine print)",
                            "raw_full_text": "",
                            "raw_html": f"<div style='padding:24px; font-family:sans-serif;'><h3>Unable to render live page</h3><p>{html.escape(live_res.get('error', 'Please check the URL.'))}</p></div>",
                            "js_hydration": {"has_hydration": False, "framework": "Static HTML"}
                        }
                        if target_live_url:
                            st.warning(f"⚠️ Live URL notice: {live_res.get('error', 'Unable to fetch.')}")
                else:
                    parsed_page = {
                        "title": "Enter Live Destination URL",
                        "hero_text": "(Awaiting URL fetch)",
                        "sections_text": "(Awaiting URL fetch)",
                        "fine_print_text": "(Awaiting URL fetch)",
                        "raw_full_text": "",
                        "raw_html": "<div style='padding:28px; font-family:sans-serif; text-align:center; color:#64748B;'><h3>🌐 Awaiting Live Destination URL</h3><p>Enter your website landing page URL above and click <strong>Fetch & Render Live URL Now</strong> to preview.</p></div>",
                        "js_hydration": {"has_hydration": False, "framework": "Static HTML"}
                    }

            # -------------------------------------------------------------
            # DUAL TABS: INTERACTIVE WEBSITE PREVIEW & EXTRACTED STRUCTURED TEXT
            # -------------------------------------------------------------
            view_tabs = st.tabs(["🌐 Interactive Website Preview", "📝 Extracted Structured Text"])

            with view_tabs[0]:
                raw_html_content = parsed_page.get("raw_html", "")
                if raw_html_content:
                    badge_label = f"● Snapshot: {html.escape(snap_file)}" if (is_portfolio_mode and snap_file) else f"● Live URL: {html.escape(target_live_url or 'Target')}"
                    display_address = html.escape(dest_url or target_live_url or "https://landing-page.com")
                    st.markdown(f"""
                    <div class="browser-window-bar">
                        <div class="browser-dots">
                            <span class="browser-dot red"></span>
                            <span class="browser-dot yellow"></span>
                            <span class="browser-dot green"></span>
                        </div>
                        <div class="browser-address">
                            <span style="color:#10B981;">🔒</span> {display_address}
                        </div>
                        <span class="browser-badge">{badge_label}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.iframe(raw_html_content, height=540)
                else:
                    st.info("Interactive HTML preview is unavailable or awaiting content.")

            with view_tabs[1]:
                st.markdown(f"**Page Title:** `{parsed_page.get('title', 'N/A')}`")

                with st.expander("👁️ Hero Section (Above-the-Fold Content)", expanded=True):
                    st.write(parsed_page.get("hero_text", "(No hero section extracted)"))

                with st.expander("📄 Core Value Props & Below-the-Fold Content", expanded=False):
                    st.write(parsed_page.get("sections_text", "(No core sections extracted)"))

                with st.expander("⚖️ Disclaimers & Fine Print", expanded=False):
                    st.write(parsed_page.get("fine_print_text", "(No fine print extracted)"))


        # --- EXECUTION BUTTON ---
        st.markdown("---")
        run_col1, run_col2 = st.columns([3, 1])
        with run_col1:
            st.markdown("##### 🚀 Execute AI Message Match & Compliance Audit")
            st.caption("Runs Google Gemini LLM against the ingested ad copy and live-rendered landing page sections with deterministic quote verification.")
        with run_col2:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            run_audit_btn = st.button("🚀 Run AI Audit", type="primary", use_container_width=True)

        if run_audit_btn:
            if not user_api_key or not user_api_key.strip():
                st.error("❌ Google Gemini API Key required. Please enter your key in the sidebar.")
            else:
                audit_ad_row = pd.Series(ingested_record)
                audit_ad_row["final_url"] = target_live_url

                with st.spinner("🤖 Running Gemini AI Auditor (Analyzing Message Symmetry, Above-the-Fold Alignment & Regulated Compliance)..."):
                    try:
                        audit_result = call_gemini_auditor(audit_ad_row, parsed_page, user_api_key, model_choice)
                        st.session_state[f"audit_res_{get_field(ingested_record, 'pair_id')}"] = audit_result
                        st.session_state[f"audit_row_{get_field(ingested_record, 'pair_id')}"] = audit_ad_row
                        st.session_state[f"audit_page_{get_field(ingested_record, 'pair_id')}"] = parsed_page
                        st.success("✅ Audit completed successfully!")
                    except Exception as e:
                        st.error(f"❌ Audit execution failed: {str(e)}")

        # --- DISPLAY AUDIT RESULTS ---
        active_audit_key = f"audit_res_{get_field(ingested_record, 'pair_id')}"
        if active_audit_key in st.session_state:
            res = st.session_state[active_audit_key]
            audit_row = st.session_state[f"audit_row_{get_field(ingested_record, 'pair_id')}"]
            audit_page = st.session_state[f"audit_page_{get_field(ingested_record, 'pair_id')}"]

            st.markdown("---")
            st.markdown("## 📊 Comprehensive Audit Findings & AI Decisions")

            match_score = int(res.get("match_score", 0))
            fold_score = int(res.get("above_the_fold_score", 0))
            alignment_status = res.get("alignment_status", "Audited")
            summary = res.get("score_summary", "")

            wasted_spend = monthly_spend * ((100.0 - match_score) / 100.0)
            annual_wasted = wasted_spend * 12.0
            daily_wasted = wasted_spend / 30.4

            verified_count = 0
            hallucination_count = 0
            omission_count = 0

            raw_mismatches = res.get("mismatches", [])
            processed_mismatches = []
            for m in raw_mismatches:
                quote = m.get("page_quote", "")
                v_res = verify_quote_in_landing_page(quote, audit_page)
                v_status = v_res.get("status", "UNCHECKED")
                if v_status == "VERIFIED":
                    verified_count += 1
                elif v_status == "HALLUCINATED":
                    hallucination_count += 1
                elif v_status in ["OMISSION_NOTED", "NONE"]:
                    omission_count += 1
                m_copy = dict(m)
                m_copy["verification"] = v_res
                processed_mismatches.append(m_copy)

            num_critical = sum(1 for m in processed_mismatches if str(m.get("severity", "")).lower() == "critical")
            strong_matches = res.get("strong_matches", [])
            recommendations = res.get("actionable_recommendations", [])
            comp_exposure = evaluate_compliance_exposure(audit_row, processed_mismatches, res.get("compliance_audit", {}))

            # Style score color
            if match_score >= 80:
                score_class = "green"
                score_color = "#2E7D32"
            elif match_score >= 50:
                score_class = "blue"
                score_color = "#0288D1"
            else:
                score_class = "red"
                score_color = "#D32F2F"

            # 4 TOP-LEVEL KPI METRIC CARDS (LIKE BEFORE)
            mcol1, mcol2, mcol3, mcol4 = st.columns([1, 1, 1, 1], gap="small")

            with mcol1:
                st.markdown(f"""
                <div class="kpi-card {score_class}">
                    <div class="kpi-label">Overall Match Score</div>
                    <div class="kpi-value" style="color: {score_color};">{match_score}%</div>
                    <div class="kpi-sub"><strong>{alignment_status}</strong></div>
                </div>
                """, unsafe_allow_html=True)

            with mcol2:
                fold_class = "green" if fold_score >= 75 else ("blue" if fold_score >= 45 else "orange")
                fold_color = "#2E7D32" if fold_score >= 75 else ("#0288D1" if fold_score >= 45 else "#ED6C02")
                st.markdown(f"""
                <div class="kpi-card {fold_class}">
                    <div class="kpi-label">Above-The-Fold Match</div>
                    <div class="kpi-value" style="color: {fold_color};">{fold_score}%</div>
                    <div class="kpi-sub">Hero Viewport Alignment</div>
                </div>
                """, unsafe_allow_html=True)

            with mcol3:
                crit_class = "red" if num_critical > 0 else ("orange" if len(processed_mismatches) > 0 else "green")
                crit_color = "#D32F2F" if num_critical > 0 else ("#ED6C02" if len(processed_mismatches) > 0 else "#2E7D32")
                st.markdown(f"""
                <div class="kpi-card {crit_class}">
                    <div class="kpi-label">Mismatches Found</div>
                    <div class="kpi-value" style="color: {crit_color};">{len(processed_mismatches)}</div>
                    <div class="kpi-sub">{num_critical} Critical Disconnects</div>
                </div>
                """, unsafe_allow_html=True)

            with mcol4:
                hall_class = "red" if hallucination_count > 0 else "green"
                hall_color = "#D32F2F" if hallucination_count > 0 else "#2E7D32"
                st.markdown(f"""
                <div class="kpi-card {hall_class}">
                    <div class="kpi-label">Hallucination Guard</div>
                    <div class="kpi-value" style="color: {hall_color};">{hallucination_count}</div>
                    <div class="kpi-sub">{verified_count} Quotes Verified in Source</div>
                </div>
                """, unsafe_allow_html=True)

            # Prominent Regulated Category Compliance Exposure Alert Banner
            if comp_exposure.get("is_regulated") and comp_exposure.get("unsupported_count", 0) > 0:
                v_info = comp_exposure.get("info", {})
                st.markdown(f"""
                <div style="background:#FEF2F2; border:2px solid #EF4444; border-radius:8px; padding:16px 20px; margin:16px 0;">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; flex-wrap:wrap; gap:8px;">
                        <div style="font-size:16px; font-weight:800; color:#B91C1C; display:flex; align-items:center; gap:8px;">
                            <span>⚖️</span> REGULATORY COMPLIANCE EXPOSURE IN REGULATED CATEGORY
                        </div>
                        <span style="background:#B91C1C; color:#FFFFFF; font-size:11px; font-weight:700; padding:4px 10px; border-radius:4px; text-transform:uppercase;">
                            {comp_exposure['risk_tier']}
                        </span>
                    </div>
                    <div style="font-size:13.5px; color:#7F1D1D; line-height:1.55;">
                        <strong>Regulated Category:</strong> {v_info.get('name', 'Regulated Industry')}<br/>
                        <strong>Governing Regulators:</strong> {v_info.get('regulators', 'FTC, CFPB, FDA, SEC')}<br/>
                        <strong>Statutory References:</strong> {v_info.get('statutes', 'FTC Act Section 5')}<br/>
                        <strong>Ad Policy Exposure:</strong> {comp_exposure.get('account_suspension_risk', 'High')}<br/>
                        <div style="margin-top:10px; background:#FFFFFF; padding:12px 14px; border-radius:6px; border:1px solid #FCA5A5; color:#991B1B; font-size:13px;">
                            ⚠️ <strong>Enforcement Exposure:</strong> {comp_exposure['unsupported_count']} claim(s) appearing in this ad copy (pricing, interest rates, approvals, or guarantees) are <strong>completely unsupported on the destination page ('NONE')</strong>. In regulated categories, promoting uncorroborated claims represents an actionable regulatory violation under FTC and statutory mandates, triggering immediate Google Ads disapproval and account suspension.
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif comp_exposure.get("is_regulated"):
                v_info = comp_exposure.get("info", {})
                st.markdown(f"""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px 18px; margin:14px 0;">
                    <span style="font-weight:700; color:#166534;">🛡️ REGULATORY COMPLIANCE STATUS:</span> 
                    <span style="color:#15803D;">Regulated Category ({v_info.get('name', 'Regulated')}) · All ad copy claims are substantively supported on the destination page with zero unverified claims.</span>
                </div>
                """, unsafe_allow_html=True)

            # ==============================================================================
            # PILLAR 3: DYNAMIC FINANCIAL WASTED SPEND CALCULATOR
            # ==============================================================================
            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("### 💰 Dynamic Financial Wasted Spend Calculator")
            st.caption("Calculate monthly and annualized PPC ad budget exposure based on the formula: **Wasted Spend ($) = Monthly Ad Spend × ((100 - Match Score) / 100)**.")

            fin_col1, fin_col2, fin_col3 = st.columns([1.1, 1.1, 0.8], gap="small")
            with fin_col1:
                single_monthly_spend = st.number_input(
                    "Monthly PPC Ad Spend ($)",
                    min_value=100.0,
                    max_value=2000000.0,
                    value=float(monthly_spend),
                    step=500.0,
                    key="single_monthly_spend_calc"
                )

            wasted_spend = single_monthly_spend * ((100.0 - match_score) / 100.0)
            annual_wasted = wasted_spend * 12.0
            daily_wasted = wasted_spend / 30.4
            risk_level = "Critical (<50%)" if match_score < 50 else ("Moderate (50-80%)" if match_score <= 80 else "Low (>80%)")
            risk_color = "#D32F2F" if match_score < 50 else ("#ED6C02" if match_score <= 80 else "#2E7D32")
            risk_bg = "#FEF2F2" if match_score < 50 else ("#FFFBEB" if match_score <= 80 else "#F0FDF4")
            risk_border = "#FCA5A5" if match_score < 50 else ("#FDE68A" if match_score <= 80 else "#BBF7D0")

            with fin_col2:
                st.markdown(f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:12px; text-align:center;">
                    <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">Monthly Wasted Spend</div>
                    <div style="font-size:24px; font-weight:800; color:#D32F2F; margin:4px 0;">${wasted_spend:,.2f}</div>
                    <div style="font-size:12px; color:#64748B;">${annual_wasted:,.2f}/yr at risk</div>
                </div>
                """, unsafe_allow_html=True)

            with fin_col3:
                st.markdown(f"""
                <div style="background:{risk_bg}; border:1px solid {risk_border}; border-radius:8px; padding:12px; text-align:center;">
                    <div style="font-size:11px; font-weight:700; color:#64748B; text-transform:uppercase;">CRO Risk Tier</div>
                    <div style="font-size:20px; font-weight:800; color:{risk_color}; margin:6px 0;">{risk_level}</div>
                    <div style="font-size:12px; color:#475569;">Formula: Spend × (100 - Score)%</div>
                </div>
                """, unsafe_allow_html=True)

            # Financial Narrative Callout
            if match_score < 50:
                st.error(f"🚨 **CRITICAL FINANCIAL RISK:** At ${single_monthly_spend:,.2f}/month budget and a {match_score}% Match Score, **${wasted_spend:,.2f}** is wasted every single month (**${annual_wasted:,.2f} annually**). The primary ad promise does not appear prominently above the fold, inducing high immediate bounce rates.")
            elif match_score <= 80:
                st.warning(f"⚠️ **MODERATE FINANCIAL EXPOSURE:** At ${single_monthly_spend:,.2f}/month budget, **${wasted_spend:,.2f}/month** (**${annual_wasted:,.2f}/year**) is underperforming due to partial message friction. Alignment optimizations will immediately lift conversion efficiency.")
            else:
                st.success(f"✓ **EFFICIENT BUDGET UTILIZATION:** Strong message symmetry ({match_score}%). Financial leakage is minimized at only **${wasted_spend:,.2f}/month**.")

            # Summary box
            st.markdown("<br/>", unsafe_allow_html=True)
            st.markdown("### 📌 Executive Audit Summary")
            with st.container(border=True):
                st.markdown(f"**Overall System Verdict:** `{alignment_status}` (**{match_score}%** Match · Above-the-Fold: **{fold_score}%**)")
                st.write(summary)

            comp_cnt = comp_exposure.get("unsupported_count", 0)
            comp_tab_title = f"⚖️ Compliance Exposure ({comp_cnt})" if comp_exposure.get("is_regulated") else "⚖️ Compliance Exposure"

            tab_mismatches, tab_compliance, tab_strong, tab_actions, tab_export = st.tabs([
                f"🚨 Identified Mismatches ({len(processed_mismatches)})",
                comp_tab_title,
                f"✅ Confirmed Matches ({len(strong_matches)})",
                "🛠️ Actionable Recommendations",
                "📋 Audit Data & Export"
            ])

            with tab_mismatches:
                if not processed_mismatches:
                    st.success("🎉 Outstanding message symmetry! Zero mismatches detected between this ad copy and landing page.")
                else:
                    st.caption("Every mismatch below cites supporting landing page text and has been checked by the programmatic hallucination verification engine.")

                    for item in processed_mismatches:
                        severity = item.get("severity", "Moderate")
                        category = item.get("category", "General")
                        ad_claim = item.get("ad_claim", "")
                        issue = item.get("issue_description", "")
                        page_quote = item.get("page_quote", "")
                        suggested_fix = item.get("suggested_fix", "")
                        is_fold = item.get("is_above_the_fold_issue", False)
                        v_res = item["verification"]
                        v_status = v_res["status"]

                        if str(severity).lower() == "critical":
                            s_badge = "<span style='background:#FEE2E2; color:#B91C1C; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #FCA5A5;'>CRITICAL</span>"
                        elif str(severity).lower() == "moderate":
                            s_badge = "<span style='background:#FEF3C7; color:#B45309; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #FDE68A;'>MODERATE</span>"
                        else:
                            s_badge = "<span style='background:#E0F2FE; color:#0369A1; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #BAE6FD;'>MINOR</span>"

                        fold_badge = "<span style='background:#FEF2F2; color:#991B1B; font-weight:600; padding:2px 6px; border-radius:4px; font-size:11px;'>⚠️ ABOVE-THE-FOLD DISCONNECT</span>" if is_fold else ""

                        match_ratio = float(v_res.get("match_ratio", 1.0 if v_status == "VERIFIED" else 0.0))
                        if v_status == "VERIFIED":
                            v_badge = f"<span style='background:#DCFCE7; color:#15803D; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #86EFAC;'>✓ EXACT QUOTE VERIFIED ({match_ratio:.0%})</span>"
                        elif v_status in ["OMISSION_NOTED", "NONE"]:
                            v_badge = "<span style='background:#FEE2E2; color:#991B1B; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #FCA5A5;'>✗ CLAIM MISSING FROM PAGE (NONE)</span>"
                        else:
                            v_badge = f"<span style='background:#FEF3C7; color:#B45309; font-weight:700; padding:2px 8px; border-radius:4px; font-size:11px; border:1px solid #FDE68A;'>⚠️ UNVERIFIED QUOTE ({match_ratio:.0%})</span>"

                        with st.container(border=True):
                            st.markdown(f"""
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <div>
                                    {s_badge} &nbsp; <strong>Category:</strong> {category} &nbsp; {fold_badge}
                                </div>
                                <div>{v_badge}</div>
                            </div>
                            """, unsafe_allow_html=True)

                            st.markdown(f"**Ad Copy Promise:** `{ad_claim}`")
                            st.markdown(f"**Identified Issue:** {issue}")

                            if page_quote and page_quote != "NONE":
                                st.markdown(f"**Landing Page Quote (Verbatim):** *\"{page_quote}\"*")
                            else:
                                st.markdown("**Landing Page Quote:** *(No supporting statement found on landing page)*")

                            st.markdown(f"💡 **Recommended Fix:** {suggested_fix}")

            with tab_compliance:
                is_reg = comp_exposure.get("is_regulated", False)
                info = comp_exposure.get("info", {})
                risk_tier = comp_exposure.get("risk_tier", "Standard")
                unsupported_claims = comp_exposure.get("unsupported_claims", [])
                suspension_risk = comp_exposure.get("account_suspension_risk", "Low")

                if not is_reg:
                    st.info("ℹ️ **Standard Commercial Vertical:** This campaign does not fall under heavily regulated advertising statutes (CFPB, FDA, SEC, TILA). Standard FTC Truth-in-Advertising and Google Ads quality policies apply.")
                else:
                    st.markdown(f"### ⚖️ Regulatory Compliance & Legal Exposure Audit: `{info.get('name', 'Regulated Vertical')}`")

                    if comp_exposure.get("unsupported_count", 0) > 0:
                        st.markdown(f"""
                        <div class="alert-box alert-box-red">
                            <div style="font-size:16px; font-weight:800; margin-bottom:4px;">
                                🚨 CRITICAL COMPLIANCE EXPOSURE DETECTED ({comp_exposure.get('unsupported_count', 0)} Unsupported Ad Claims)
                            </div>
                            <div>
                                This ad operates in <strong>{info.get('name')}</strong> and makes promises or terms that have <strong>ZERO substantiation on the destination landing page</strong>.
                                Under <strong>{info.get('statutes')}</strong>, advertising terms not substantiated on the landing page constitutes deceptive advertising.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    c_c1, c_c2, c_c3 = st.columns(3)
                    with c_c1:
                        st.markdown(f"""
                        <div class="metric-card {'metric-card-red' if 'High' in risk_tier or 'Critical' in risk_tier else 'metric-card-blue'}">
                            <div class="metric-label">Compliance Risk Tier</div>
                            <div class="metric-val" style="font-size:18px;">{risk_tier}</div>
                            <div class="metric-sub">{info.get('name', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with c_c2:
                        st.markdown(f"""
                        <div class="metric-card metric-card-blue">
                            <div class="metric-label">Governing Regulators</div>
                            <div class="metric-val" style="font-size:16px;">{info.get('regulators', 'FTC')}</div>
                            <div class="metric-sub">{info.get('statutes', '')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with c_c3:
                        st.markdown(f"""
                        <div class="metric-card {'metric-card-red' if 'High' in suspension_risk else 'metric-card-blue'}">
                            <div class="metric-label">Google Ads Policy Risk</div>
                            <div class="metric-val" style="font-size:16px;">{suspension_risk}</div>
                            <div class="metric-sub">{info.get('google_policy', 'Misrepresentation')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<br/>", unsafe_allow_html=True)
                    st.markdown("#### 🚨 Unsupported Ad Claims Subject to Enforcement Action")
                    if unsupported_claims:
                        for idx, uc in enumerate(unsupported_claims, 1):
                            with st.container(border=True):
                                st.markdown(f"**Violation #{idx}:** `{uc.get('ad_claim', '')}`")
                                st.markdown(f"• **Statutory Concern:** {uc.get('issue_description', '')}")
                                st.markdown(f"• **Governing Policy:** `{uc.get('compliance_statute', info.get('statutes', 'FTC Section 5'))}`")
                                st.markdown(f"• **Remediation:** {uc.get('suggested_fix', '')}")
                    else:
                        st.success("✓ All ad claims in this regulated vertical have verified supporting disclosures on the destination page.")

            with tab_strong:
                if not strong_matches:
                    st.info("No verified strong matches recorded for this pair.")
                else:
                    for sm in strong_matches:
                        with st.container(border=True):
                            st.markdown(f"**Ad Copy Claim:** `{sm.get('ad_claim', '')}`")
                            st.markdown(f"**Verified Landing Page Text:** *\"{sm.get('page_quote', '')}\"*")
                            st.markdown(f"**Analysis:** {sm.get('notes', 'Strong verbatim message alignment.')}")

            with tab_actions:
                if not recommendations:
                    st.info("No strategic fixes required.")
                else:
                    for idx, rec in enumerate(recommendations, 1):
                        with st.container(border=True):
                            st.markdown(f"**Step {idx}:** {rec}")

            with tab_export:
                st.markdown("### 📥 Export Audit Reports")
                st.caption("Generate presentation-ready audit deliverables in multiple file formats for executive and compliance stakeholders.")

                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    excel_data = generate_excel_audit_report(
                        res,
                        audit_row,
                        processed_mismatches,
                        strong_matches,
                        recommendations,
                        monthly_spend=monthly_spend,
                        compliance_data=comp_exposure
                    )
                    st.download_button(
                        label="📊 Download Multi-Sheet Excel Report (.xlsx)",
                        data=excel_data,
                        file_name=f"BigBoost_AI_Audit_{get_field(ingested_record, 'pair_id')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                with exp_col2:
                    docx_data = generate_docx_audit_report(
                        res,
                        audit_row,
                        processed_mismatches,
                        strong_matches,
                        recommendations,
                        monthly_spend=monthly_spend,
                        compliance_data=comp_exposure
                    )
                    st.download_button(
                        label="📄 Download Word Document Report (.docx)",
                        data=docx_data,
                        file_name=f"BigBoost_AI_Audit_{get_field(ingested_record, 'pair_id')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )

                st.markdown("<br/>", unsafe_allow_html=True)
                with st.expander("📋 View Raw JSON Response", expanded=False):
                    st.json(res)

    with mode_tab2:
        render_bulk_leaderboard_section(df, snap_dir, user_api_key, model_choice)


if __name__ == "__main__":
    main()
