import os
import json
import re
from typing import Dict, Any, List
import pandas as pd

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False


def format_landing_page_for_llm(parsed: Dict[str, Any]) -> str:
    """Format parsed HTML into an annotated structured text prompt for the auditor."""
    sections = [
        f"=== [PAGE TITLE] ===\n{parsed.get('title', '')}\n",
        f"=== [ABOVE THE FOLD - HERO SECTION] ===\n{parsed.get('hero_text', '(No hero section identified)')}\n",
        f"=== [BELOW THE FOLD - CORE SECTIONS & VALUE PROPS] ===\n{parsed.get('sections_text', '(No core sections identified)')}\n",
        f"=== [FOOTER & FINE PRINT DISCLAIMERS] ===\n{parsed.get('fine_print_text', '(No footer disclaimers identified)')}\n"
    ]
    return "\n".join(sections)


GEMINI_AUDIT_PROMPT_TEMPLATE = """
You are an Enterprise-Grade Ad-to-Landing-Page Message Match Auditor & Conversion Rate Optimization (CRO) Specialist. Your objective is to audit search ads against landing page content with absolute precision, zero hallucination, and high business impact.

--- AD COPY DETAILS ---
Advertiser: {advertiser}
Vertical: {vertical}
Headline 1: {headline_1}
Headline 2: {headline_2}
Headline 3: {headline_3}
Description 1: {description_1}
Description 2: {description_2}
Final URL: {final_url}

--- LANDING PAGE STRUCTURED CONTENT ---
{landing_page_structured}

--- AUDIT INSTRUCTIONS ---
1. CORE MESSAGE MATCH & POSITIONING AUDIT:
   - Calculate an Overall Match Score (0-100%).
   - Evaluate "Above-the-Fold" alignment (0-100%): Verify if primary ad promises exist within the Hero section without requiring scrolling.
   - Detect offer, pricing, CTA, or claim discrepancies between the ad copy and landing page sections.

2. STRICT HALLUCINATION GUARD & EXACT QUOTE EXTRACTION:
   - For every identified mismatch, extract an EXACT verbatim substring quote from the landing page.
   - If no direct match exists on the page, return "NONE". Do not paraphrase or invent quotes.
   - Mark 'is_above_the_fold_issue': true if the missing promise or disconnect pertains to the top hero section.
   - Severity: "Critical", "Moderate", or "Minor".

3. REGULATED CATEGORIES COMPLIANCE & LEGAL EXPOSURE AUDIT:
   - Identify if this vertical/advertiser is in a regulated category (Finance, Loans, Mortgages, Insurance, Healthcare, Pharma, Supplements, Legal, Crypto, Education).
   - CRITICAL COMPLIANCE FLAG: If an ad in a regulated vertical makes claims or promises (e.g. specific APR/interest rates, approval speed, guarantees, free consultations, health benefits, refund terms) that are UNSUPPORTED on the landing page (i.e. page_quote is "NONE" or contradictory), you MUST flag this as a "Regulatory Compliance Exposure".
   - Identify the governing regulatory body/policy (e.g. CFPB TILA Regulation Z, FTC Act Section 5 Deceptive Advertising, FDA, SEC, or Google Ads Misrepresentation Policy).

4. SIMPLE PLAIN ENGLISH:
   - Explain all summaries and issues in simple 5th-grade plain English so non-technical stakeholders instantly understand the impact.

5. OUTPUT FORMAT: Reply ONLY with valid JSON matching this exact structure:
{{
  "match_score": <int 0-100>,
  "score_summary": "<Explain overall match and single biggest problem in 2 simple English sentences>",
  "above_the_fold_score": <int 0-100>,
  "alignment_status": "<Perfect Alignment | High Alignment | Moderate Alignment | Severe Mismatch & Bounce Risk | Critical Compliance Exposure>",
  "compliance_audit": {{
    "is_regulated_vertical": <true|false>,
    "regulated_industry": "<e.g., Financial Services & Lending | Healthcare & Medical | Legal Services | General Commercial>",
    "compliance_risk_tier": "<Critical Regulatory Violation | Elevated Regulatory Risk | Compliant / Low Risk>",
    "governing_regulators": "<e.g., CFPB / FTC / FDA / SEC / Google Ads Misrepresentation Policy>",
    "compliance_exposure_summary": "<Explain the legal and regulatory advertising risk in 2 plain English sentences>",
    "statutory_remediation": "<Concrete step for legal/compliance team to remediate exposure>"
  }},
  "mismatches": [
    {{
      "id": 1,
      "category": "<Offer Discrepancy | Pricing & Rates | Call-to-Action (CTA) | Speed & Approval | Audience & Terms>",
      "severity": "<Critical | Moderate | Minor>",
      "is_above_the_fold_issue": <true|false>,
      "is_compliance_risk": <true|false>,
      "compliance_statute": "<e.g., CFPB Regulation Z | FTC Section 5 | FDA Medical Claims | Google Ads Policy | None>",
      "ad_claim": "<exact promise from ad>",
      "issue_description": "<simple 1-sentence explanation of the problem in plain English>",
      "page_quote": "<verbatim exact quote from landing page OR 'NONE'>",
      "suggested_fix": "<concrete rewritten recommendation in plain English>"
    }}
  ],
  "strong_matches": [
    {{
      "ad_claim": "<claim from ad>",
      "page_quote": "<exact quote from landing page>",
      "notes": "<why this aligns effectively>"
    }}
  ],
  "actionable_recommendations": [
    "<High-level strategic recommendation 1>",
    "<High-level strategic recommendation 2>"
  ]
}}
"""


def call_gemini_auditor(ad_row: pd.Series, parsed_html: Dict[str, Any], api_key: str, model_name: str = "gemini-3.7-flash") -> Dict[str, Any]:
    """Execute live Google Gemini API call with structured JSON prompting and automated resilient fallback."""
    if not GENAI_AVAILABLE:
        raise RuntimeError("google-generativeai package is not installed.")

    if not api_key or not api_key.strip():
        raise ValueError("Google Gemini API Key is required. Enter it in the sidebar.")

    genai.configure(api_key=api_key.strip())

    structured_page = format_landing_page_for_llm(parsed_html)

    prompt = GEMINI_AUDIT_PROMPT_TEMPLATE.format(
        advertiser=ad_row.get("advertiser", "Brand"),
        vertical=ad_row.get("vertical", "General Commercial"),
        headline_1=ad_row.get("headline_1", ""),
        headline_2=ad_row.get("headline_2", ""),
        headline_3=ad_row.get("headline_3", ""),
        description_1=ad_row.get("description_1", ""),
        description_2=ad_row.get("description_2", ""),
        final_url=ad_row.get("final_url", ""),
        landing_page_structured=structured_page
    )

    generation_config = {
        "temperature": 0.1,  # Low temperature for deterministic quote extraction
        "top_p": 0.95,
        "max_output_tokens": 4096,
        "response_mime_type": "application/json"
    }

    # Normalize requested model name and prepare resilient fallback hierarchy
    target_models = []
    cleaned_name = str(model_name or "").strip()
    if cleaned_name.startswith("models/"):
        cleaned_name = cleaned_name.replace("models/", "")

    if cleaned_name and cleaned_name not in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        target_models.append(cleaned_name)
    elif cleaned_name in ["gemini-2.5-flash", "gemini-2.5-pro"]:
        target_models.append("gemini-3.7-flash")

    for fallback in ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
        if fallback not in target_models:
            target_models.append(fallback)

    last_err = None
    for candidate in target_models:
        try:
            model = genai.GenerativeModel(model_name=candidate, generation_config=generation_config)
            response = model.generate_content(prompt)
            text_response = response.text.strip()

            # Clean code block backticks if present
            if text_response.startswith("```"):
                text_response = re.sub(r"^```(?:json)?\s*", "", text_response)
                text_response = re.sub(r"\s*```$", "", text_response)

            parsed_json = json.loads(text_response)
            parsed_json["_model_used"] = candidate
            return parsed_json
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            # If 404, not found, or model deprecated/unavailable, attempt next candidate
            if any(term in err_str for term in ["404", "not found", "no longer available", "deprecated", "unknown model"]):
                continue
            raise RuntimeError(f"Gemini API Execution Error: {str(e)}")

    raise RuntimeError(f"Gemini API Execution Error: {str(last_err)}")



def call_groq_auditor(
    ad_row: pd.Series,
    parsed_html: Dict[str, Any],
    api_key: str,
    model_name: str = "llama-3.3-70b-versatile"
) -> Dict[str, Any]:
    """Execute ultra-fast Groq LPU API call with structured JSON output and fallback hierarchy."""
    if not requests:
        raise RuntimeError("The 'requests' package is required to call Groq API.")

    if not api_key or not api_key.strip():
        raise ValueError("Groq API Key is required. Enter it in the sidebar or set GROQ_API_KEY.")

    structured_page = format_landing_page_for_llm(parsed_html)

    prompt = GEMINI_AUDIT_PROMPT_TEMPLATE.format(
        advertiser=ad_row.get("advertiser", "Brand"),
        vertical=ad_row.get("vertical", "General Commercial"),
        headline_1=ad_row.get("headline_1", ""),
        headline_2=ad_row.get("headline_2", ""),
        headline_3=ad_row.get("headline_3", ""),
        description_1=ad_row.get("description_1", ""),
        description_2=ad_row.get("description_2", ""),
        final_url=ad_row.get("final_url", ""),
        landing_page_structured=structured_page
    )

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }

    cleaned_name = str(model_name or "").strip()
    target_models = []
    if cleaned_name:
        target_models.append(cleaned_name)

    for fallback in ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "deepseek-r1-distill-llama-70b", "mixtral-8x7b-32768"]:
        if fallback not in target_models:
            target_models.append(fallback)

    last_err = None
    for candidate in target_models:
        payload = {
            "model": candidate,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an Enterprise-Grade Ad-to-Landing-Page Message Match Auditor & Conversion Rate Optimization (CRO) Specialist. You must output strictly valid JSON conforming exactly to the requested schema with zero markdown formatting or conversational filler."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 4096
        }

        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=45
            )

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content)
                parsed_json = json.loads(content)
                parsed_json["_model_used"] = f"groq:{candidate}"
                return parsed_json
            else:
                err_data = resp.text
                last_err = f"HTTP {resp.status_code}: {err_data}"
                if resp.status_code in [400, 404, 422]:
                    continue
                else:
                    raise RuntimeError(f"Groq API Error ({resp.status_code}): {err_data}")
        except Exception as e:
            last_err = e
            if "timeout" in str(e).lower():
                continue
            raise RuntimeError(f"Groq API Execution Error: {str(e)}")

    raise RuntimeError(f"Groq API Execution Error: {str(last_err)}")


def call_ai_auditor(
    ad_row: pd.Series,
    parsed_html: Dict[str, Any],
    api_key: str,
    model_name: str = "llama-3.3-70b-versatile",
    provider: str = "groq"
) -> Dict[str, Any]:
    """Unified entrypoint dispatching to either Groq LPU or Google Gemini based on selected provider."""
    p_lower = str(provider or "").lower()
    m_lower = str(model_name or "").lower()

    if "groq" in p_lower or any(k in m_lower for k in ["llama", "mixtral", "deepseek", "groq"]):
        return call_groq_auditor(ad_row, parsed_html, api_key, model_name)
    else:
        return call_gemini_auditor(ad_row, parsed_html, api_key, model_name)
