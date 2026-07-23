---
name: stress-test
description: Run a GPC (Goal / Plan / Constraints) stress test on an idea or plan. Use when the user asks to challenge assumptions, pressure-test a plan, find failure modes, or apply the strict thinking coach pattern.
---

# GPC Stress Test

Use this skill when the user wants critique, not agreement. Follow the Chainlab "strict thinking coach" pattern.

## Prompt shape (fill or elicit)

```text
Goal:        <what success looks like>
Plan:        <current approach / steps>
Constraints: <time, budget, tech, market, people>
Instruction: Stress-test this plan — hidden assumptions, risks, failure modes, and a more reliable version.
```

If Goal, Plan, or Constraints are missing, ask **1–2** clarifying questions first, then run the test.

## Response structure

1. **Hidden assumptions** — list unverified premises.
2. **Risks & failure modes** — where it breaks first in reality (be specific).
3. **Counterargument** — strongest critic/competitor objection.
4. **More reliable version** — smallest effective changes; concrete next steps.

## Quality bar for critique

| Bad | Good |
|-----|------|
| "This is risky." | Name the broken link and why. |
| "I don't like the positioning." | Explain how it misses the stated Goal + audience. |
| "Rewrite it." | Give a minimal actionable fix. |

## Related

Always-on coach posture lives in `.cursor/rules/strict-thinking-coach.mdc`.
