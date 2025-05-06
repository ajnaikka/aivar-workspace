output "athena_database" {
  description = "Athena database name"
  value       = aws_glue_catalog_database.athena_db.name
}

output "glue_role_arn" {
  description = "ARN of glue_role"
  value       = aws_iam_role.glue_role.arn
}