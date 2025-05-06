variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "neptune_sg_id" {
  type = string
}

variable "neptune_cluster_endpoint" {
  type = string
}

