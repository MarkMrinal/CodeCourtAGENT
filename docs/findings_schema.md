# Findings Schema Specification

Every finding produced by Inspector HEUSC adheres to this contract. This contract is consumed by both the Court debate agents (`court.py`), the citation validator, and the Streamlit UI.

```json
{
  "id": "F1",
  "file": "app/auth.py",
  "function": "login_user",
  "issue": "duplicate_code",
  "detail": "Identical block also found in app/register.py and app/reset.py",
  "metric": null,
  "severity": "medium"
}
```

### Fields
| Field | Type | Description |
|---|---|---|
| `id` | `string` | Unique deterministic identifier (e.g. `F1`, `F2`). Must be cited in debates. |
| `file` | `string` | Relative path to the file within the repository. |
| `function` | `string` | Enclosing function name, or `module_scope` / `global_suite`. |
| `issue` | `string` | Normalized issue category (e.g., `sql_injection_risk`, `high_cyclomatic_complexity`). |
| `detail` | `string` | Human-readable explanation of the detected issue. |
| `metric` | `string \| null` | Objective measurement if available (e.g., `CC: 14`, `42 lines`). |
| `severity` | `string` | Priority tier: `"high"` \| `"medium"` \| `"low"`. |
