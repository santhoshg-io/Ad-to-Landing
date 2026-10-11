from typing import Dict, List, Any, Optional
import pandas as pd
from .config import REGULATED_VERTICALS

def evaluate_compliance_exposure(
    ad_row_or_vertical: Any,
    mismatches_or_ad_row: Any = None,
    parsed_page_or_mismatches: Any = None,
    ai_compliance: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate compliance exposure in regulated categories when ad claims are unsupported on page.
    Flags regulatory liability under FTC, CFPB, FDA, SEC, and Google Ads Misrepresentation policies.
    Guarantees zero Series truthiness ambiguity errors.
    """
    vertical_name = ""
    advertiser_name = ""
    mismatches = []
    ai_comp = None

    # Case 1: First argument is ad_row (pd.Series or dict)
    if isinstance(ad_row_or_vertical, (pd.Series, dict)):
        ad_row = ad_row_or_vertical
        try:
            val_v = ad_row.get("vertical", "")
            vertical_name = "" if pd.isna(val_v) else str(val_v)
        except Exception:
            vertical_name = ""
        try:
            val_a = ad_row.get("advertiser", "")
            advertiser_name = "" if pd.isna(val_a) else str(val_a)
        except Exception:
            advertiser_name = ""

        if isinstance(mismatches_or_ad_row, list):
            mismatches = mismatches_or_ad_row
        elif isinstance(parsed_page_or_mismatches, list):
            mismatches = parsed_page_or_mismatches

        if isinstance(ai_compliance, dict):
            ai_comp = ai_compliance
        elif isinstance(parsed_page_or_mismatches, dict):
            if "compliance_audit" in parsed_page_or_mismatches:
                ai_comp = parsed_page_or_mismatches["compliance_audit"]
            elif "is_regulated_vertical" in parsed_page_or_mismatches:
                ai_comp = parsed_page_or_mismatches

    # Case 2: First argument is vertical_name string
    else:
        vertical_name = "" if ad_row_or_vertical is None else str(ad_row_or_vertical)
        if isinstance(mismatches_or_ad_row, (pd.Series, dict)):
            try:
                val_a = mismatches_or_ad_row.get("advertiser", "")
                advertiser_name = "" if pd.isna(val_a) else str(val_a)
            except Exception:
                advertiser_name = ""
            if isinstance(parsed_page_or_mismatches, list):
                mismatches = parsed_page_or_mismatches
        elif isinstance(mismatches_or_ad_row, list):
            mismatches = mismatches_or_ad_row

        if isinstance(ai_compliance, dict):
            ai_comp = ai_compliance
        elif isinstance(parsed_page_or_mismatches, dict):
            if "compliance_audit" in parsed_page_or_mismatches:
                ai_comp = parsed_page_or_mismatches["compliance_audit"]
            elif "is_regulated_vertical" in parsed_page_or_mismatches:
                ai_comp = parsed_page_or_mismatches

    v_lower = vertical_name.lower().strip()
    adv_lower = advertiser_name.lower().strip()
    combined_context = f"{v_lower} {adv_lower}"

    matched_vertical_key = None
    matched_info = None

    for key, info in REGULATED_VERTICALS.items():
        if key in combined_context or any(kw in combined_context for kw in info.get("keywords", [])):
            matched_vertical_key = key
            matched_info = info
            break

    # If AI identified as regulated, adopt AI classification
    if not matched_info and ai_comp and ai_comp.get("is_regulated_vertical"):
        matched_vertical_key = "regulated_industry"
        matched_info = {
            "name": ai_comp.get("regulated_industry", "Regulated Industry"),
            "regulators": ai_comp.get("governing_regulators", "FTC & Regulatory Agencies"),
            "statutes": "Consumer Protection and Advertising Substantiation Regulations",
            "google_policy": "Google Ads Misrepresentation & Sensitive Category Policy",
            "statutory_risk": "Promotional discrepancies in regulated categories violate statutory disclosure mandates."
        }

    is_regulated = bool(matched_info)
    unsupported_claims = []

    for m in mismatches:
        if not isinstance(m, dict):
            continue
        page_quote = str(m.get("page_quote", "")).strip().upper()
        sev = str(m.get("severity", "Moderate")).strip()
        cat = str(m.get("category", "")).strip()

        # Flag if claim is absent (NONE) or high severity in pricing/offers
        if page_quote in ["NONE", "[NONE]", "N/A", ""] or sev.lower() == "critical" or any(c in cat for c in ["Pricing & Rates", "Offer Discrepancy", "Speed & Approval"]):
            unsupported_claims.append({
                "ad_claim": m.get("ad_claim", ""),
                "landing_page_quote": m.get("page_quote", "NONE"),
                "problem": m.get("issue_description", ""),
                "severity": sev,
                "category": cat,
                "suggested_fix": m.get("suggested_fix", "")
            })

    if is_regulated and unsupported_claims:
        risk_tier = "🚨 CRITICAL REGULATORY VIOLATION"
        risk_color = "#D32F2F"
        account_suspension_risk = "HIGH (Ad Disapproval & Google Ads Account Suspension Risk)"
    elif is_regulated:
        risk_tier = "🛡️ COMPLIANT IN REGULATED VERTICAL"
        risk_color = "#2E7D32"
        account_suspension_risk = "LOW (Claims Substantively Corroborated)"
    else:
        risk_tier = "STANDARD CRO SENSITIVITY (Non-Regulated)"
        risk_color = "#0288D1"
        account_suspension_risk = "MINIMAL (Standard Bounce Friction)"

    return {
        "is_regulated": is_regulated,
        "vertical_key": matched_vertical_key,
        "info": matched_info or {},
        "unsupported_claims": unsupported_claims,
        "unsupported_count": len(unsupported_claims),
        "risk_tier": risk_tier,
        "risk_color": risk_color,
        "account_suspension_risk": account_suspension_risk,
        "ai_summary": ai_comp.get("compliance_exposure_summary", "") if ai_comp else "",
        "statutory_remediation": ai_comp.get("statutory_remediation", "") if ai_comp else ""
    }
