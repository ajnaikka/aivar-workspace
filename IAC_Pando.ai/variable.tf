# Variables
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


# PostgreSQL source configuration variables
variable "postgres_server" {
  description = "PostgreSQL server hostname or IP"
  type        = string
  default = "PSQL Hostname"
}

variable "postgres_database" {
  description = "PostgreSQL database name"
  type        = string
  default = "PSQL DB name"
}

variable "postgres_username" {
  description = "PostgreSQL username"
  type        = string
  default = "psql username"
}

variable "postgres_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  default = "psql password"
}