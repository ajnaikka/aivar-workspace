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

variable "neptune_sg_id" {
  type = string
}
