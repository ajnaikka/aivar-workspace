data "aws_caller_identity" "current" {}

# Creating custom KMS key to encrypt s3 buckets
resource "aws_kms_key" "s3_encryption" {
  description = "KMS key for S3 bucket encryption"
  enable_key_rotation = true
  policy = jsonencode({
    Version = "2012-10-17",
    Id      = "key-default-1",
    Statement = [
      {
        Sid       = "AllowRootAccountFullAccess",
        Effect    = "Allow",
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" # "arn:aws:iam::123456789012:root" hardcode if doesn't work
        },
        Action    = "kms:*",
        Resource  = "*"
      },
      {
        Sid       = "AllowGlueToUseKey",
        Effect    = "Allow",
        Principal = {
          AWS = var.glue_role_arn
        },
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ],
        Resource = "*"
      }
    ]
  })
}

# S3 Buckets for data storage
resource "aws_s3_bucket" "exim_core" {
  bucket = "${var.project_name}-exim-core-${var.environment}"

  tags = {
    Name        = "${var.project_name}-exim-core"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exim_core" {
  bucket = aws_s3_bucket.exim_core.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_encryption.arn
    }
  }
}


resource "aws_s3_bucket" "exim_cost" {
  bucket = "${var.project_name}-exim-cost-${var.environment}"

  tags = {
    Name        = "${var.project_name}-exim-cost"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exim_cost" {
  bucket = aws_s3_bucket.exim_cost.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_encryption.arn
    }
  }
}

resource "aws_s3_bucket" "exim_rm" {
  bucket = "${var.project_name}-exim-rm-${var.environment}"

  tags = {
    Name        = "${var.project_name}-exim-rm"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exim_rm" {
  bucket = aws_s3_bucket.exim_rm.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_encryption.arn
    }
  }
}

# resource "aws_s3_bucket" "athena_results" {
#   bucket = "${var.project_name}-athena-results-${var.environment}"
#   tags = {
#     Name = "${var.project_name}-athena-results"
#     Environment = var.environment
#   }
# }