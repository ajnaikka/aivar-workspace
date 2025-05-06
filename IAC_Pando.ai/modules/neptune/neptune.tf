resource "aws_neptune_subnet_group" "neptune_subnet_group" {
  name       = "${var.project_name}-neptune-subnet-group"
  subnet_ids = var.private_subnet_ids
}

resource "aws_neptune_cluster_parameter_group" "neptune_pg" {
  family      = "neptune1.4"
  name        = "${var.project_name}-neptune-pg"
  description = "Neptune parameter group"
}

resource "aws_neptune_cluster" "neptune" {
  cluster_identifier                  = "${var.project_name}-neptune-cluster"
  engine                              = "neptune"
# engine_mode                         = "serverless"  # enable for serverless
  backup_retention_period             = 7
  preferred_backup_window             = "02:00-03:00"
  skip_final_snapshot                 = true
  vpc_security_group_ids              = [var.neptune_sg_id]
  neptune_subnet_group_name           = aws_neptune_subnet_group.neptune_subnet_group.name
  neptune_cluster_parameter_group_name = aws_neptune_cluster_parameter_group.neptune_pg.name
  iam_roles                             = [aws_iam_role.neptune_load_role.arn]
#   serverless_v2_scaling_configuration {
#     min_capacity = 1
#     max_capacity = 128
#   }

}

# remove the below "aws_neptune_cluster_instance" block for serverless
resource "aws_neptune_cluster_instance" "neptune_instance" {                
  identifier                 = "${var.project_name}-neptune-instance"
  cluster_identifier         = aws_neptune_cluster.neptune.id
  instance_class             = "db.r5.large"
  engine                     = "neptune"
}

resource "aws_iam_role" "neptune_load_role" {
  name = "${var.project_name}-NeptuneLoadFromS3"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "rds.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_readonly" {
  role       = aws_iam_role.neptune_load_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}


resource "aws_iam_policy" "bedrock_access" {
  name = "${var.project_name}-NeptuneBedrockAccess"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid = "BedrockAccess",
        Effect = "Allow",
        Action = "bedrock:*",
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "bedrock_policy_attachment" {
  role       = aws_iam_role.neptune_load_role.name
  policy_arn = aws_iam_policy.bedrock_access.arn
}
