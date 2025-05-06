resource "aws_glue_catalog_database" "athena_db" {
  name = "${var.project_name}_athena_db"
}

resource "aws_glue_crawler" "exim_core_crawler" {
  name          = "${var.project_name}-exim-core-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.athena_db.name
  table_prefix = "fba_exim_core_"
  s3_target {
    path = "s3://${var.s3_buckets.exim_core.name}"
  }
  
  schema_change_policy {
    delete_behavior = "LOG"    # Keeps old schema in the catalog, just logs deletions
    update_behavior = "UPDATE_IN_DATABASE"  # Automatically updates the schema in the catalog when new changes appear
  }
}

resource "aws_glue_crawler" "exim_cost_crawler" {
  name          = "${var.project_name}-exim-cost-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.athena_db.name
  table_prefix = "fba_exim_cost_"
  s3_target {
    path = "s3://${var.s3_buckets.exim_cost.name}"
  }
  
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}

resource "aws_glue_crawler" "exim_rm_crawler" {
  name          = "${var.project_name}-exim-rm-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.athena_db.name
  table_prefix = "fba_exim_rm_"
  s3_target {
    path = "s3://${var.s3_buckets.exim_rm.name}"
  }
  
  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }
}




resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-glue-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

# attaching glueservice policy to glue_role
resource "aws_iam_role_policy_attachment" "glue_service_attachment" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# attaching custom policy to glue_role for gule service to read s3 buckets
resource "aws_iam_role_policy" "glue_s3_access" {
  name = "glue-s3-access"
  role = aws_iam_role.glue_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      Effect = "Allow"
      Resource = [
        var.s3_buckets.exim_core.arn,
        "${var.s3_buckets.exim_core.arn}/*",
        var.s3_buckets.exim_cost.arn,
        "${var.s3_buckets.exim_cost.arn}/*",
        var.s3_buckets.exim_rm.arn,
        "${var.s3_buckets.exim_rm.arn}/*"
      ]
    }]
  })
}

resource "aws_iam_role_policy" "glue_kms_access" {
  name = "GlueKMSAccess"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ],
        Resource = var.KMS_Key_arn
      }
    ]
  })
}
