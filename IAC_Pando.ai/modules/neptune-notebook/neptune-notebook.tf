resource "aws_sagemaker_notebook_instance" "neptune_notebook" {
  name                    = "${var.project_name}-neptune-notebook"
  role_arn                = aws_iam_role.sagemaker_role.arn
  instance_type           = "ml.t3.medium"
  subnet_id               = var.private_subnet_ids[0]
  security_groups         = [var.neptune_sg_id]
  direct_internet_access  = "Enabled"
  
  lifecycle_config_name   = aws_sagemaker_notebook_instance_lifecycle_configuration.neptune_config.name
}

resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "neptune_config" {
  name = "${var.project_name}-neptune-notebook-config"
  
  on_create = base64encode(<<-EOF
    #!/bin/bash
    set -e
    
    # Install Neptune workbench
    cd /tmp
    git clone https://github.com/aws/graph-notebook.git
    cd graph-notebook
    pip install .
    
    # Configure connection to Neptune
    echo "NEPTUNE_CLUSTER_ENDPOINT=${var.neptune_cluster_endpoint}" >> /etc/environment
    echo "NEPTUNE_PORT=8182" >> /etc/environment
  EOF
  )
}


resource "aws_iam_role" "sagemaker_role" {
  name = "${var.project_name}-sagemaker-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "sagemaker.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_execution" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy" "sagemaker_neptune_access" {
  name = "sagemaker-neptune-access"
  role = aws_iam_role.sagemaker_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = ["neptune-db:*"]
      Effect = "Allow"
      Resource = "*"
    }]
  })
}