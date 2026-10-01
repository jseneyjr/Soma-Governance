from __future__ import annotations

"""Review adapter: converts Prosecutor/Defender findings to arbiter inputs.

Maps Supercell review findings (JSON) into Prediction/Claim objects that the
deterministic arbiter can process. This is the bridge between prose-based
review and set-algebra arbitration.

Usage:
    from immune_system.verification.review_adapter import (
        findings_to_predictions, findings_to_claims, run_review_arbitration,
    )
"""

import json
import os
import tempfile

from . import (
    ArbitrationResult, Claim, Prediction, RiskCategory,
    Severity, ToolEvidence,
)
from .arbiter import arbitrate, format_report


# Mapping from review severity strings to Severity enum
_SEVERITY_MAP = {
    "block": Severity.CRITICAL,
    "BLOCK": Severity.CRITICAL,
    "warn": Severity.HIGH,
    "WARN": Severity.HIGH,
    "info": Severity.LOW,
    "INFO": Severity.LOW,
}

# Mapping from review domain/keywords to RiskCategory
_KEYWORD_TO_CATEGORY: dict[str, RiskCategory] = {
    # Security
    "code_injection": RiskCategory.CODE_INJECTION,
    "injection": RiskCategory.CODE_INJECTION,
    "format string attack": RiskCategory.CODE_INJECTION,
    "f-string injection": RiskCategory.CODE_INJECTION,
    "path_traversal": RiskCategory.PATH_TRAVERSAL,
    "traversal": RiskCategory.PATH_TRAVERSAL,
    "containment": RiskCategory.PATH_TRAVERSAL,
    "shell injection": RiskCategory.SHELL_INJECTION,
    "shell command": RiskCategory.SHELL_INJECTION,
    "shell=true": RiskCategory.SHELL_INJECTION,
    # Structural
    "dead_code": RiskCategory.DEAD_CODE,
    "dead code": RiskCategory.DEAD_CODE,
    "orphan": RiskCategory.MISSING_WIRE,
    "missing_wire": RiskCategory.MISSING_WIRE,
    "unused": RiskCategory.DEAD_CODE,
    # Contracts
    "contract_drift": RiskCategory.CONTRACT_DRIFT,
    "signature": RiskCategory.CONTRACT_DRIFT,
    "schema": RiskCategory.CONTRACT_DRIFT,
    "type_mismatch": RiskCategory.TYPE_MISMATCH,
    "timezone": RiskCategory.TYPE_MISMATCH,
    # Testing
    "missing_coverage": RiskCategory.MISSING_COVERAGE,
    "untested": RiskCategory.MISSING_COVERAGE,
    "missing test": RiskCategory.MISSING_COVERAGE,
    "tautological": RiskCategory.TAUTOLOGICAL_TEST,
    # Quality
    "dry": RiskCategory.DRY_VIOLATION,
    "duplicate": RiskCategory.DRY_VIOLATION,
    "copy-paste": RiskCategory.DRY_VIOLATION,
    "doc_drift": RiskCategory.DOC_DRIFT,
    "documentation": RiskCategory.DOC_DRIFT,
    "readme": RiskCategory.DOC_DRIFT,
    "changelog": RiskCategory.DOC_DRIFT,
    "convention": RiskCategory.CONVENTION_VIOLATION,
    "enforcement": RiskCategory.CONVENTION_VIOLATION,
    # State
    "state_corruption": RiskCategory.STATE_CORRUPTION,
    "boundary": RiskCategory.BOUNDARY_VIOLATION,
    "threshold": RiskCategory.BOUNDARY_VIOLATION,
    # Portability
    "portability": RiskCategory.PLATFORM_INCOMPATIBLE,
    "windows": RiskCategory.PLATFORM_INCOMPATIBLE,
    "encoding": RiskCategory.PLATFORM_INCOMPATIBLE,
}


def _classify_finding(text: str) -> RiskCategory:
    """Map a finding description to a RiskCategory via keyword matching.

    Falls back to CONTRACT_DRIFT if no keyword matches.
    """
    lower = text.lower()
    for keyword, category in _KEYWORD_TO_CATEGORY.items():
        if keyword in lower:
            return category
    return RiskCategory.CONTRACT_DRIFT


def findings_to_predictions(findings: list[dict]) -> list[Prediction]:
    """Convert Prosecutor findings (JSON dicts) to Prediction objects.

    Each finding dict must have:
      - severity: "BLOCK" | "WARN" | "INFO"
      - issue: str description
      - file: str (optional)
      - function: str (optional)
    """
    predictions = []
    for f in findings:
        severity = _SEVERITY_MAP.get(f.get("severity", "INFO"), Severity.LOW)
        issue = f.get("issue", "")
        category = _classify_finding(issue)
        predictions.append(Prediction(
            category=category,
            severity=severity,
            risk=issue,
            mechanism=f.get("mechanism", issue),
            affected_function=f.get("function", f.get("file", "unknown")),
        ))
    return predictions


def findings_to_claims(verifications: list[dict]) -> list[Claim]:
    """Convert Defender verifications (JSON dicts) to Claim objects.

    Each verification dict must have:
      - verdict: "CONFIRMED" | "CONCERN"
      - claim: str description
      - file: str
      - line: int (optional)
      - tests: list[str] (optional)
    """
    claims = []
    for v in verifications:
        if v.get("verdict") != "CONFIRMED":
            continue  # Only confirmed claims go to the arbiter
        claim_text = v.get("claim", "")
        category = _classify_finding(claim_text)
        claims.append(Claim(
            category=category,
            claim=claim_text,
            evidence_file=v.get("file", "unknown"),
            evidence_line=v.get("line", 0),
            tests_covering=v.get("tests", []),
        ))
    return claims


def run_review_arbitration(
    prosecutor_findings: list[dict],
    defender_verifications: list[dict],
    layer1_evidence: list[ToolEvidence] | None = None,
) -> ArbitrationResult:
    """Run deterministic arbitration on review findings.

    This is the un-bypassable entry point. Converts prose findings to
    structured objects and feeds them through the arbiter.

    Returns ArbitrationResult with deterministic SHIP/BLOCK/REVISE verdict.
    """
    predictions = findings_to_predictions(prosecutor_findings)
    claims = findings_to_claims(defender_verifications)
    evidence = layer1_evidence or []

    return arbitrate(predictions, claims, evidence)


def save_arbitration_evidence(
    result: ArbitrationResult,
    workspace: str,
    cycle: int = 1,
) -> str:
    """Persist arbitration result to .soma/evidence/ for checkpoint verification.

    The checkpoint gate checks for this file to prevent bypassing the arbiter.
    Uses atomic write (tempfile + rename) to prevent corruption on crash.

    Returns the path to the saved evidence file.
    """
    # Sanitize cycle to prevent path traversal
    cycle = int(cycle)
    if cycle < 1:
        raise ValueError(f"cycle must be a positive integer, got {cycle}")

    evidence_dir = os.path.join(workspace, ".soma", "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    target = os.path.join(evidence_dir, f"arbitration_cycle_{cycle}.json")

    record = {
        "cycle": cycle,
        "verdict": result.verdict.value,
        "divergence_count": len(result.divergences),
        "convergence_count": len(result.convergences),
        "prediction_count": len(result.predictions),
        "claim_count": len(result.claims),
        "divergences": [
            {
                "type": d.divergence_type,
                "category": d.category.value,
                "resolution": d.resolution,
            }
            for d in result.divergences
        ],
    }

    # Atomic write: write to temp file, then rename
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(evidence_dir), suffix='.json')
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2)
        os.replace(tmp_path, str(target))
    except BaseException:
        os.unlink(tmp_path)
        raise

    return target
