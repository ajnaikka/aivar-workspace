output "neptune_notebook_url" {
  description = "URL for Neptune notebook"
  value       = aws_sagemaker_notebook_instance.neptune_notebook.url
}