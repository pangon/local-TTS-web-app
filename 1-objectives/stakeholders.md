# Stakeholders

Everyone with a stake in the system: those who use it, fund it, maintain it, or are affected by it. Every requirement should trace back to a stakeholder need.

## Influence Levels

- **High** — can approve or veto decisions; priority conflicts resolved in their favor
- **Medium** — consulted during review; concerns addressed but may be overruled
- **Low** — informed of decisions; needs considered but not blocking

## Stakeholder Table

| ID | Role | Description | Interests | Influence |
|----|------|-------------|-----------|-----------|
| STK-end-user | End User | Person using the browser interface to convert text to speech | Easy-to-use interface, high-quality audio output, fast synthesis, privacy (no cloud dependency) | High |
| STK-self-hoster | Self-Hoster / Operator | Person deploying and running the app locally; may be the same as the end user or a sysadmin | Simple installation, low resource usage, clear configuration, reliable operation | High |
| STK-developer | Developer | Contributor maintaining or extending the codebase | Clean architecture, good documentation, easy local dev setup, testability | Medium |
