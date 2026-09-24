# Requirements — Fix wave-B map-data and physics audit findings in the Exolon game: P1-2 (player spawn does not match the Collision surface: 59 of 125 maps spawn 16px above and 29 below the ground), P1-3 (bullets are culled at x>528 while the player can move to x=544 and 61 maps have Collision right of x=512), P1-5 (beam_up/beam_down pairs create two 25-hit-point fields instead of one shared 25-hit model), P1-1 (46 pistons on 27 maps use the wrong height anchor and frequently cannot damage the player). Ground every fix in the TMX Collision data; self-checking verifiers per finding with contradictory controls.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

## Acceptance criteria

- [ ] Given ..., when ..., then ...

## Failure and edge cases

- 

## Governance context

Canonical governance JSON under `governance/` remains separately reviewed authority. Any rule, example, debt, or digest named here is non-authoritative context until the verifier rederives current governance evidence.

- Applicable rule IDs:
- Canonical-example deviations and evidence:
- Intentional debt created, repaid, or accepted:

## Non-functional requirements

- Security:
- Reliability:
- Performance:
- Observability:
