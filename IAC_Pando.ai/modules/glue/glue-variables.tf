variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "exim-analytics"
}


variable "s3_buckets" {
  description = "Map of S3 bucket names and ARNs"
  type = object({
    exim_core = object({
      name = string
      arn  = string
    })
    exim_cost = object({
      name = string
      arn  = string
    })
    exim_rm = object({
      name = string
      arn  = string
    })
  })
}
variable "KMS_Key_arn" {
  description = "KMS key arn "
  type        = string
}
