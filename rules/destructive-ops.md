---
name: Destructive Ops Safety
description: Mandates dry-runs and explicit cost-warnings for infrastructure-as-code state mutations.
trigger: model_decision
---
# Infrastructure Safety Net

> **Role**: This rule acts as a safety boundary for Infrastructure as Code (IaC) to prevent accidental cloud spend, data loss, or unintentional resource mutations.

## 1. Dry-Run Mandate
- **No Blind Applies**: Never automatically execute commands that mutate infrastructure state (e.g., `terraform apply`, `kubectl apply`, `aws cloudformation deploy`) without explicit permission.
- **Mandatory Plans**: Always run the dry-run equivalent first (e.g., `terraform plan`, `kubectl diff`) and present the output. Explicitly pause and require the user's sign-off before proceeding with the destructive/mutating operation.

## 2. Cost-Warning System
- **Flag Persistent Costs**: Before applying any infrastructure change, explicitly flag if the change introduces a persistently running resource (e.g., an EC2 instance, an RDS instance, a NAT Gateway, or an un-capped load balancer).
- **Surprise Prevention**: Ensure the user is fully aware of the monthly idle cost implications of the resources being stood up.
