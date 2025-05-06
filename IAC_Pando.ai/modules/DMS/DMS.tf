# DMS Resources
##########################

resource "aws_dms_replication_subnet_group" "subnet_group" {
  replication_subnet_group_id          = "${var.project_name}-subnet-group"
  replication_subnet_group_description = "DMS subnet group"
  subnet_ids                           = var.private_subnet_ids
}

resource "aws_dms_replication_instance" "instance" {
  replication_instance_id      = "${var.project_name}-dms-instance"
  replication_instance_class   = "dms.t3.large"
  allocated_storage            = 50
  vpc_security_group_ids       = [var.dms_sg_id]
  replication_subnet_group_id  = aws_dms_replication_subnet_group.subnet_group.id
  publicly_accessible          = false
  multi_az                     = false
  depends_on = [aws_iam_role_policy_attachment.dms_attachment]
}

resource "aws_dms_endpoint" "source" {
  endpoint_id   = "${var.project_name}-source"
  endpoint_type = "source"
  engine_name   = "postgres"
  
  server_name   = var.postgres_server
  database_name = var.postgres_database
  username      = var.postgres_username
  password      = var.postgres_password
  port          = 5432
}

resource "aws_dms_endpoint" "target_exim_core" {
  endpoint_id   = "${var.project_name}-target-exim-core"
  endpoint_type = "target"
  engine_name   = "s3"
  
  s3_settings {
    bucket_name             = var.s3_buckets.exim_core.name
    service_access_role_arn = aws_iam_role.dms_role.arn
    data_format             = "parquet"
  }
}

resource "aws_dms_endpoint" "target_exim_cost" {
  endpoint_id   = "${var.project_name}-target-exim-cost"
  endpoint_type = "target"
  engine_name   = "s3"
  
  s3_settings {
    bucket_name             = var.s3_buckets.exim_cost.name
    service_access_role_arn = aws_iam_role.dms_role.arn
    data_format             = "parquet"
  }
}

resource "aws_dms_endpoint" "target_exim_rm" {
  endpoint_id   = "${var.project_name}-target-exim-rm"
  endpoint_type = "target"
  engine_name   = "s3"
  
  s3_settings {
    bucket_name             = var.s3_buckets.exim_rm.name
    service_access_role_arn = aws_iam_role.dms_role.arn
    data_format             = "parquet"
  }
}

resource "aws_dms_replication_task" "task_exim_core" {
  replication_task_id       = "${var.project_name}-task-exim-core"
  replication_instance_arn  = aws_dms_replication_instance.instance.replication_instance_arn
  source_endpoint_arn       = aws_dms_endpoint.source.endpoint_arn
  target_endpoint_arn       = aws_dms_endpoint.target_exim_core.endpoint_arn
  migration_type            = "full-load-and-cdc"

  replication_task_settings = jsonencode({
    TargetMetadata = {
      TargetSchema = ""
    }
    FullLoadSettings = {
      TargetTablePrepMode = "DROP_AND_CREATE"
    }
    ChangeDataCaptureSettings = {
      TimestampColumnName = "last_updated_at" # 🔁 Replace with actual column name from your source tables
    }
    Logging = {
      EnableLogging = true
    }
  })

  table_mappings            = jsonencode({
    rules = [{
      rule-type = "selection"
      rule-id = "1"
      rule-name = "exim_core_tables"
      object-locator = {
        schema-name = "%"
        table-name = "exim_core_%"
      }
      rule-action = "include"
    }]
  })
}

resource "aws_dms_replication_task" "task_exim_cost" {
  replication_task_id       = "${var.project_name}-task-exim-cost"
  replication_instance_arn  = aws_dms_replication_instance.instance.replication_instance_arn
  source_endpoint_arn       = aws_dms_endpoint.source.endpoint_arn
  target_endpoint_arn       = aws_dms_endpoint.target_exim_cost.endpoint_arn
  migration_type            = "full-load-and-cdc"

  replication_task_settings = jsonencode({
    TargetMetadata = {
      TargetSchema = ""
    }
    FullLoadSettings = {
      TargetTablePrepMode = "DROP_AND_CREATE"
    }
    ChangeDataCaptureSettings = {
      TimestampColumnName = "last_updated_at" # 🔁 Replace with actual column name from your source tables
    }
    Logging = {
      EnableLogging = true
    }
  })

  table_mappings            = jsonencode({
    rules = [{
      rule-type = "selection"
      rule-id = "1"
      rule-name = "exim_cost_tables"
      object-locator = {
        schema-name = "%"
        table-name = "exim_cost_%"
      }
      rule-action = "include"
    }]
  })
}

resource "aws_dms_replication_task" "task_exim_rm" {
  replication_task_id       = "${var.project_name}-task-exim-rm"
  replication_instance_arn  = aws_dms_replication_instance.instance.replication_instance_arn
  source_endpoint_arn       = aws_dms_endpoint.source.endpoint_arn
  target_endpoint_arn       = aws_dms_endpoint.target_exim_rm.endpoint_arn
  migration_type            = "full-load-and-cdc"

  replication_task_settings = jsonencode({
    TargetMetadata = {
      TargetSchema = ""
    }
    FullLoadSettings = {
      TargetTablePrepMode = "DROP_AND_CREATE"
    }
    ChangeDataCaptureSettings = {
      TimestampColumnName = "last_updated_at" # 🔁 Replace with actual column name from your source tables
    }
    Logging = {
      EnableLogging = true
    }
  })

  table_mappings            = jsonencode({
    rules = [{
      rule-type = "selection"
      rule-id = "1"
      rule-name = "exim_rm_tables"
      object-locator = {
        schema-name = "%"
        table-name = "exim_rm_%"
      }
      rule-action = "include"
    }]
  })
}





# resource "aws_iam_role" "dms_role" {
#   name = "${var.project_name}-dms-role"
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Action = "sts:AssumeRole"
#       Effect = "Allow"
#       Principal = {
#         Service = "dms.amazonaws.com"
#       }
#     }]
#   })
# }

resource "aws_iam_role" "dms_role" {
  name = "${var.project_name}-dms-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "AWSDMSVPCPolicyTemplate"
        Effect = "Allow"
        Principal = {
          Service = "dms.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = "952262428733"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "dms_inline_policy" {
  name = "DMSVPCAccessPolicy"
  role = aws_iam_role.dms_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CreateNetworkInterface"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DeleteNetworkInterface",
          "ec2:ModifyNetworkInterfaceAttribute"
        ]
        Resource = [
          "arn:aws:ec2:*:952262428733:network-interface/*",
          "arn:aws:ec2:*:952262428733:instance/*",
          "arn:aws:ec2:*:952262428733:subnet/*",
          "arn:aws:ec2:*:952262428733:security-group/*"
        ]
      },
      {
        Sid    = "DescribeVPC"
        Effect = "Allow"
        Action = [
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeInternetGateways",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeDhcpOptions",
          "ec2:DescribeNetworkInterfaces"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role" "dms_cloudwatch_logs_role" {
  name = "${var.project_name}-dms-cloudwatch-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "AWSDMSCloudWatchPolicyTemplate"
        Effect = "Allow"
        Principal = {
          Service = "dms.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = "952262428733"
          }
        }
      }
    ]
  })
}


resource "aws_iam_role_policy" "dms_cloudwatch_logs_policy" {
  name = "DMSCloudWatchLogsPolicy"
  role = aws_iam_role.dms_cloudwatch_logs_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid = "AllowDescribeOnAllLogGroups"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups"
        ]
        Resource = [
          "arn:aws:logs:*:952262428733:log-group:*"
        ]
      },
      {
        Sid = "AllowDescribeOfAllLogStreamsOnDmsTasksLogGroup"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:*:952262428733:log-group:dms-tasks-*",
          "arn:aws:logs:*:952262428733:log-group:dms-serverless-replication-*"
        ]
      },
      {
        Sid = "AllowCreationOfDmsLogGroups"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup"
        ]
        Resource = [
          "arn:aws:logs:*:952262428733:log-group:dms-tasks-*",
          "arn:aws:logs:*:952262428733:log-group:dms-serverless-replication-*:log-stream:"
        ]
      },
      {
        Sid = "AllowCreationOfDmsLogStream"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream"
        ]
        Resource = [
          "arn:aws:logs:*:952262428733:log-group:dms-tasks-*:log-stream:dms-task-*",
          "arn:aws:logs:*:952262428733:log-group:dms-serverless-replication-*:log-stream:dms-serverless-*"
        ]
      },
      {
        Sid = "AllowUploadOfLogEventsToDmsLogStream"
        Effect = "Allow"
        Action = [
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:*:952262428733:log-group:dms-tasks-*:log-stream:dms-task-*",
          "arn:aws:logs:*:952262428733:log-group:dms-serverless-replication-*:log-stream:dms-serverless-*"
        ]
      }
    ]
  })
}

# guess the below can be removed
resource "aws_iam_role_policy_attachment" "dms_attachment" {
  role       = aws_iam_role.dms_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonDMSVPCManagementRole"
}

