# Bucket name
output "bucket_schema_kb" {
  value = aws_s3_bucket.schema_kb.bucket
}

# Bucket ARNs
output "bucket_query_history_kb" {
  value = aws_s3_bucket.query_history_kb.bucket
}