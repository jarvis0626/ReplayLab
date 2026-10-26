"""Evidence-gated geometric verification; no model or filename chooses verdicts.

Coordinates and distances are normalized image measurements. They establish visible
2D relationships only and do not establish physical attachment or hidden geometry.
"""

from __future__ import annotations

import math

from app.schemas import Observation, ObservationSet, Rule, RuleResult, Step, VerificationResult

MIN_CONFIDENCE = 0.75
MIN_QUALITY = 0.65


def _quality_issues(reference: ObservationSet, current: ObservationSet) -> list[str]:
    issues: list[str] = []
    for name, observation_set in (("Reference", reference), ("Checkpoint", current)):
        # Coverage is needed to establish absence and exact counts, not to
        # compare two clearly observed objects within a partial scene.
        for field in ("visibility", "image_quality"):
            value = getattr(observation_set, field)
            if value is None:
                issues.append(f"{name} {field.replace('_', ' ')} is unknown.")
            elif value < MIN_QUALITY:
                issues.append(f"{name} {field.replace('_', ' ')} {value:.2f} is below {MIN_QUALITY:.2f}.")
        if observation_set.comparable is not True:
            issues.append(
                f"{name} camera comparability is {'unknown' if observation_set.comparable is None else 'not established'}."
            )
    return issues


def _matches(observations: ObservationSet, label: str) -> tuple[list[Observation], list[Observation]]:
    matching = [item for item in observations.observations if item.label.casefold() == label.casefold()]
    reliable = [
        item for item in matching if item.confidence is not None and item.confidence >= MIN_CONFIDENCE
    ]
    ambiguous = [item for item in matching if item.confidence is None or item.confidence < MIN_CONFIDENCE]
    return reliable, ambiguous


def _complete_scene(current: ObservationSet) -> bool:
    """Sparse detections cannot prove absence without a provider completeness claim."""
    return (
        current.coverage is not None
        and current.coverage >= 0.90
        and current.visibility is not None
        and current.visibility >= 0.85
        and current.image_quality is not None
        and current.image_quality >= 0.75
        and current.provenance.get("detection_complete") is True
    )


def _center(observation: Observation) -> tuple[float, float]:
    x1, y1, x2, y2 = observation.bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def _ambiguous_duplicates(observations: list[Observation]) -> bool:
    """Highly overlapping boxes or repeated identities cannot prove distinct objects."""
    for index, first in enumerate(observations):
        for second in observations[index + 1 :]:
            if first.track_id is not None and first.track_id == second.track_id:
                return True
            ax1, ay1, ax2, ay2 = first.bbox
            bx1, by1, bx2, by2 = second.bbox
            intersection = max(0, min(ax2, bx2) - max(ax1, bx1)) * max(0, min(ay2, by2) - max(ay1, by1))
            union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - intersection
            if union > 0 and intersection / union >= 0.75:
                return True
    return False


def _observation_evidence(observation: Observation) -> str:
    confidence = "unknown" if observation.confidence is None else f"{observation.confidence:.2f}"
    coordinates = ", ".join(f"{value:.3f}" for value in observation.bbox)
    return f"Observed {observation.label}: box [{coordinates}], confidence {confidence}, source {observation.source}, provider {observation.provider}."


def _expected(rule: Rule) -> str:
    if rule.kind == "presence":
        return f"{rule.subject} must be {'present' if rule.value is not False else 'absent'}."
    if rule.kind == "count":
        return f"Exactly {int(rule.value)} {rule.subject} object(s)."
    if rule.kind == "color":
        return f"{rule.subject} must have observed color {rule.value}."
    if rule.kind == "near":
        return f"{rule.subject} and {rule.target} centers must be within {float(rule.value or 0.2):.3f} image units."
    if rule.kind == "aligned":
        return f"{rule.subject} and {rule.target} centers must align on the {rule.value or 'x'} axis within {rule.tolerance:.3f}."
    return f"{rule.subject} center must be {rule.kind} of {rule.target} center by more than {rule.tolerance:.3f}."


def _result(
    rule: Rule, status: str, observed: str, evidence: list[str], correction: str | None = None
) -> RuleResult:
    return RuleResult(
        rule_id=rule.id,
        kind=rule.kind,
        status=status,
        expected=_expected(rule),
        observed=observed,
        evidence=evidence,
        correction=correction,
    )


def _evaluate(rule: Rule, current: ObservationSet) -> RuleResult:
    reliable, ambiguous = _matches(current, rule.subject)
    evidence = [_observation_evidence(item) for item in reliable + ambiguous]
    if rule.kind == "presence":
        should_exist = rule.value is not False
        if reliable:
            status = "pass" if should_exist else "fail"
            correction = (
                None if should_exist else f"Remove the visible {rule.subject} from the assembly area."
            )
            return _result(
                rule, status, f"{len(reliable)} reliable {rule.subject} detection(s).", evidence, correction
            )
        if ambiguous:
            return _result(
                rule, "uncertain", f"{rule.subject} has only low or unknown confidence detections.", evidence
            )
        if not _complete_scene(current):
            return _result(
                rule,
                "uncertain",
                f"No reliable {rule.subject} detection; full-scene detection coverage is not established.",
                evidence,
            )
        evidence.append(
            "Provider declares complete scene detection with adequate visibility, coverage, and image quality."
        )
        status = "fail" if should_exist else "pass"
        correction = f"Place {rule.subject} visibly in the assembly area." if should_exist else None
        return _result(
            rule,
            status,
            f"{rule.subject} was not detected in the adequately observed scene.",
            evidence,
            correction,
        )

    if rule.kind == "count":
        expected = int(rule.value)
        count = len(reliable)
        if _ambiguous_duplicates(reliable):
            return _result(
                rule,
                "uncertain",
                f"Overlapping boxes or repeated tracking identities cannot establish distinct {rule.subject} objects.",
                evidence,
            )
        if count > expected:
            return _result(
                rule,
                "fail",
                f"At least {count} reliable {rule.subject} detections, expected {expected}.",
                evidence,
                f"Remove {count - expected} extra {rule.subject} object(s).",
            )
        if ambiguous or not _complete_scene(current):
            return _result(
                rule,
                "uncertain",
                f"{count} reliable {rule.subject} detection(s); an exact count is not supported by complete reliable detection.",
                evidence,
            )
        evidence.append(
            "Provider declares complete scene detection with adequate visibility, coverage, and image quality."
        )
        if count == expected:
            return _result(rule, "pass", f"Exactly {count} reliable {rule.subject} detection(s).", evidence)
        return _result(
            rule,
            "fail",
            f"{count} {rule.subject} detection(s) in a complete scene, expected {expected}.",
            evidence,
            f"Add {expected - count} {rule.subject} object(s) visibly to the assembly area.",
        )

    if len(reliable) != 1 or ambiguous:
        return _result(
            rule,
            "uncertain",
            f"A unique, reliable {rule.subject} observation is required; found {len(reliable)} reliable and {len(ambiguous)} ambiguous.",
            evidence,
        )
    subject = reliable[0]
    if rule.kind == "color":
        if (
            subject.color is None
            or subject.color_confidence is None
            or subject.color_confidence < MIN_CONFIDENCE
        ):
            return _result(
                rule, "uncertain", f"Reliable color evidence for {rule.subject} is unavailable.", evidence
            )
        evidence.append(
            f"{rule.subject} observed color {subject.color}, color confidence {subject.color_confidence:.2f}."
        )
        matches = subject.color.casefold() == str(rule.value).casefold()
        return _result(
            rule,
            "pass" if matches else "fail",
            f"Observed color {subject.color}; expected {rule.value}.",
            evidence,
            None if matches else f"Use the {rule.value} {rule.subject} in this position.",
        )

    targets, ambiguous_targets = _matches(current, rule.target or "")
    evidence += [_observation_evidence(item) for item in targets + ambiguous_targets]
    if len(targets) != 1 or ambiguous_targets:
        return _result(
            rule,
            "uncertain",
            f"A unique, reliable {rule.target} observation is required; found {len(targets)} reliable and {len(ambiguous_targets)} ambiguous.",
            evidence,
        )
    sx, sy = _center(subject)
    tx, ty = _center(targets[0])
    evidence.append(
        f"Normalized centers: {rule.subject}=({sx:.3f}, {sy:.3f}); {rule.target}=({tx:.3f}, {ty:.3f})."
    )
    if rule.kind == "near":
        distance = math.hypot(sx - tx, sy - ty)
        threshold = float(rule.value or 0.2)
        status = (
            "pass"
            if distance <= threshold - rule.tolerance
            else "fail"
            if distance >= threshold + rule.tolerance
            else "uncertain"
        )
        observed = f"Center distance {distance:.3f}; maximum {threshold:.3f}, uncertainty margin {rule.tolerance:.3f}."
        correction = f"Move {rule.subject} closer to {rule.target}."
    elif rule.kind == "aligned":
        axis = rule.value or "x"
        distance = abs(sx - tx) if axis == "x" else abs(sy - ty)
        status = (
            "pass"
            if distance <= rule.tolerance
            else "fail"
            if distance >= rule.tolerance * 2
            else "uncertain"
        )
        observed = f"Center offset on {axis} axis {distance:.3f}; alignment tolerance {rule.tolerance:.3f}."
        correction = f"Align the {axis} centers of {rule.subject} and {rule.target}."
    else:
        signed_margin = {"above": ty - sy, "below": sy - ty, "left": tx - sx, "right": sx - tx}[rule.kind]
        status = (
            "pass"
            if signed_margin > rule.tolerance
            else "fail"
            if signed_margin < -rule.tolerance
            else "uncertain"
        )
        observed = f"Signed {rule.kind} center separation {signed_margin:.3f}; uncertainty margin {rule.tolerance:.3f}."
        correction = f"Move {rule.subject} {rule.kind} of {rule.target} in the camera view."
    return _result(rule, status, observed, evidence, correction if status == "fail" else None)


def verify(step: Step, reference: ObservationSet, current: ObservationSet) -> VerificationResult:
    """Evaluate approved constraints against current evidence without inferred facts."""
    issues = _quality_issues(reference, current)
    if issues:
        results = [
            _result(rule, "uncertain", "Scene evidence is insufficient for this comparison.", issues)
            for rule in step.rules
        ]
    else:
        results = [_evaluate(rule, current) for rule in step.rules]
    # One demonstrated mismatch establishes failure, while all constraints must be
    # sufficiently observed to pass. Preserve any remaining uncertainty per rule.
    status = (
        "fail"
        if any(item.status == "fail" for item in results)
        else "pass"
        if results and all(item.status == "pass" for item in results)
        else "uncertain"
    )
    evidence = list(dict.fromkeys(issues + [line for result in results for line in result.evidence]))
    if status == "pass":
        explanation = f"All {len(results)} approved visible constraint(s) are satisfied. This verifies only the observed 2D relationships."
    elif status == "fail":
        failures = [item for item in results if item.status == "fail"]
        explanation = " ".join(f"{item.observed} {item.correction or ''}".strip() for item in failures)
        if any(item.status == "uncertain" for item in results):
            explanation += " Other constraints remain uncertain; review their diagnostics."
    elif issues:
        explanation = (
            " ".join(issues) + " Capture a clear, unobstructed checkpoint from the reference viewpoint."
        )
    elif not results:
        explanation = "This step has no approved observable constraints. Review and add constraints before verification."
    else:
        explanation = " ".join(item.observed for item in results if item.status == "uncertain")
        explanation += " Improve visibility or detection reliability and capture another checkpoint."
    return VerificationResult(
        step_id=step.id,
        status=status,
        observations=current.observations,
        rule_results=results,
        evidence=evidence,
        explanation=explanation,
        provider_mode=current.provider_mode,
    )
