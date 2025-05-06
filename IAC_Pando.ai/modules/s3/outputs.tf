# Bucket Names

output "bucket_exim_core" {
  value = aws_s3_bucket.exim_core.bucket
}

output "bucket_exim_cost" {
  value = aws_s3_bucket.exim_cost.bucket
}

output "bucket_exim_rm" {
  value = aws_s3_bucket.exim_rm.bucket
}


# Bucket ARNs
output "bucket_exim_core_arn" {
  value = aws_s3_bucket.exim_core.arn
}

output "bucket_exim_cost_arn" {
  value = aws_s3_bucket.exim_cost.arn
}

output "bucket_exim_rm_arn" {
  value = aws_s3_bucket.exim_rm.arn
}

# KMS arn
output "s3_encryption_kms_key_arn" {
  description = "ARN of the customer-managed KMS key used for S3 encryption"
  value       = aws_kms_key.s3_encryption.arn
}
