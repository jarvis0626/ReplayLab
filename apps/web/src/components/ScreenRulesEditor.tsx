import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { ScreenRule } from "../types";

export function ScreenRulesEditor({
  rules,
  onChange,
}: {
  rules: ScreenRule[];
  onChange: (rules: ScreenRule[]) => void;
}) {
  const [inputs, setInputs] = useState<Record<string, string>>({});
  function patch(id: string, value: Partial<ScreenRule>) {
    onChange(
      rules.map((rule) => (rule.id === id ? { ...rule, ...value } : rule)),
    );
  }
  return (
    <div className="digital-rule-editor">
      <div className="rule-heading">
        <span className="field-label">Screen checkpoint rules</span>
        <button
          className="icon-button"
          aria-label="Add screen rule"
          onClick={() =>
            onChange([
              ...rules,
              {
                id: `screen-${crypto.randomUUID()}`,
                kind: "text_present",
                expected: "",
                alternatives: [],
                contradictions: [],
                description: "",
              },
            ])
          }
        >
          <Plus size={16} />
        </button>
      </div>
      {!rules.length && (
        <p className="muted small">
          Add an observable UI rule before approval. Missing OCR text alone
          produces UNCERTAIN.
        </p>
      )}
      {rules.map((rule, i) => (
        <div className="rule-editor" key={rule.id}>
          <div className="row-between">
            <span className="rule-index">SCREEN RULE {i + 1}</span>
            <button
              className="icon-button"
              aria-label={`Remove screen rule ${i + 1}`}
              onClick={() => onChange(rules.filter((r) => r.id !== rule.id))}
            >
              <Trash2 size={13} />
            </button>
          </div>
          <label>
            UI evidence type
            <select
              value={rule.kind}
              onChange={(e) =>
                patch(rule.id, { kind: e.target.value as ScreenRule["kind"] })
              }
            >
              {[
                "text_present",
                "text_absent",
                "window",
                "path",
                "selection",
                "error_absent",
              ].map((kind) => (
                <option value={kind} key={kind}>
                  {kind.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            Expected visible text/state
            <input
              value={rule.expected}
              onChange={(e) => patch(rule.id, { expected: e.target.value })}
            />
          </label>
          <label>
            Accepted alternatives (comma separated)
            <input
              value={
                inputs[`${rule.id}-alternatives`] ??
                rule.alternatives.join(", ")
              }
              onChange={(e) => {
                setInputs((prev) => ({
                  ...prev,
                  [`${rule.id}-alternatives`]: e.target.value,
                }));
                patch(rule.id, {
                  alternatives: e.target.value
                    .split(",")
                    .map((v) => v.trim())
                    .filter(Boolean),
                });
              }}
            />
          </label>
          <label>
            Visible contradictions (comma separated)
            <input
              value={
                inputs[`${rule.id}-contradictions`] ??
                rule.contradictions.join(", ")
              }
              onChange={(e) => {
                setInputs((prev) => ({
                  ...prev,
                  [`${rule.id}-contradictions`]: e.target.value,
                }));
                patch(rule.id, {
                  contradictions: e.target.value
                    .split(",")
                    .map((v) => v.trim())
                    .filter(Boolean),
                });
              }}
            />
          </label>
          <label>
            Grounded correction / description
            <textarea
              rows={2}
              value={rule.description}
              onChange={(e) => patch(rule.id, { description: e.target.value })}
            />
          </label>
        </div>
      ))}
      <p className="editor-note">
        Only visible matching evidence can satisfy a rule. Add positive
        counterevidence for a definite mismatch; hidden application state is
        never inferred.
      </p>
    </div>
  );
}
