terraform {
  required_version = ">= 1.16"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state file, gitignored. Fine for a solo learning project: no
  # locking, no remote collaboration. Rationale in
  # docs/decisions/0002-terraform-local-state.md.
}

provider "aws" {
  region  = var.aws_region
  profile = "rafa-iac"
}
