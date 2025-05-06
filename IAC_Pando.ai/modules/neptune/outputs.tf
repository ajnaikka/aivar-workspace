output "neptune_endpoint" {
  description = "Neptune cluster endpoint"
  value       = aws_neptune_cluster.neptune.endpoint
}