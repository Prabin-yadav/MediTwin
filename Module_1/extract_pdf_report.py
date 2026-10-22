#!/usr/bin/env python3
"""
MediTwin Module 1 - Universal PDF Health & Laboratory Report Extractor
Extracts observations from all medical lab report layouts:
- Tabular / Columnar (Test | Result | Unit | Range)
- Delimited / Colon-separated (Test: 12.3 mg/dL)
- Multi-line block layouts (Test on line 1, value on line 2)
- Multi-column coordinate-clustered layouts (via PyMuPDF word clustering)
- Scanned, photocopied, image-only, or complex formatted reports via Multimodal Medical Vision AI
- Automatically converts international lab units (lakhs/cumm -> 10³/µL, mmol/L -> mg/dL, etc.)
- Supports both the 29 canonical Module 1 biomarkers and extended clinical tests (CBC differentials, Thyroid, Vitamins, etc.)
"""

import sys
import os
import re
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Ensure Module_1 is on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Ensure UTF-8 output on Windows consoles to prevent UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load Environment Variables from backend/.env or .env if not already set
def load_env_file():
    candidates = [
        CURRENT_DIR.parent / "backend" / ".env",
        CURRENT_DIR.parent / ".env",
        CURRENT_DIR / ".env"
    ]
    for p in candidates:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if k not in os.environ and v:
                            os.environ[k] = v
            except Exception:
                pass

load_env_file()

try:
    from config import (
        OBSERVATION_CONFIG,
        OBSERVATION_ALIASES,
        EXTENDED_OBSERVATIONS,
        EXTENDED_ALIASES,
        SUPPORTED_OBSERVATIONS
    )
except ImportError:
    OBSERVATION_CONFIG = {}
    OBSERVATION_ALIASES = {}
    EXTENDED_OBSERVATIONS = {}
    EXTENDED_ALIASES = {}
    SUPPORTED_OBSERVATIONS = []


# ==============================================================================
# 1. TEXT & LAYOUT EXTRACTION WITH COORDINATE CLUSTERING
# ==============================================================================

def cluster_words_into_lines(words: list) -> list[str]:
    """
    Groups PyMuPDF words (x0, y0, x1, y1, word) into horizontal lines based on
    vertical proximity, sorting words from left to right.
    This reconstructs true tabular rows even when PDF text streams are fragmented.
    """
    if not words:
        return []

    # Sort words by y0 then x0
    sorted_words = sorted(words, key=lambda w: (w[1], w[0]))
    lines = []
    current_line = []
    current_y = None
    y_tolerance = 4.0

    for w in sorted_words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], str(w[4])
        if current_y is None:
            current_y = y0
            current_line.append((x0, text))
        elif abs(y0 - current_y) <= y_tolerance:
            current_line.append((x0, text))
        else:
            # Sort words in line horizontally
            current_line.sort(key=lambda item: item[0])
            line_str = "    ".join(item[1] for item in current_line)
            lines.append(line_str)
            current_y = y0
            current_line = [(x0, text)]

    if current_line:
        current_line.sort(key=lambda item: item[0])
        line_str = "    ".join(item[1] for item in current_line)
        lines.append(line_str)

    return lines


def extract_pdf_data(pdf_path: str) -> tuple[str, list[str], bool, int]:
    """
    Extracts text and reconstructed layout lines from a PDF file using PyMuPDF.
    Returns (raw_text, reconstructed_lines, is_scanned, page_count).
    """
    import pymupdf

    doc = pymupdf.open(pdf_path)
    page_count = len(doc)
    all_raw_text = []
    all_reconstructed_lines = []
    total_chars = 0

    for page_idx in range(page_count):
        page = doc[page_idx]
        text = page.get_text("text")
        all_raw_text.append(text)
        total_chars += len(text.strip())

        # Extract words with coordinates
        words = page.get_text("words")
        if words:
            page_lines = cluster_words_into_lines(words)
            all_reconstructed_lines.extend(page_lines)

    combined_text = "\n".join(all_raw_text)
    doc.close()

    # Consider scanned if average characters per page is very low (< 60 chars)
    is_scanned = total_chars < 60 * max(1, page_count)
    return combined_text, all_reconstructed_lines, is_scanned, page_count


# ==============================================================================
# 2. DATE EXTRACTION
# ==============================================================================

def extract_report_date(text: str) -> str:
    """
    Extracts the most probable report or collection date from text.
    Returns ISO 8601 formatted string or today's date.
    """
    date_patterns = [
        r'(?:report\s*date|collected|collection\s*date|date\s*of\s*collection|specimen\s*date|test\s*date|sample\s*date|registered\s*on|registration\s*date)[:\s]+(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(?:report\s*date|collected|collection\s*date|date\s*of\s*collection|specimen\s*date|test\s*date|sample\s*date|registered\s*on|registration\s*date)[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(?:report\s*date|collected|date)[:\s]+([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})',
    ]

    for pat in date_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            for fmt in (
                "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y",
                "%d-%m-%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y",
                "%B %d %Y", "%b %d %Y", "%d %b %Y", "%d %B %Y"
            ):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    if 1990 <= dt.year <= datetime.now().year + 1:
                        return dt.strftime("%Y-%m-%dT09:00:00+00:00")
                except ValueError:
                    continue

    return datetime.now().strftime("%Y-%m-%dT09:00:00+00:00")


# ==============================================================================
# 3. UNIT CONVERSION & NORMALIZATION ENGINE
# ==============================================================================

def convert_units_and_normalize(canonical_or_extended_name: str, value: float, raw_unit: str) -> tuple[float, str, str]:
    """
    Converts values into standard canonical units where needed:
    - Platelets: lakhs/cumm -> 10³/µL; raw count (>5000) -> 10³/µL
    - WBC / Leukocytes: /cumm, /µL, >100 -> 10³/µL
    - Glucose: mmol/L -> mg/dL (x 18.0182)
    - Cholesterol / HDL / LDL: mmol/L -> mg/dL (x 38.67)
    - Triglycerides: mmol/L -> mg/dL (x 88.57)
    - Bilirubin: µmol/L -> mg/dL (x 0.0585)
    - Creatinine: µmol/L -> mg/dL (x 0.0113)
    - HbA1c: mmol/mol -> % ((IFCC * 0.09148) + 2.152)
    Returns (normalized_value, standard_unit, conversion_note).
    """
    unit_lower = (raw_unit or "").strip().lower()
    conversion_note = ""

    # 1. Platelets
    if "platelet" in canonical_or_extended_name.lower():
        if "lakh" in unit_lower or "lac" in unit_lower:
            val = round(value * 100.0, 1)
            return val, "10³/µL", f"Converted {value} lakhs/cumm to {val} 10³/µL"
        elif value > 3000:
            val = round(value / 1000.0, 1)
            return val, "10³/µL", f"Converted {value} /cumm to {val} 10³/µL"
        return value, "10³/µL", ""

    # 2. Leukocytes / WBC
    if "leukocyte" in canonical_or_extended_name.lower() or canonical_or_extended_name == "Leukocytes [#/volume] in Blood by Automated count":
        if "cumm" in unit_lower or "mcl" in unit_lower or "µl" in unit_lower or "/ul" in unit_lower or value > 120:
            if value > 100:
                val = round(value / 1000.0, 2)
                return val, "10³/µL", f"Converted {value} /cumm to {val} 10³/µL"
        return value, "10³/µL", ""

    # 3. Blood Glucose
    if canonical_or_extended_name == "Glucose":
        if "mmol" in unit_lower:
            val = round(value * 18.0182, 1)
            return val, "mg/dL", f"Converted {value} mmol/L to {val} mg/dL"
        return value, "mg/dL", ""

    # 4. Lipids (Cholesterol, HDL, LDL)
    if "cholesterol" in canonical_or_extended_name.lower():
        if "mmol" in unit_lower:
            val = round(value * 38.67, 1)
            return val, "mg/dL", f"Converted {value} mmol/L to {val} mg/dL"
        return value, "mg/dL", ""

    # 5. Triglycerides
    if "triglyceride" in canonical_or_extended_name.lower():
        if "mmol" in unit_lower:
            val = round(value * 88.57, 1)
            return val, "mg/dL", f"Converted {value} mmol/L to {val} mg/dL"
        return value, "mg/dL", ""

    # 6. Bilirubin
    if "bilirubin" in canonical_or_extended_name.lower():
        if "umol" in unit_lower or "µmol" in unit_lower:
            val = round(value * 0.0585, 2)
            return val, "mg/dL", f"Converted {value} µmol/L to {val} mg/dL"
        return value, "mg/dL", ""

    # 7. Creatinine
    if "creatinine" in canonical_or_extended_name.lower():
        if "umol" in unit_lower or "µmol" in unit_lower:
            val = round(value * 0.0113, 2)
            return val, "mg/dL", f"Converted {value} µmol/L to {val} mg/dL"
        return value, "mg/dL", ""

    # 8. HbA1c
    if "hba1c" in canonical_or_extended_name.lower() or "hemoglobin a1c" in canonical_or_extended_name.lower():
        if "mmol/mol" in unit_lower or value > 25:
            val = round((value * 0.09148) + 2.152, 2)
            return val, "%", f"Converted {value} mmol/mol (IFCC) to {val}% (DCCT)"
        return value, "%", ""

    # Default unit lookup
    info = OBSERVATION_CONFIG.get(canonical_or_extended_name) or EXTENDED_OBSERVATIONS.get(canonical_or_extended_name, {})
    default_unit = info.get("unit", raw_unit)
    return value, default_unit, conversion_note


# ==============================================================================
# 4. OBSERVATION NAME NORMALIZATION & DICTIONARY LOOKUP
# ==============================================================================

# Clinical acronyms and abbreviations that map unambiguously when found as distinct words
ACRONYM_MAP = {
    # Thyroid
    "tsh": ("Thyroid Stimulating Hormone", False),
    "ft3": ("Free Triiodothyronine", False),
    "ft4": ("Free Thyroxine", False),
    "t3": ("Triiodothyronine", False),
    "t4": ("Thyroxine", False),
    # Renal / Metabolic
    "bun": ("Urea Nitrogen", True),
    "fbs": ("Glucose", True),
    "ppbs": ("Glucose", True),
    "rbs": ("Glucose", True),
    "fpg": ("Glucose", True),
    # Liver
    "alt": ("Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma", True),
    "ast": ("Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma", True),
    "alp": ("Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma", True),
    "sgpt": ("Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma", True),
    "sgot": ("Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma", True),
    "ggt": ("Gamma Glutamyl Transferase", False),
    "ggtp": ("Gamma Glutamyl Transferase", False),
    # CBC
    "wbc": ("Leukocytes [#/volume] in Blood by Automated count", True),
    "tlc": ("Leukocytes [#/volume] in Blood by Automated count", True),
    "plt": ("Platelets [#/volume] in Blood by Automated count", True),
    "tpc": ("Platelets [#/volume] in Blood by Automated count", True),
    "pcv": ("Hematocrit [Volume Fraction] of Blood by Automated count", True),
    "hct": ("Hematocrit [Volume Fraction] of Blood by Automated count", True),
    "mcv": ("Mean Corpuscular Volume", False),
    "mch": ("Mean Corpuscular Hemoglobin", False),
    "mchc": ("Mean Corpuscular Hemoglobin Concentration", False),
    "rdw": ("Red Cell Distribution Width", False),
    "esr": ("Erythrocyte Sedimentation Rate", False),
    "rbc": ("Red Blood Cell Count", False),
    # Diabetes & Lipids
    "hba1c": ("Hemoglobin A1c/Hemoglobin.total in Blood", True),
    "a1c": ("Hemoglobin A1c/Hemoglobin.total in Blood", True),
    "hdl": ("High Density Lipoprotein Cholesterol", True),
    "ldl": ("Low Density Lipoprotein Cholesterol", True),
    "tg": ("Triglycerides", True),
    "tgl": ("Triglycerides", True),
    "egfr": ("Glomerular filtration rate/1.73 sq M.predicted", True),
    "gfr": ("Glomerular filtration rate/1.73 sq M.predicted", True),
    "bmi": ("Body Mass Index", True),
    "sbp": ("Systolic Blood Pressure", True),
    "dbp": ("Diastolic Blood Pressure", True),
    "aec": ("Eosinophils", False),
    "tibc": ("Serum Iron", False),
}

def normalize_observation_name(raw_name: str) -> tuple[str, str, bool, float]:
    """
    Matches raw extracted observation text to either:
    1. One of the 29 canonical Module 1 biomarkers (is_canonical = True)
    2. An extended clinical observation (is_canonical = False)
    Returns (matched_key, display_label, is_canonical, confidence).
    """
    cleaned = raw_name.strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s/().\-+]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 1. Exact canonical alias match
    if cleaned in OBSERVATION_ALIASES:
        canonical = OBSERVATION_ALIASES[cleaned]
        info = OBSERVATION_CONFIG.get(canonical, {})
        return canonical, info.get("label", canonical), True, 1.0

    # 2. Exact extended alias match
    if cleaned in EXTENDED_ALIASES:
        ext = EXTENDED_ALIASES[cleaned]
        info = EXTENDED_OBSERVATIONS.get(ext, {})
        return ext, info.get("label", ext), False, 1.0

    # 3. Cleaned without punctuation
    alpha_clean = re.sub(r'[^a-z0-9 ]', '', cleaned).strip()
    if alpha_clean in OBSERVATION_ALIASES:
        canonical = OBSERVATION_ALIASES[alpha_clean]
        info = OBSERVATION_CONFIG.get(canonical, {})
        return canonical, info.get("label", canonical), True, 0.98

    if alpha_clean in EXTENDED_ALIASES:
        ext = EXTENDED_ALIASES[alpha_clean]
        info = EXTENDED_OBSERVATIONS.get(ext, {})
        return ext, info.get("label", ext), False, 0.98

    # 4. Token boundary acronym match (e.g. "TSH - Ultrasensitive", "SGPT (ALT)", "Blood Sugar Fasting (FBS)")
    words = set(re.findall(r'\b[a-z0-9+-]+\b', cleaned))
    for acr, (target_name, is_c) in ACRONYM_MAP.items():
        if acr in words:
            cfg = OBSERVATION_CONFIG if is_c else EXTENDED_OBSERVATIONS
            lbl = cfg.get(target_name, {}).get("label", target_name)
            return target_name, lbl, is_c, 0.95

    # 5. Multi-word phrase containment
    # Canonical multi-words
    for alias, canonical in OBSERVATION_ALIASES.items():
        if len(alias) >= 5 and (f" {alias} " in f" {cleaned} " or cleaned.startswith(alias)):
            info = OBSERVATION_CONFIG.get(canonical, {})
            return canonical, info.get("label", canonical), True, 0.92

    # Extended multi-words
    for alias, ext in EXTENDED_ALIASES.items():
        if len(alias) >= 5 and (f" {alias} " in f" {cleaned} " or cleaned.startswith(alias)):
            info = EXTENDED_OBSERVATIONS.get(ext, {})
            return ext, info.get("label", ext), False, 0.92

    # 6. Distinct Single Clinical Keyword checks
    keyword_map = [
        # Canonical
        (r'\bplatelet(s)?\b', "Platelets [#/volume] in Blood by Automated count", True),
        (r'\b(leukocyte|leukocytes|white blood cell(s)?)\b', "Leukocytes [#/volume] in Blood by Automated count", True),
        (r'\b(hemoglobin|haemoglobin)\b(?!.*\ba1c\b)', "Hemoglobin [Mass/volume] in Blood", True),
        (r'\bcreatinine\b', "Creatinine", True),
        (r'\b(blood urea|serum urea)\b', "Urea Nitrogen", True),
        (r'\bpotassium\b', "Potassium", True),
        (r'\bsodium\b', "Sodium", True),
        (r'\bcalcium\b', "Calcium", True),
        (r'\bchloride\b', "Chloride", True),
        (r'\balbumin\b(?!.*\bglobulin\b)', "Albumin [Mass/volume] in Serum or Plasma", True),
        (r'\b(total cholesterol|cholesterol total)\b', "Total Cholesterol", True),
        (r'\btriglyceride(s)?\b', "Triglycerides", True),
        # Extended
        (r'\bneutrophil(s)?\b', "Neutrophils", False),
        (r'\blymphocyte(s)?\b', "Lymphocytes", False),
        (r'\beosinophil(s)?\b', "Eosinophils", False),
        (r'\bmonocyte(s)?\b', "Monocytes", False),
        (r'\bbasophil(s)?\b', "Basophils", False),
        (r'\buric acid\b', "Uric Acid", False),
        (r'\bvitamin d\b', "Vitamin D", False),
        (r'\bvitamin b12\b', "Vitamin B12", False),
        (r'\bferritin\b', "Ferritin", False),
    ]

    for pattern, target_name, is_c in keyword_map:
        if re.search(pattern, cleaned, re.IGNORECASE):
            cfg = OBSERVATION_CONFIG if is_c else EXTENDED_OBSERVATIONS
            lbl = cfg.get(target_name, {}).get("label", target_name)
            return target_name, lbl, is_c, 0.90

    # 7. Fuzzy Jaccard token overlap
    best_target = None
    best_is_canonical = False
    best_overlap = 0.0

    all_targets = [(k, v["aliases"], True) for k, v in OBSERVATION_CONFIG.items()] + \
                  [(k, v["aliases"], False) for k, v in EXTENDED_OBSERVATIONS.items()]

    for target_name, aliases, is_c in all_targets:
        for alias in aliases:
            a_words = set(re.findall(r'\b[a-z0-9]+\b', alias.lower()))
            if not a_words:
                continue
            intersection = len(words & a_words)
            overlap = intersection / len(a_words)
            if overlap > best_overlap and intersection >= 1:
                best_overlap = overlap
                best_target = target_name
                best_is_canonical = is_c

    if best_target and best_overlap >= 0.7:
        cfg = OBSERVATION_CONFIG if best_is_canonical else EXTENDED_OBSERVATIONS
        lbl = cfg.get(best_target, {}).get("label", best_target)
        return best_target, lbl, best_is_canonical, round(0.85 * best_overlap, 2)

    return None, None, False, 0.0


    return None, None, False, 0.0


def validate_plausibility(name: str, value: float, is_canonical: bool) -> tuple[bool, str]:
    """
    Checks if extracted numeric value falls into the physiological plausibility range.
    """
    config_dict = OBSERVATION_CONFIG if is_canonical else EXTENDED_OBSERVATIONS
    info = config_dict.get(name, {})
    bounds = info.get("plausibility_range", (0, 10000))
    low, high = bounds
    if low <= value <= high:
        return True, "Within plausible physiological range"
    return False, f"Value {value} is outside plausible range ({low} - {high})"


# ==============================================================================
# 5. REGEX & MULTI-STRATEGY LOCAL PARSER
# ==============================================================================

def parse_text_lines(lines: list[str], report_date: str) -> dict[str, dict]:
    """
    Parses a list of text lines with multi-layout recognition:
    - Blood pressure composites
    - Tabular columns
    - Colon / delimiter separated
    - Multi-line lookahead
    """
    observations = {}

    # Pass 1: Composite Blood Pressure
    bp_patterns = [
        r'(?:blood\s*pressure|bp|b\.p\.|nibp)[:\s]+(\d{2,3})\s*[/\\-]\s*(\d{2,3})',
        r'(\d{2,3})\s*[/\\-]\s*(\d{2,3})\s*mm\s*hg',
        r'systolic[/_]diastolic[:\s]+(\d{2,3})\s*[/\\-]\s*(\d{2,3})'
    ]
    for line in lines:
        for pat in bp_patterns:
            bp_match = re.search(pat, line, re.IGNORECASE)
            if bp_match:
                sbp_raw = float(bp_match.group(1))
                dbp_raw = float(bp_match.group(2))
                sbp_val, sbp_unit, _ = convert_units_and_normalize("Systolic Blood Pressure", sbp_raw, "mmHg")
                dbp_val, dbp_unit, _ = convert_units_and_normalize("Diastolic Blood Pressure", dbp_raw, "mmHg")

                sbp_ok, sbp_msg = validate_plausibility("Systolic Blood Pressure", sbp_val, True)
                dbp_ok, dbp_msg = validate_plausibility("Diastolic Blood Pressure", dbp_val, True)

                if sbp_ok and "Systolic Blood Pressure" not in observations:
                    observations["Systolic Blood Pressure"] = {
                        "name": "Systolic Blood Pressure",
                        "canonical_name": "Systolic Blood Pressure",
                        "label": OBSERVATION_CONFIG["Systolic Blood Pressure"]["label"],
                        "is_canonical": True,
                        "value": sbp_val,
                        "unit": sbp_unit,
                        "date": report_date,
                        "confidence": 0.95,
                        "plausible": sbp_ok,
                        "plausibility_note": sbp_msg,
                        "raw_match": line.strip()
                    }
                if dbp_ok and "Diastolic Blood Pressure" not in observations:
                    observations["Diastolic Blood Pressure"] = {
                        "name": "Diastolic Blood Pressure",
                        "canonical_name": "Diastolic Blood Pressure",
                        "label": OBSERVATION_CONFIG["Diastolic Blood Pressure"]["label"],
                        "is_canonical": True,
                        "value": dbp_val,
                        "unit": dbp_unit,
                        "date": report_date,
                        "confidence": 0.95,
                        "plausible": dbp_ok,
                        "plausibility_note": dbp_msg,
                        "raw_match": line.strip()
                    }
                break

    # Pass 2: Tabular & Key-Value Pattern Matching
    # Handles:
    # 1. Name: 12.3 mg/dL
    # 2. Name     12.3     mg/dL     10.0-15.0
    # 3. Name     12.3  *H mg/dL
    # 4. | Name | 12.3 | mg/dL |
    line_regexes = [
        # Colons/equals: Name: 12.3 mg/dL
        re.compile(r'^\s*\|?\s*([A-Za-z0-9\s/().\-+]{2,45}?)\s*[:=\t|]+\s*([<>]?\s*[\d,]+(?:\.\d+)?)\s*([A-Za-z%µ³\/\^0-9\-\*]*)(?:\s+[\d.\-<>]+|\s+Normal|\s+High|\s+Low|\s+\*H|\s+\*L)?', re.IGNORECASE),
        # Tabular whitespace: Name        12.3    mg/dL
        re.compile(r'^\s*\|?\s*([A-Za-z0-9\s/().\-+]{2,45}?)\s{2,}([<>]?\s*[\d,]+(?:\.\d+)?)\s*([A-Za-z%µ³\/\^0-9\-\*]*)', re.IGNORECASE),
        # Space separated with flag: Name 12.3 mg/dL
        re.compile(r'^\s*([A-Za-z0-9\s/().\-+]{2,40}?)\s+([<>]?\s*[\d,]+(?:\.\d+)?)\s+([A-Za-z%µ³\/\^0-9\-\*]+)', re.IGNORECASE),
    ]

    total_lines = len(lines)
    for i, line in enumerate(lines):
        cleaned_line = line.strip().replace('"', '').replace("'", "")
        if not cleaned_line or len(cleaned_line) < 3:
            continue

        matched = False
        for rx in line_regexes:
            m = rx.search(cleaned_line)
            if m:
                raw_name = m.group(1).strip()
                raw_val_str = m.group(2).replace(',', '').replace('<', '').replace('>', '').strip()
                raw_unit = m.group(3).strip() if len(m.groups()) >= 3 else ""

                try:
                    raw_val = float(raw_val_str)
                except ValueError:
                    continue

                matched_name, display_label, is_canonical, conf = normalize_observation_name(raw_name)
                if matched_name and matched_name not in observations:
                    norm_val, norm_unit, conv_note = convert_units_and_normalize(matched_name, raw_val, raw_unit)
                    is_plaus, plaus_note = validate_plausibility(matched_name, norm_val, is_canonical)
                    if conv_note:
                        plaus_note = f"{plaus_note} ({conv_note})" if is_plaus else plaus_note

                    observations[matched_name] = {
                        "name": matched_name,
                        "canonical_name": matched_name if is_canonical else None,
                        "label": display_label,
                        "is_canonical": is_canonical,
                        "value": norm_val,
                        "unit": norm_unit,
                        "date": report_date,
                        "confidence": conf,
                        "plausible": is_plaus,
                        "plausibility_note": plaus_note,
                        "raw_match": cleaned_line
                    }
                    matched = True
                    break

        # Pass 3: Multi-line lookahead (Test name on current line, value on next line)
        if not matched and i + 1 < total_lines:
            matched_name, display_label, is_canonical, conf = normalize_observation_name(cleaned_line)
            if matched_name and matched_name not in observations:
                next_line = lines[i + 1].strip()
                val_match = re.search(r'^([<>]?\s*[\d,]+(?:\.\d+)?)\s*([A-Za-z%µ³\/\^0-9\-]*)', next_line)
                if val_match:
                    raw_val_str = val_match.group(1).replace(',', '').replace('<', '').replace('>', '').strip()
                    raw_unit = val_match.group(2).strip()
                    try:
                        raw_val = float(raw_val_str)
                        norm_val, norm_unit, conv_note = convert_units_and_normalize(matched_name, raw_val, raw_unit)
                        is_plaus, plaus_note = validate_plausibility(matched_name, norm_val, is_canonical)
                        if conv_note:
                            plaus_note = f"{plaus_note} ({conv_note})" if is_plaus else plaus_note

                        observations[matched_name] = {
                            "name": matched_name,
                            "canonical_name": matched_name if is_canonical else None,
                            "label": display_label,
                            "is_canonical": is_canonical,
                            "value": norm_val,
                            "unit": norm_unit,
                            "date": report_date,
                            "confidence": round(conf * 0.9, 2),
                            "plausible": is_plaus,
                            "plausibility_note": plaus_note,
                            "raw_match": f"{cleaned_line} -> {next_line}"
                        }
                    except ValueError:
                        pass

    return observations


# ==============================================================================
# 6. MULTIMODAL MEDICAL VISION AI ENGINE
# ==============================================================================

def extract_via_medical_vision_ai(pdf_path: str) -> dict:
    """
    Renders PDF pages to high-resolution images and uses Gemini Flash Multimodal Vision
    to extract every medical lab test, observation, and vital sign into structured JSON.
    Includes automatic retries with exponential backoff for transient 503/429 API errors.
    """
    import time
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return {"success": False, "error": "GEMINI_API_KEY not configured for vision OCR"}

    import pymupdf

    abs_path = str(Path(pdf_path).resolve())
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"PDF file not found: {abs_path}"}

    doc = pymupdf.open(abs_path)
    page_count = min(len(doc), 5)  # Analyze up to first 5 pages
    images_base64 = []

    for page_idx in range(page_count):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        images_base64.append(b64)
    doc.close()

    if not images_base64:
        return {"success": False, "error": "No pages rendered for vision analysis"}

    prompt = (
        "You are an expert clinical laboratory document parser. "
        "Extract every single laboratory test, vital sign, and biomarker measurement from these medical report pages. "
        "Include test name, numeric value, unit, reference range, and specimen/report date. "
        "If a test has multiple parts (like Blood Pressure), separate Systolic and Diastolic as separate entries. "
        "Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "report_date": "YYYY-MM-DD",\n'
        '  "observations": [\n'
        '    {\n'
        '      "name": "string (test name)",\n'
        '      "value": 12.3,\n'
        '      "unit": "string (e.g. mg/dL, %, g/dL)",\n'
        '      "reference_range": "string"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    parts = [{"text": prompt}]
    for b64 in images_base64:
        parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    req_data = json.dumps(payload).encode("utf-8")
    last_error = ""

    # Attempt up to 4 times with exponential backoff on transient errors (503 / 429)
    for attempt in range(4):
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(raw_text)
                return {"success": True, "data": parsed}
        except urllib.error.HTTPError as http_err:
            last_error = f"HTTP {http_err.code}: {http_err.reason}"
            if http_err.code in (503, 500, 429):
                time.sleep(1.5 * (attempt + 1))
                continue
            else:
                break
        except Exception as e:
            last_error = str(e)
            time.sleep(1.5 * (attempt + 1))

    return {"success": False, "error": f"Vision AI request failed after retries: {last_error}"}


# ==============================================================================
# 7. MAIN ORCHESTRATOR
# ==============================================================================

def process_pdf(pdf_path: str) -> dict:
    """
    Main entry point to extract, parse, validate, and normalize lab report data from ANY PDF.
    Combines:
    1. Fast PyMuPDF layout reconstruction
    2. Multi-strategy tabular and columnar line parser
    3. Multimodal Medical Vision AI fallback for scanned / photocopied / image PDFs
    """
    abs_pdf_path = str(Path(pdf_path).resolve())
    if not os.path.exists(abs_pdf_path):
        return {
            "success": False,
            "error": f"File not found: {abs_pdf_path}",
            "observations": []
        }

    try:
        raw_text, reconstructed_lines, is_scanned, page_count = extract_pdf_data(abs_pdf_path)
        report_date = extract_report_date(raw_text)


        # Step 1: Run local parser on both reconstructed lines and raw lines
        all_lines = reconstructed_lines + [l.strip() for l in raw_text.splitlines() if l.strip()]
        local_observations = parse_text_lines(all_lines, report_date)

        vision_applied = False
        final_observations = dict(local_observations)

        # Step 2: Trigger Multimodal Medical Vision AI if:
        # - PDF is scanned or image-based, OR
        # - Local parser found fewer than 2 observations (complex format or graphical table)
        if is_scanned or len(local_observations) < 2:
            vision_res = extract_via_medical_vision_ai(pdf_path)
            if vision_res.get("success"):
                vision_data = vision_res["data"]
                vision_applied = True

                # Use Vision report date if available
                v_date = vision_data.get("report_date")
                if v_date and re.match(r'^\d{4}-\d{2}-\d{2}', v_date):
                    report_date = f"{v_date[:10]}T09:00:00+00:00"

                for item in vision_data.get("observations", []):
                    raw_name = str(item.get("name", "")).strip()
                    val = item.get("value")
                    unit = str(item.get("unit", "")).strip()

                    try:
                        num_val = float(val)
                    except (ValueError, TypeError):
                        continue

                    matched_name, display_label, is_canonical, conf = normalize_observation_name(raw_name)
                    if matched_name and matched_name not in final_observations:
                        norm_val, norm_unit, conv_note = convert_units_and_normalize(matched_name, num_val, unit)
                        is_plaus, plaus_note = validate_plausibility(matched_name, norm_val, is_canonical)
                        if conv_note:
                            plaus_note = f"{plaus_note} ({conv_note})" if is_plaus else plaus_note

                        final_observations[matched_name] = {
                            "name": matched_name,
                            "canonical_name": matched_name if is_canonical else None,
                            "label": display_label,
                            "is_canonical": is_canonical,
                            "value": norm_val,
                            "unit": norm_unit,
                            "date": report_date,
                            "confidence": round(conf * 0.95, 2),
                            "plausible": is_plaus,
                            "plausibility_note": plaus_note,
                            "raw_match": f"Vision AI: {raw_name} = {val} {unit}"
                        }

        obs_list = list(final_observations.values())
        canonical_count = sum(1 for o in obs_list if o.get("is_canonical"))
        extended_count = len(obs_list) - canonical_count

        return {
            "success": True,
            "file_name": os.path.basename(pdf_path),
            "page_count": page_count,
            "is_scanned": is_scanned,
            "vision_ocr_applied": vision_applied,
            "raw_text_length": len(raw_text),
            "report_date": report_date,
            "extracted_count": len(obs_list),
            "canonical_count": canonical_count,
            "extended_count": extended_count,
            "observations": obs_list,
            "preview_text": raw_text[:1200] if raw_text else "(Scanned / Graphical PDF Document)"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to extract PDF: {str(e)}",
            "observations": []
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: extract_pdf_report.py <pdf_path>"}))
        sys.exit(1)

    pdf_file = sys.argv[1]
    result = process_pdf(pdf_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))
