# Play: Threat Model

Authoritative procedure for `skills/threat-model`.

## Procedure

1. **Assets.** List what needs protecting (data, credentials, money,
   availability, reputation).
2. **Actors.** List every party that interacts with the system, including
   attackers with plausible motives (a competitor, an opportunistic
   scraper, a malicious insider, an automated bot).
3. **Entry points.** Every place an actor interacts with the system: UI,
   API endpoints, CLI, file imports, webhooks, message queues, admin
   tools.
4. **Trust boundaries.** Where the trust level changes between actors and
   components.
5. **Data flows.** For sensitive data, trace where it travels, at rest
   and in transit, and who/what can read it at each hop.
6. **Privileges.** What each actor and each component can do, and what it
   should not be able to do.
7. **Threats.** For each entry point and trust boundary, what could go
   wrong? Optionally organize using STRIDE:

   ```text
   Spoofing                identity or origin can be faked
   Tampering                data or code can be modified in transit/at rest
   Repudiation               an action can be denied with no evidence
   Information disclosure    data reaches someone who shouldn't see it
   Denial of service          the system can be made unavailable
   Elevation of privilege     an actor gains capability beyond their level
   ```

   Apply only the categories relevant to what you actually found in steps
   1-6. Do not force-fit every category onto every entry point.

8. **Mitigations.** For each threat judged worth addressing, name the
   concrete mitigation. Point to `skills/security-design` for features
   that still need implementation-level requirements worked out.
9. **Residual risks.** What remains after mitigation, and why it is
   accepted (cost, likelihood, or business decision).

## Scale to project complexity

```text
Small internal tool, no sensitive data, no network exposure
    -> a few bullet points is enough, or skip entirely

Typical internal web app with user data
    -> assets/actors/entry points/threats/mitigations, one pass

Internet-facing service, sensitive data, or high business value
    -> full STRIDE pass per trust boundary, explicit residual risk sign-off
```

Do not produce a large enterprise threat-model document for a small
application — match the depth to what is actually at stake.

## Output

Use `templates/threat-model.md`. Findings that require concrete
implementation requirements should be handed off to
`skills/security-design`.
