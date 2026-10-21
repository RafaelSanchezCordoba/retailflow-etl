variable "aws_region" {
  description = "AWS region for all RetailFlow resources"
  type        = string
  default     = "eu-north-1"
}

variable "alert_email" {
  description = "Email address to receive AWS Budgets threshold alerts"
  type        = string
  sensitive   = true
}

variable "monthly_budget_limit_usd" {
  description = "Monthly AWS cost budget limit, in USD, for the alert threshold"
  type        = number
  default     = 5
}
