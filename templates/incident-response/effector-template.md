---
type: wall
hypothesis: "[INCIDENT] Block changes to affected files during active incident response"
prediction: "Preventing modifications during investigation reduces mean-time-to-resolution by >40%"
falsification: "Effector cells auto-expire after 3 sessions — no falsification needed"
expiry_sessions: 3
expiry_days: 7
created: "template"
impact_weight: 3.0
response_type: effector
minimum_mode: tempest
fitness:
  triggers: 0
  true_positives: 0
  false_positives: 0
  score: null
---
## Effector Cell: Acute Incident Response

Short-lived, aggressive protection during active incidents. This cell automatically expires after 3 sessions.

### When to Use
- Immediately after a production incident
- During active security vulnerability investigation
- When a critical bug is discovered but root cause is unknown

### Behavior
- Forces Tempest review on ALL changes to affected files
- 3x impact weight (highest priority)
- Auto-expires — no manual cleanup needed
