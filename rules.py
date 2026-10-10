"""Deterministic checklist (no LLM).

One row = one required element, the 21 CFR 211 paragraph that requires it, and text patterns
that show the element is present. The patterns are simple on purpose. They miss things and
they raise false alarms. The evaluation in eval/run_eval.py measures both.
"""
import re

DOC_TYPES = {
    "MBR": "Master production and control record (master batch record)",
    "BPR": "Batch production and control record (executed batch record)",
}

QU = r"\b(quality (control |assurance )?unit|QA|QU|QCU)\b"

CHECKLIST = {
    "MBR": [
        {"id": "process_validation", "cfr": "211.100", "para": "211.100(a)",
         "need": "Process validation is referenced (validated process, validation report or protocol)",
         "patterns": [r"process validation", r"validated process", r"validation (report|protocol|study)"]},
        {"id": "qu_approval", "cfr": "211.22", "para": "211.22(c)",
         "need": "Quality unit review and approval, with signature and date",
         "patterns": [QU + r".{0,60}(approv|review).{0,80}(sign|date)"]},
        {"id": "prepared_and_checked", "cfr": "211.186", "para": "211.186(a)",
         "need": "Prepared, dated and signed by one person and independently checked by a second person",
         "patterns": [r"prepared by.{0,200}(checked|verified) by"]},
        {"id": "theoretical_yield", "cfr": "211.186", "para": "211.186(b)(7)",
         "need": "Theoretical yield, with minimum and maximum percentages",
         "patterns": [r"theoretical yield"]},
        {"id": "packaging_labeling", "cfr": "211.186", "para": "211.186(b)(8)",
         "need": "Containers, closures and packaging materials, with a specimen or copy of each label",
         "patterns": [r"(specimen|copy) of (each |the )?label", r"label (specimen|copy)"]},
        {"id": "sampling_testing", "cfr": "211.186", "para": "211.186(b)(9)",
         "need": "Sampling and testing procedures and specifications",
         "patterns": [r"sampling", r"in-process (control|check|test)", r"specification"]},
    ],
    "BPR": [
        {"id": "dates", "cfr": "211.188", "para": "211.188(b)(1)",
         "need": "Date of each significant step",
         "patterns": [r"date of (manufactur\w*|production|filling|packaging|mixing|compounding)",
                      r"(manufactur\w*|production|filling) date"]},
        {"id": "equipment", "cfr": "211.188", "para": "211.188(b)(2)",
         "need": "Identity of the major equipment and lines used",
         "patterns": [r"equipment (id\w*|no\.?|number)", r"\b(mixer|tank|filler|line|vessel)\s+[A-Z]{1,4}-\d{2,}"]},
        {"id": "component_lots", "cfr": "211.188", "para": "211.188(b)(3)",
         "need": "Lot number of each component used",
         "patterns": [r"\blot (no\.?|number|#)\s*:?\s*[A-Z0-9-]{3,}"]},
        {"id": "in_process_results", "cfr": "211.188", "para": "211.188(b)(5)",
         "need": "In-process and laboratory control results",
         "patterns": [r"in-process (result|control|test)", r"laboratory (control )?result"]},
        {"id": "actual_yield", "cfr": "211.188", "para": "211.188(b)(7)",
         "need": "Actual yield and percentage of theoretical yield",
         "patterns": [r"actual yield"]},
        {"id": "performed_checked", "cfr": "211.188", "para": "211.188(b)(11)",
         "need": "Identification of the persons performing and checking each significant step",
         "patterns": [r"(performed|done) by.{0,120}(checked|verified) by"]},
        {"id": "qu_release_review", "cfr": "211.192", "para": "211.192",
         "need": "Quality unit review and approval of the record before release",
         "patterns": [QU + r".{0,80}(review|approv).{0,120}(release|sign|date)"]},
    ],
}


def rule_check(doc_type: str, text: str) -> list[dict]:
    """Return one finding for every checklist row whose patterns are all absent from the text."""
    findings = []
    for row in CHECKLIST.get(doc_type, []):
        if not any(re.search(p, text, re.I | re.S) for p in row["patterns"]):
            findings.append({"source": "rule", "check_id": row["id"], "cfr_section": row["cfr"],
                             "issue": f"Missing: {row['need']} [{row['para']}]",
                             "evidence_quote": "MISSING"})
    return findings
