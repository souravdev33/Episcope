# Recording run sheet (target: 16–18 minutes)

Record the actual app and terminal at 1080p. Each speaker should introduce themselves on screen and speak for at least four minutes. Keep this as a guide; explain code and trade-offs in your own words. Do not present prototype outputs as official estimates.

| Time | Speaker | Chapter | Show |
|---|---|---|---|
| 00:00–04:00 | Sourav | Problem, stakeholders, CEP conflicts | Brief requirements, users, privacy/sensitivity/equity choices |
| 04:00–08:00 | Aritra | Architecture and data engineering | Generator schema, Spark bronze/silver/gold path, secret setup, quarantine and batch lineage |
| 08:00–12:00 | Sakib | Analytics and evaluation | Detection and forecasting methods, baseline comparison plan, uncertainty, honest status of unevaluated metrics |
| 12:00–16:00 | Noha | Allocation, dashboard, ethics and limits | Dashboard filters/views, suppressed cells, illustrative plan, policy recommendations, limitations |
| 16:00–18:00 | All | Live/replay demonstration and close | Clean run, incremental replay, idempotency evidence, quarantine example, next steps |

Before recording, complete a clean run with your own reviewed code. Show actual terminal timestamps. The assignment asks to show an incremental day and rerun; capture the result and verify source hashes/output counts yourselves. Include a real quarantine example. Do not edit out errors. The current dashboard labels its schematic tiles, synthetic records, and illustrative planning outputs.

## Rehearsal prompts

- **Sourav:** What is a reporting artifact, and how might it trigger a false alarm? Which stakeholder should verify it?
- **Aritra:** Why keep bronze raw, and where is the identifier removed? What does the source batch identifier let an analyst trace?
- **Sakib:** Why use a transparent baseline first? What evidence would be required before trusting its sensitivity and forecast intervals?
- **Noha:** How do district selection and suppression affect the other views? Why is the allocation only illustrative today?
