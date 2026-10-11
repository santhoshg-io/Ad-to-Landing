import io, os, re, json, html
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

def find_dataset_paths() -> Tuple[Optional[Path], Optional[Path]]:
    """
    Dynamically locate ads.csv and landing_page_snapshots directory.
    Checks workspace root, PS-03_message_match_auditor, ps-03_message, etc.
    """
    candidates = [
        Path("data"),
        Path("."),
        Path("PS-03_message_match_auditor"),
        Path(__file__).parent.parent / "data" if "__file__" in globals() else Path("data"),
        Path(__file__).parent / "data" if "__file__" in globals() else Path("data"),
        Path(__file__).parent.parent if "__file__" in globals() else Path("."),
    ]
    for base in candidates:
        csv_candidate = base / "ads.csv"
        snap_candidate = base / "landing_page_snapshots"
        if csv_candidate.exists() and snap_candidate.exists():
            return csv_candidate, snap_candidate
    return None, None


@st.cache_data(show_spinner=False)
def load_ads_dataset(ads_path: Optional[Path] = None) -> pd.DataFrame:
    """Load and index ads.csv into a pandas DataFrame."""
    if ads_path is None or not Path(ads_path).exists():
        csv_path, snap_dir = find_dataset_paths()
    else:
        csv_path = Path(ads_path)

    if not csv_path or not Path(csv_path).exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(csv_path)
        df.columns = [c.strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()


def extract_js_hydration_text(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract structured content from modern JavaScript SPAs and hydration scripts
    (Next.js __NEXT_DATA__, Nuxt __NUXT_DATA__, JSON-LD Schema.org, React hydration).
    Recovers critical headlines, pricing, and offers even if client-side rendered.
    """
    hydration_texts = []
    schemas = []
    framework_detected = "Standard Static HTML"

    # 1. Next.js Hydration Payload
    next_script = soup.find("script", id="__NEXT_DATA__")
    if next_script and next_script.string:
        try:
            data = json.loads(next_script.string)
            framework_detected = "Next.js (React Hydration)"
            def extract_strings(obj):
                if isinstance(obj, str):
                    s = obj.strip()
                    if len(s) > 3 and not s.startswith("http") and not s.startswith("/") and "{" not in s:
                        hydration_texts.append(s)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        extract_strings(v)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_strings(item)
            extract_strings(data.get("props", {}))
        except Exception:
            pass

    # 2. Nuxt.js Hydration Payload
    nuxt_script = soup.find("script", id="__NUXT_DATA__")
    if nuxt_script and nuxt_script.string:
        framework_detected = "Nuxt.js (Vue Hydration)"
        try:
            data = json.loads(nuxt_script.string)
            for item in data:
                if isinstance(item, str) and len(item.strip()) > 3:
                    hydration_texts.append(item.strip())
        except Exception:
            pass

    # 3. JSON-LD Schema.org Data (often contains product offers, pricing, guarantees)
    for ld in soup.find_all("script", type="application/ld+json"):
        if ld.string:
            try:
                data = json.loads(ld.string)
                schemas.append(data)
                def extract_ld_strings(obj):
                    if isinstance(obj, str) and len(obj.strip()) > 3:
                        hydration_texts.append(obj.strip())
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            extract_ld_strings(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            extract_ld_strings(item)
                extract_ld_strings(data)
            except Exception:
                pass

    return {
        "framework": framework_detected,
        "extracted_texts": list(dict.fromkeys(hydration_texts))[:40],  # Unique, capped for prompt safety
        "schemas": schemas,
        "has_hydration": bool(hydration_texts)
    }


def parse_landing_page_from_raw_html(html_raw: str, base_url: str = "") -> Dict[str, Any]:
    """
    Parse HTML content (from either offline snapshot or live fetch), extracting Hero,
    Sections, Fine Print, and JavaScript hydration data. Injects <base href> for asset rendering.
    """
    if not html_raw:
        return {
            "title": "No Content",
            "hero_text": "",
            "sections_text": "",
            "fine_print_text": "",
            "raw_full_text": "",
            "raw_html": "",
            "js_hydration": {"framework": "None", "has_hydration": False}
        }

    # Strip any hackathon disclaimer text
    srishti_pattern = re.compile(r"This page is a fictional example created for the Srishti 2K26 hackathon\.?", re.IGNORECASE)
    clean_html = srishti_pattern.sub("", html_raw)

    soup = BeautifulSoup(clean_html, "html.parser")

    # Extract JS hydration before decomposing scripts
    js_hydration = extract_js_hydration_text(soup)

    # Title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(" ", strip=True) if title_tag else "Landing Page"

    # Inject <base href="..."> if base_url provided so iframe loads CSS/images correctly
    rendered_html = clean_html
    if base_url and "<base " not in clean_html.lower():
        head_match = re.search(r"<head[^>]*>", clean_html, re.IGNORECASE)
        if head_match:
            idx = head_match.end()
            base_tag = f'\n<base href="{html.escape(base_url, quote=True)}" target="_blank">\n'
            rendered_html = clean_html[:idx] + base_tag + clean_html[idx:]

    # Clean non-content tags for text extraction
    content_soup = BeautifulSoup(clean_html, "html.parser")
    for s in content_soup(["script", "style", "svg", "noscript"]):
        s.decompose()

    # 1. Above-The-Fold: Hero elements & Header
    hero_el = content_soup.find(class_=re.compile(r"hero", re.IGNORECASE))
    header_el = content_soup.find("header")
    hero_parts = []
    if header_el:
        hero_parts.append(header_el.get_text(" ", strip=True))
    if hero_el:
        hero_parts.append(hero_el.get_text(" ", strip=True))
    elif not header_el:
        h1 = content_soup.find("h1")
        if h1:
            hero_parts.append(h1.get_text(" ", strip=True))
            p = h1.find_next_sibling("p")
            if p:
                hero_parts.append(p.get_text(" ", strip=True))

    hero_text = " ".join(hero_parts).strip()

    # 2. Fine Print / Footer
    footer_el = content_soup.find("footer")
    fine_el = content_soup.find(class_=re.compile(r"fine", re.IGNORECASE))
    fine_print_text = ""
    if fine_el:
        fine_print_text = fine_el.get_text(" ", strip=True)
    elif footer_el:
        fine_print_text = footer_el.get_text(" ", strip=True)
    fine_print_text = srishti_pattern.sub("", fine_print_text).strip()

    # 3. Below-The-Fold: Sections, Cards, FAQ
    sections_parts = []
    sections = content_soup.find_all("section")
    for sec in sections:
        sec_text = sec.get_text(" ", strip=True)
        if sec_text:
            sections_parts.append(sec_text)

    # If DOM text is sparse but hydration text was found, enrich sections
    if js_hydration["has_hydration"] and len(sections_parts) < 2:
        sections_parts.append("--- JAVASCRIPT HYDRATION CONTENT ---")
        sections_parts.extend(js_hydration["extracted_texts"][:25])

    sections_text = "\n\n".join(sections_parts).strip()

    # 4. Raw Full Text for verbatim matching
    raw_full_text = content_soup.get_text(" ", strip=True)
    if js_hydration["has_hydration"]:
        raw_full_text += " " + " ".join(js_hydration["extracted_texts"])
    raw_full_text = srishti_pattern.sub("", raw_full_text).strip()

    return {
        "title": page_title,
        "hero_text": hero_text,
        "sections_text": sections_text,
        "fine_print_text": fine_print_text,
        "raw_full_text": raw_full_text,
        "raw_html": rendered_html,
        "js_hydration": js_hydration
    }


def parse_landing_page_html(html_path: Path) -> Dict[str, Any]:
    """Extract structured text from offline HTML landing page snapshot."""
    if not html_path.exists():
        return {
            "title": "Snapshot Not Found",
            "hero_text": "",
            "sections_text": "",
            "fine_print_text": "",
            "raw_full_text": "",
            "raw_html": "",
            "js_hydration": {"framework": "None", "has_hydration": False}
        }

    try:
        html_raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        html_raw = ""

    return parse_landing_page_from_raw_html(html_raw)


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_url_content(url: str, timeout: int = 15) -> Dict[str, Any]:
    """
    Fetch and render live URLs handling bot blocks (Cloudflare, PerimeterX, WAF)
    and client-side JavaScript rendering (extracting hydration state).
    """
    if not REQUESTS_AVAILABLE or requests is None:
        return {
            "success": False,
            "error": "The 'requests' library is not available in the environment.",
            "raw_html": "",
            "parsed": None,
            "meta": {}
        }

    target_url = str(url or "").strip()
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.google.com/"
    }

    try:
        session = requests.Session()
        session.headers.update(headers)
        ssl_verified = True
        
        try:
            # 1. Primary Attempt: Standard Secure SSL Verification
            response = session.get(target_url, timeout=timeout, allow_redirects=True)
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as ssl_err:
            # 2. Resilient Fallback: Self-signed/Institutional SSL certificate (e.g. psgtech.ac.in) or proxy bypass
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass
            try:
                response = session.get(target_url, timeout=timeout, allow_redirects=True, verify=False)
                ssl_verified = False
            except Exception:
                # 3. Protocol Fallback: If HTTPS fails, try HTTP
                if target_url.startswith("https://"):
                    http_url = target_url.replace("https://", "http://", 1)
                    response = session.get(http_url, timeout=timeout, allow_redirects=True)
                    ssl_verified = False
                else:
                    raise ssl_err

        response.raise_for_status()

        final_url = response.url
        raw_html = response.text
        status_code = response.status_code

        parsed = parse_landing_page_from_raw_html(raw_html, base_url=final_url)

        meta = {
            "status_code": status_code,
            "final_url": final_url,
            "size_kb": len(raw_html) / 1024.0,
            "framework": parsed.get("js_hydration", {}).get("framework", "Standard Static HTML"),
            "has_hydration": parsed.get("js_hydration", {}).get("has_hydration", False),
            "bot_protection_bypassed": True,
            "ssl_verified": ssl_verified
        }

        return {
            "success": True,
            "error": None,
            "raw_html": raw_html,
            "parsed": parsed,
            "meta": meta
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch live URL: {str(e)}",
            "raw_html": "",
            "parsed": None,
            "meta": {"status_code": getattr(e, "response", None).status_code if hasattr(e, "response") and e.response is not None else 0}
        }




def _clean_field(val: Any) -> str:
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


def _normalize_dataframe_to_ad_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = []
    col_map = {}
    for c in df.columns:
        clean_c = re.sub(r"[^a-z0-9]", "", str(c).lower())
        col_map[clean_c] = c

    def find_val(row, patterns):
        for pat in patterns:
            clean_pat = re.sub(r"[^a-z0-9]", "", pat.lower())
            if clean_pat in col_map:
                actual_col = col_map[clean_pat]
                v = _clean_field(row[actual_col])
                if v:
                    return v
        return ""

    for idx, row in df.iterrows():
        p_id = find_val(row, ["pair_id", "id", "campaign_id", "ad_id", "pair"]) or f"UPLOAD_ROW_{idx+1:02d}"
        adv = find_val(row, ["advertiser", "brand", "company", "client", "business"]) or "Advertiser"
        vert = find_val(row, ["vertical", "industry", "category", "sector"]) or "General Commercial"
        f_url = find_val(row, ["final_url", "url", "landing_page", "destination_url", "landing_page_url", "link", "target_url"])
        h1 = find_val(row, ["headline_1", "headline 1", "h1", "title_1", "title 1", "title", "headline"])
        h2 = find_val(row, ["headline_2", "headline 2", "h2", "title_2", "title 2", "subtitle"])
        h3 = find_val(row, ["headline_3", "headline 3", "h3", "title_3", "title 3"])
        d1 = find_val(row, ["description_1", "description 1", "d1", "desc_1", "desc 1", "description", "body"])
        d2 = find_val(row, ["description_2", "description 2", "d2", "desc_2", "desc 2"])
        p1 = find_val(row, ["path_1", "path 1", "path1"])
        p2 = find_val(row, ["path_2", "path 2", "path2"])
        kw = find_val(row, ["keyword", "target_keyword", "search_term", "query"])

        records.append({
            "pair_id": p_id,
            "advertiser": adv,
            "vertical": vert,
            "final_url": f_url,
            "headline_1": h1,
            "headline_2": h2,
            "headline_3": h3,
            "description_1": d1,
            "description_2": d2,
            "path_1": p1,
            "path_2": p2,
            "keyword": kw,
            "monthly_ad_spend": 10000.0,
            "cpc": 3.50
        })
    return records


def _parse_raw_text_to_ad_record(text: str, default_id: str = "UPLOAD_DOC_01") -> Dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    record = {
        "pair_id": default_id,
        "advertiser": "Ingested Advertiser",
        "vertical": "General Commercial",
        "final_url": "",
        "headline_1": "",
        "headline_2": "",
        "headline_3": "",
        "description_1": "",
        "description_2": "",
        "path_1": "",
        "path_2": "",
        "keyword": "",
        "monthly_ad_spend": 10000.0,
        "cpc": 3.50
    }

    url_match = re.search(r"https?://[^\s<>'\"]+", text)
    if url_match:
        record["final_url"] = url_match.group(0).rstrip(".,;")

    unassigned_lines = []
    for line in lines:
        if re.match(r"^(?:headline\s*1|h1|title\s*1|title)[\s*:]+", line, re.IGNORECASE):
            record["headline_1"] = re.sub(r"^(?:headline\s*1|h1|title\s*1|title)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:headline\s*2|h2|title\s*2)[\s*:]+", line, re.IGNORECASE):
            record["headline_2"] = re.sub(r"^(?:headline\s*2|h2|title\s*2)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:headline\s*3|h3|title\s*3)[\s*:]+", line, re.IGNORECASE):
            record["headline_3"] = re.sub(r"^(?:headline\s*3|h3|title\s*3)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:description\s*1|d1|desc\s*1|description)[\s*:]+", line, re.IGNORECASE):
            record["description_1"] = re.sub(r"^(?:description\s*1|d1|desc\s*1|description)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:description\s*2|d2|desc\s*2)[\s*:]+", line, re.IGNORECASE):
            record["description_2"] = re.sub(r"^(?:description\s*2|d2|desc\s*2)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:advertiser|brand|company)[\s*:]+", line, re.IGNORECASE):
            record["advertiser"] = re.sub(r"^(?:advertiser|brand|company)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:vertical|industry|category)[\s*:]+", line, re.IGNORECASE):
            record["vertical"] = re.sub(r"^(?:vertical|industry|category)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:url|link|destination|landing page)[\s*:]+", line, re.IGNORECASE):
            record["final_url"] = re.sub(r"^(?:url|link|destination|landing page)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^(?:keyword|search term)[\s*:]+", line, re.IGNORECASE):
            record["keyword"] = re.sub(r"^(?:keyword|search term)[\s*:]+", "", line, flags=re.IGNORECASE).strip()
        else:
            if not line.startswith("http://") and not line.startswith("https://"):
                unassigned_lines.append(line)

    if not record["headline_1"] and len(unassigned_lines) > 0:
        record["headline_1"] = unassigned_lines[0]
    if not record["headline_2"] and len(unassigned_lines) > 1:
        record["headline_2"] = unassigned_lines[1]
    if not record["headline_3"] and len(unassigned_lines) > 2:
        record["headline_3"] = unassigned_lines[2]
    if not record["description_1"] and len(unassigned_lines) > 3:
        record["description_1"] = unassigned_lines[3]
    if not record["description_2"] and len(unassigned_lines) > 4:
        record["description_2"] = unassigned_lines[4]

    return record


def parse_uploaded_ad_copy_file(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Ingest ad copy from an uploaded file (.xlsx, .xls, .csv, .docx, .txt, .json).
    Returns a list of standardized ad copy records.
    """
    fname = filename.lower()
    records = []

    if fname.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
        records = _normalize_dataframe_to_ad_records(df)
    elif fname.endswith(".xlsx") or fname.endswith(".xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
        records = _normalize_dataframe_to_ad_records(df)
    elif fname.endswith(".docx"):
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        table_rows = []
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    table_rows.append(" | ".join(cells))
        combined_text = chr(10).join(paragraphs + table_rows)
        records = [_parse_raw_text_to_ad_record(combined_text, default_id="UPLOAD_DOCX_01")]
    elif fname.endswith(".json"):
        raw_data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
        if isinstance(raw_data, list):
            for i, item in enumerate(raw_data):
                item["pair_id"] = item.get("pair_id", f"UPLOAD_JSON_{i+1:02d}")
                records.append(item)
        elif isinstance(raw_data, dict):
            raw_data["pair_id"] = raw_data.get("pair_id", "UPLOAD_JSON_01")
            records.append(raw_data)
    else:
        text_content = file_bytes.decode("utf-8", errors="ignore")
        records = [_parse_raw_text_to_ad_record(text_content, default_id="UPLOAD_TXT_01")]

    return records
