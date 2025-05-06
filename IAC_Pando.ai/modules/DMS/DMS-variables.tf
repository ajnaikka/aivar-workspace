variable "project_name" {
  description = "Project name for tagging and resource naming"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "dms_sg_id" {
  type = string
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


# PostgreSQL source configuration variables
variable "postgres_server" {
  description = "PostgreSQL server hostname or IP"
  type        = string
}

variable "postgres_database" {
  description = "PostgreSQL database name"
  type        = string
}

variable "postgres_username" {
  description = "PostgreSQL username"
  type        = string
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}