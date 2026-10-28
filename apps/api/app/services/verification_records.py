"""Normalize deterministic results; retain only explicitly permitted evidence."""

from datetime import datetime, timezone
from uuid import uuid4

from app.services.screen_observation import redact_text
from app.verification_contracts import (
    ConstraintEvaluation, EvidenceReference, VerificationProvider, WorkflowVerification,
)


def build_verification(
    project, task, step, result, *, task_revision, latency_ms, retained=False,
    observation=None, selected_mode="mock", explanation_provider="deterministic_template",
) -> WorkflowVerification:
    """A projection of a verdict, never a second authority deciding correctness."""
    def clean(text):
        return redact_text(str(text))[:4000]  # bounded relevant evidence only
    kinds = {rule.id: rule.kind for rule in (step.screen_rules if task.modality == "digital" else step.rules)}
    constraints = [ConstraintEvaluation(
        id=item.rule_id, kind=kinds.get(item.rule_id, "unknown"), verdict=item.status,
        expected=clean(item.expected), observed=clean(item.observed),
        evidence=[clean(line) for line in item.evidence[:20]],
        correction=clean(item.correction) if item.correction else None,
    ) for item in result.rule_results]
    if not constraints and task.modality == "digital":
        # Global gates prevent individual rule evaluation. Make that abstention
        # inspectable without pretending the expected conditions were observed.
        constraints = [ConstraintEvaluation(
            id=rule.id, kind=rule.kind, verdict="uncertain", expected=clean(rule.expected),
            observed="Not evaluated: " + clean(result.explanation),
            evidence=[clean(line) for line in result.evidence[:20]],
        ) for rule in step.screen_rules]
    evidence = [EvidenceReference(
        id=f"observation-{index + 1}", kind="visible_observation", text=clean(line),
        source=result.provider_mode,
    ) for index, line in enumerate(result.evidence[:100])]
    if step.reference_frame_id:
        evidence.append(EvidenceReference(
            id=step.reference_frame_id, kind="reference_frame",
            text=f"Reviewed tutorial reference frame {step.reference_frame_id}.",
            source="reviewed_tutorial", timestamp=step.timestamp_start,
        ))
    uncertainty = [item.observed for item in constraints if item.verdict == "uncertain"]
    if result.status == "uncertain" and not uncertainty:
        uncertainty = [clean(result.explanation)]
    classification = None
    if task.modality == "digital":
        reason = result.reason
        if reason == "interface_mismatch":
            classification = (
                "confirmed_version_mismatch" if observation is not None
                and observation.interface_version and task.interface_version
                and not observation.provenance.get("interface_version_ambiguous")
                else "possible_version_mismatch"
            )
        elif result.status == "fail":
            classification = "unexpected_ui_state"
        elif result.status == "uncertain":
            classification = (
                "expected_ui_not_found" if constraints and all(
                    "No adequately qualified observation" in item.observed for item in constraints
                ) else "insufficient_visual_evidence"
            )
    corrections = [item.correction for item in constraints if item.correction]
    correction = " ".join(dict.fromkeys(corrections)) if corrections else (
        clean(result.explanation) if result.status != "pass" else None
    )
    expected = [item.expected for item in constraints]
    if not expected:
        expected = [clean(step.expected_state or step.description or step.title)]
    return WorkflowVerification(
        id=uuid4().hex, workflow_id=project["id"], task_id=task.id, step_id=step.id,
        modality=task.modality, verdict=result.status, expected_conditions=expected,
        observed_conditions=[item.observed for item in constraints] or [clean(line) for line in result.evidence[:20]],
        constraints=constraints,
        evidence_references=evidence, uncertainty_reasons=list(dict.fromkeys(uncertainty)),
        correction=correction, explanation=clean(result.explanation),
        provider=VerificationProvider(mode=selected_mode, observation=result.provider_mode,
                                      explanation=explanation_provider),
        mismatch_classification=classification, latency_ms=round(max(0, latency_ms), 3),
        created_at=datetime.now(timezone.utc).isoformat(), task_revision=task_revision,
        retained=retained,
    )
