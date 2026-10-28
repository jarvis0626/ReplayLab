"""Deterministic screen checkpoints based on positive, qualified UI evidence."""

from __future__ import annotations

import re
import unicodedata

from app.digital_schemas import ScreenObservation, ScreenResult, ScreenRule, ScreenRuleResult
from app.services.graph import available_steps, validate_graph
from app.services.thresholds import evidence_thresholds
from app.services.screen_observation import is_coach_capture, redact_text

def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("\\", "/")
    value = value.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", value).strip()


def _matches(text: str, expected: str) -> bool:
    phrase = _normalized(expected)
    if not phrase or "[redacted" in phrase:
        return False
    normalized_text = _normalized(text)
    if phrase in {
        "installed",
        "enabled",
        "ready",
        "downloaded",
        "configured",
        "connected",
        "complete",
        "completed",
    }:
        if re.search(r"\b(?:not|never|no)\b.{0,60}(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized_text):
            return False
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", normalized_text) is not None


def _rules(step) -> list[ScreenRule]:
    return [
        rule if isinstance(rule, ScreenRule) else ScreenRule.model_validate(rule)
        for rule in getattr(step, "screen_rules", [])
    ]


def _reliable(observation: ScreenObservation):
    return [
        item
        for item in observation.elements
        if item.confidence is not None and item.confidence >= evidence_thresholds().confidence
    ]


def _evidence(item) -> str:
    return f"Visible {item.role}: {redact_text(item.text)} (confidence {item.confidence:.2f}, source {item.source})."


def _evaluate(rule: ScreenRule, observation: ScreenObservation) -> ScreenRuleResult:
    reliable = _reliable(observation)
    role = {"window": "window", "path": "path", "selection": "selection"}.get(rule.kind)
    scoped = [item for item in reliable if role is None or item.role == role]
    choices = [rule.expected, *rule.alternatives]

    def matches(item, phrase):
        if rule.kind == "path":
            actual = (
                re.sub(r"^(?:path|destination|folder)\s*:\s*", "", _normalized(item.text))
                .strip("\"'")
                .rstrip("/")
            )
            return actual == _normalized(phrase).strip("\"'").rstrip("/")
        return _matches(item.text, phrase)

    positive = [item for item in scoped if any(matches(item, phrase) for phrase in choices)]
    contradictions = [item for item in scoped if any(matches(item, phrase) for phrase in rule.contradictions)]
    expected = redact_text(rule.expected)
    evidence = [_evidence(item) for item in positive + contradictions]
    if rule.kind == "text_absent":
        if positive:
            return ScreenRuleResult(
                rule_id=rule.id,
                status="fail",
                expected=f"{expected} must not be visible.",
                observed=f"The prohibited text {expected} is reliably visible.",
                evidence=evidence,
                correction=f"Resolve the visible {expected} state before continuing.",
            )
        if observation.complete:
            return ScreenRuleResult(
                rule_id=rule.id,
                status="pass",
                expected=f"{expected} must not be visible.",
                observed="The provider explicitly marks this observed scope complete; prohibited text was not found.",
                evidence=[
                    "Complete observed scope was explicitly supplied; this is not inferred from an OCR miss."
                ],
            )
        return ScreenRuleResult(
            rule_id=rule.id,
            status="uncertain",
            expected=f"{expected} must not be visible.",
            observed="Missing OCR text cannot establish absence in an incompletely observed screen.",
        )
    if rule.kind == "error_absent":
        # An explicit positive status such as 'No errors' is usable evidence.
        # Arbitrary absence is not inferred from an OCR search returning nothing.
        errors = [
            item
            for item in reliable
            if item.role == "error" and not any(_matches(item.text, phrase) for phrase in choices)
        ]
        if errors:
            return ScreenRuleResult(
                rule_id=rule.id,
                status="fail",
                expected=expected,
                observed="A visible error contradicts this checkpoint.",
                evidence=[_evidence(item) for item in errors],
                correction="Resolve the visible error and recheck the same checkpoint.",
            )
        if positive:
            return ScreenRuleResult(
                rule_id=rule.id,
                status="pass",
                expected=expected,
                observed=f"Explicit safe status {expected} is visible.",
                evidence=evidence,
            )
        if observation.complete:
            return ScreenRuleResult(
                rule_id=rule.id,
                status="pass",
                expected=expected,
                observed="No error was identified within the explicitly complete observed scope.",
                evidence=["Complete observed scope was explicitly supplied."],
            )
        return ScreenRuleResult(
            rule_id=rule.id,
            status="uncertain",
            expected=expected,
            observed="No explicit safe status or complete observation establishes the absence of errors.",
        )
    if positive and contradictions:
        return ScreenRuleResult(
            rule_id=rule.id,
            status="uncertain",
            expected=expected,
            observed="Both expected and contradictory labels are visible; the active target state is ambiguous.",
            evidence=evidence,
        )
    if contradictions:
        return ScreenRuleResult(
            rule_id=rule.id,
            status="fail",
            expected=expected,
            observed="A known contradictory UI state is reliably visible.",
            evidence=evidence,
            correction=f"Return to the approved {expected} state, then capture the target window again.",
        )
    if positive:
        return ScreenRuleResult(
            rule_id=rule.id,
            status="pass",
            expected=expected,
            observed=f"Expected {role or 'text'} {expected} is reliably visible.",
            evidence=evidence,
        )
    # A visibly selected alternative window/path is strong counterevidence. Text
    # elsewhere on the screen is not treated as the active destination.
    if role in {"path", "selection", "window"} and len(scoped) == 1:
        item = scoped[0]
        return ScreenRuleResult(
            rule_id=rule.id,
            status="fail",
            expected=expected,
            observed=f"The explicitly observed active {role} differs from {expected}.",
            evidence=[_evidence(item)],
            correction=f"Choose the approved {role} {expected}, then recheck.",
        )
    return ScreenRuleResult(
        rule_id=rule.id,
        status="uncertain",
        expected=expected,
        observed=f"No adequately qualified observation establishes {expected}. A missing label alone is not a mismatch.",
    )


def _aggregate(results):
    return (
        "fail"
        if any(item.status == "fail" for item in results)
        else "pass"
        if results and all(item.status == "pass" for item in results)
        else "uncertain"
    )


def verify_screen(step, observation: ScreenObservation, workflow=None, completed_ids=None) -> ScreenResult:
    rules = _rules(step)
    warnings = []
    instruction = " ".join(
        str(getattr(step, field, "")) for field in ("title", "description", "expected_state")
    )
    if re.search(
        r"(?:disable|turn off|bypass).{0,45}(?:antivirus|security|defender|firewall|protection|signature verification)",
        instruction,
        re.IGNORECASE,
    ):
        return ScreenResult(
            step_id=step.id,
            status="uncertain",
            provider_mode=observation.provider_mode,
            reason="unsafe_instruction",
            explanation="This instruction asks to disable or bypass a security protection. Review it independently before proceeding.",
            warnings=[
                "ReplayLab does not execute instructions, click controls, or change security settings."
            ],
        )
    if re.search(r"https?://|\bcurl\b.+\|\s*(?:sh|bash)\b|\bInvoke-Expression\b", instruction, re.IGNORECASE):
        warnings.append(
            "Review external downloads and publisher trust before proceeding; ReplayLab does not execute commands or downloads."
        )
    if observation.provenance.get("self_capture") or is_coach_capture(observation.visible_text):
        return ScreenResult(
            step_id=step.id,
            status="uncertain",
            provider_mode=observation.provider_mode,
            reason="insufficient_evidence",
            explanation="The shared image shows the ReplayLab coach. Share the separate target application window so its instructions cannot prove their own completion.",
            warnings=warnings,
        )
    quality_issues = []
    if observation.image_quality is None or observation.image_quality < evidence_thresholds().digital_quality:
        quality_issues.append("The screenshot has insufficient or unknown image quality.")
    if observation.confidence is None or observation.confidence < evidence_thresholds().confidence:
        quality_issues.append("Screen recognition confidence is insufficient or unknown.")
    if quality_issues:
        results = [
            ScreenRuleResult(
                rule_id=rule.id,
                status="uncertain",
                expected=redact_text(rule.expected),
                observed="Screen evidence does not meet the quality and confidence gates.",
                evidence=quality_issues,
            )
            for rule in rules
        ]
        return ScreenResult(
            step_id=step.id,
            status="uncertain",
            rule_results=results,
            evidence=quality_issues,
            explanation=" ".join(quality_issues) + " Capture a clear target window and retry.",
            provider_mode=observation.provider_mode,
            reason="insufficient_evidence",
            warnings=warnings,
        )
    if observation.provenance.get("interface_version_ambiguous") is True:
        return ScreenResult(
            step_id=step.id,
            status="uncertain",
            provider_mode=observation.provider_mode,
            reason="interface_mismatch",
            explanation="Multiple reliable interface versions are visible. Select a single comparable target window and recheck before claiming completion or a mismatch.",
            warnings=warnings,
        )
    expected_version = getattr(workflow, "interface_version", None) if workflow else None
    if (
        expected_version
        and observation.interface_version
        and _normalized(expected_version) != _normalized(observation.interface_version)
    ):
        return ScreenResult(
            step_id=step.id,
            status="uncertain",
            provider_mode=observation.provider_mode,
            reason="interface_mismatch",
            explanation="The explicitly observed interface version differs from the tutorial. Review or update its steps; this is not evidence of a user mistake.",
            evidence=[
                f"Tutorial interface version {redact_text(expected_version)}; observed version {redact_text(observation.interface_version)}."
            ],
            warnings=warnings,
        )
    results = [_evaluate(rule, observation) for rule in rules]
    evidence = list(dict.fromkeys(line for result in results for line in result.evidence))
    expectations = [
        phrase
        for rule in rules
        if rule.kind not in {"text_absent", "error_absent"}
        for phrase in [rule.expected, *rule.alternatives]
    ]
    unexpected = [
        item
        for item in _reliable(observation)
        if item.role in {"dialog", "error"}
        and not any(_matches(item.text, phrase) for phrase in expectations)
    ]
    if unexpected:
        details = [_evidence(item) for item in unexpected]
        reason = "unexpected_dialog" if any(item.role == "dialog" for item in unexpected) else "mismatch"
        return ScreenResult(
            step_id=step.id,
            status="fail",
            rule_results=results,
            evidence=evidence + details,
            explanation="A visible unexpected dialog or error interrupts this checkpoint. "
            + " ".join(details)
            + " Resolve it and recheck the current step.",
            provider_mode=observation.provider_mode,
            reason=reason,
            warnings=warnings,
        )
    status = _aggregate(results)
    observed_step_id = step.id if status == "pass" else None
    missing_prerequisites = set(getattr(step, "dependencies", [])) - set(completed_ids or [])
    later_step = None
    if workflow:
        try:
            order = validate_graph(workflow.steps)
            available_steps(workflow.steps, completed_ids or [])
        except ValueError:
            return ScreenResult(
                step_id=step.id,
                status="uncertain",
                rule_results=results,
                evidence=evidence,
                explanation="The workflow or completion history violates its dependency graph. Reload and review the workflow before continuing.",
                provider_mode=observation.provider_mode,
                reason="insufficient_evidence",
                warnings=warnings,
            )
        by_id = {item.id: item for item in workflow.steps}
        ordered_steps = [by_id[identifier] for identifier in order]
        current_index = next((index for index, item in enumerate(ordered_steps) if item.id == step.id), -1)
        for candidate in ordered_steps[current_index + 1 :]:
            candidate_rules = _rules(candidate)
            if (
                candidate_rules
                and _aggregate([_evaluate(rule, observation) for rule in candidate_rules]) == "pass"
            ):
                later_step = candidate
        if later_step:
            observed_step_id = later_step.id
    if missing_prerequisites or (later_step is not None and status != "pass"):
        missing = sorted(missing_prerequisites)
        explanation = "Visible evidence matches a checkpoint whose prerequisites have not all been verified. Review the earlier checkpoints before advancing."
        if status == "fail":
            explanation = "A contradictory current state is visible, and a later checkpoint is detected. Return to the approved current step and verify its prerequisites."
        return ScreenResult(
            step_id=step.id,
            status="fail" if status == "fail" else "uncertain",
            rule_results=results,
            evidence=evidence
            + (["Unverified prerequisite identifiers: " + ", ".join(missing)] if missing else []),
            explanation=explanation,
            provider_mode=observation.provider_mode,
            reason="skipped_step",
            observed_step_id=observed_step_id,
            warnings=warnings,
        )
    if status == "pass":
        explanation = (
            f"All {len(results)} approved screen constraint(s) are supported by visible UI evidence."
        )
    elif status == "fail":
        explanation = " ".join(
            f"{item.observed} {item.correction or ''}".strip() for item in results if item.status == "fail"
        )
    elif not results:
        explanation = (
            "This step has no approved screen constraints. Add observable UI checkpoints before verification."
        )
    else:
        explanation = (
            " ".join(item.observed for item in results if item.status == "uncertain")
            + " Recheck the target window or clarify the checkpoint."
        )
    return ScreenResult(
        step_id=step.id,
        status=status,
        rule_results=results,
        evidence=evidence,
        explanation=explanation,
        provider_mode=observation.provider_mode,
        reason="completed"
        if status == "pass"
        else "mismatch"
        if status == "fail"
        else "insufficient_evidence",
        observed_step_id=observed_step_id,
        warnings=warnings,
    )
