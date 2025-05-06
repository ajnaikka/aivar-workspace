# Provider configuration
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.49.0"
    }
    opensearch = {
      source = "opensearch-project/opensearch"
      version = "2.3.1"
    }

  }
  required_version = ">= 1.0.0"

  # backend "s3" {  
  #   bucket       = "aivar-terraform-state"  
  #   key          = "aivar/terraform.tfstate"  
  #   region       = "us-east-1"  
  #   encrypt      = true  
  #   use_lockfile = true  #S3 native locking
  # }  
}

provider "aws" {
  region = var.aws_region
}

# provider "opensearch" {
#   url         = aws_opensearchserverless_collection.schema_kb.collection_endpoint
#   healthcheck = false
# }

# module "vpc" {
#   source         = "./modules/vpc"
#   project_name   = var.project_name
#   environment    = var.environment
#   aws_region     = var.aws_region
# }

# module "s3" {
#   source        = "./modules/s3"
#   project_name  = var.project_name
#   environment   = var.environment
#   aws_region    = var.aws_region
#   glue_role_arn = module.glue.glue_role_arn
# }


# module "neptune" {
#   source                = "./modules/neptune"
#   project_name          = var.project_name
#   environment           = var.environment
#   aws_region            = var.aws_region
#   private_subnet_ids    = module.vpc.private_subnets
#   neptune_sg_id         = module.vpc.neptune_sg_id
# }

# module "glue" {
#   source        = "./modules/glue"
#   project_name  = var.project_name
#   environment   = var.environment
#   aws_region    = var.aws_region
#   KMS_Key_arn   = module.s3.s3_encryption_kms_key_arn
#   s3_buckets = {
#     exim_core = {
#       name = module.s3.bucket_exim_core
#       arn  = module.s3.bucket_exim_core_arn
#     }
#     exim_cost = {
#       name = module.s3.bucket_exim_cost
#       arn  = module.s3.bucket_exim_cost_arn
#     }
#     exim_rm = {
#       name = module.s3.bucket_exim_rm
#       arn  = module.s3.bucket_exim_rm_arn
#     }
#   }
# }

module "bedrock" {
  source                = "./modules/bedrock"
  # providers = {
  #   opensearch = opensearch
  #   aws        = aws
  # }
  project_name          = var.project_name
  environment           = var.environment
  aws_region            = var.aws_region
  
}

# module "neptune-notebook" {
#   source                 = "./modules/neptune-notebook"
#   project_name             = var.project_name
#   environment              = var.environment
#   aws_region               = var.aws_region
#   private_subnet_ids       = module.vpc.private_subnets
#   neptune_sg_id            = module.vpc.neptune_sg_id
#   neptune_cluster_endpoint = module.neptune.neptune_endpoint

# }

# module "DMS" {
#   source                = "./modules/DMS"
#   project_name          = var.project_name
#   environment           = var.environment
#   aws_region            = var.aws_region
#   private_subnet_ids    = module.vpc.private_subnets
#   postgres_database     = var.postgres_database
#   postgres_password     = var.postgres_password
#   postgres_server       = var.postgres_server
#   postgres_username     = var.postgres_username
#   dms_sg_id = module.vpc.dms_sg_id
#   s3_buckets = {
#     exim_core = {
#       name = module.s3.bucket_exim_core
#       arn  = module.s3.bucket_exim_core_arn
#     }
#     exim_cost = {
#       name = module.s3.bucket_exim_cost
#       arn  = module.s3.bucket_exim_cost_arn
#     }
#     exim_rm = {
#       name = module.s3.bucket_exim_rm
#       arn  = module.s3.bucket_exim_rm_arn
#     }
#   }
# }

# module "lambda" {
#   source                = "./modules/lambda"
#   project_name          = var.project_name
#   environment           = var.environment
#   aws_region            = var.aws_region
  
# }