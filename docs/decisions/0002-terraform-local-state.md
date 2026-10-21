# ADR-0002 — Terraform local state

- **Status:** Accepted
- **Date:** 2026-10-21

## Context

Stage 4 introduces Terraform to manage AWS resources (S3 raw bucket, IAM user, budget
alert). Terraform needs somewhere to persist state. The two realistic options:

1. **Local state** — a `terraform.tfstate` file on the developer's machine.
2. **Remote state in S3** — the usual production pattern, with the state bucket
   itself managed by Terraform (or a separate bootstrap step), optionally with
   DynamoDB locking.

## Decision

Use local state. Reasons:

- This is a single developer, solo project — no second person or CI job ever runs
  `terraform apply` concurrently, so state locking has nothing to protect against.
- An S3 backend run from scratch has a bootstrap problem: the bucket that would hold
  the state doesn't exist until Terraform creates it, which means either a second
  manual bootstrap step or a backend migration after the fact. Extra ceremony with no
  benefit at this scale.
- `terraform.tfstate` and `terraform.tfvars` are gitignored (`infrastructure/terraform`
  entries in `.gitignore`, in place since Stage 2's Terraform baseline check).

## Consequences

- State lives only on this machine. If the disk is lost, Terraform loses track of
  what it created — the AWS resources themselves are unaffected, but reconciling them
  back into Terraform would need `terraform import`. Acceptable for a portfolio
  project with three cheap resources (one S3 bucket, one IAM user, one budget).
- No locking: a second `terraform apply` run from another machine or at the same time
  would race. Not a real risk here, since nobody else touches this state.
- If the project ever needs a second contributor or CI-driven `apply`, this decision
  should be revisited and migrated to an S3 (or Terraform Cloud) backend.
