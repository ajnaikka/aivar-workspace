## Lambda Function Configuration
resource "aws_lambda_function" "schema_extractor" {
  function_name    = "athena-schema-extractor"
  role             = aws_iam_role.lambda_exec_schema_extractor.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  filename         = data.archive_file.lambda_code.output_path
  source_code_hash = data.archive_file.lambda_code.output_base64sha256
  timeout          = 600
  memory_size      = 128

#   vpc_config {
#     # Every subnet should be able to reach an EFS mount target in the same Availability Zone. Cross-AZ mounts are not permitted.
#     subnet_ids         = [aws_subnet.subnet_for_lambda.id]
#     security_group_ids = [aws_security_group.sg_for_lambda.id]
#   }

  environment {
    variables = {
      S3_BUCKET         = "athena-neptune-data"
      S3_TARGET_PATH    = "neptune-nodes-data/"
      S3_OUTPUT_LOCATION = "s3://pando-freight-agent/output/"
    }
  }
   layers = [
    "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python313:1"
  ]
}

## IAM Execution Role
resource "aws_iam_role" "lambda_exec_schema_extractor" {
  name = "lambda-athena-neptune-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

## Custom IAM Policy
resource "aws_iam_policy" "lambda_schema_extractor_policy" {
  name        = "AthenaNeptuneDataAccess"
  description = "Permissions for Athena and S3 access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::athena-neptune-data/*",
          "arn:aws:s3:::pando-freight-agent/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

## Policy Attachment
resource "aws_iam_role_policy_attachment" "lambda_permissions" {
  role       = aws_iam_role.lambda_exec_schema_extractor.name
  policy_arn = aws_iam_policy.lambda_schema_extractor_policy.arn
}

## Lambda Deployment Package
data "archive_file" "lambda_code" {
  type        = "zip"
  source_dir  = "${path.module}/schema-extractor"
  output_path = "${path.module}/lambda_package(schema-extractor).zip"
}

#------------------------


resource "aws_iam_role" "lambda_exec_s3-kb_role" {
  name = "lambda_s3-kb_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "lambda_s3-kb_policy" {
  name        = "lambda_s3-kb_policy"
  description = "Permissions for lambda_s3-kb to access Athena and S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          "arn:aws:s3:::pando-db-auto-schema/*",
          "arn:aws:s3:::pando-freight-agent/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

## Policy Attachment
resource "aws_iam_role_policy_attachment" "s3-kb_policy_attachment" {
  role       = aws_iam_role.lambda_exec_s3-kb_role.name
  policy_arn = aws_iam_policy.lambda_s3-kb_policy.arn
}

# Package Lambda code
data "archive_file" "s3-kb" {
  type        = "zip"
  source_dir  = "${path.module}/s3-kb"
  output_path = "${path.module}/lambda_package(s3-kb).zip"
}


resource "aws_lambda_function" "lambda_s3-kb" {
  function_name    = "s3-kb"
  role             = aws_iam_role.lambda_exec_s3-kb_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  filename         = data.archive_file.s3-kb.output_path
  source_code_hash = data.archive_file.s3-kb.output_base64sha256
  timeout          = 600
  memory_size      = 128

#   vpc_config {
#     # Every subnet should be able to reach an EFS mount target in the same Availability Zone. Cross-AZ mounts are not permitted.
#     subnet_ids         = [aws_subnet.subnet_for_lambda.id]
#     security_group_ids = [aws_security_group.sg_for_lambda.id]
#   }

  environment {
    variables = {
      S3_BUCKET         = "pando-db-auto-schema"
      S3_OUTPUT_LOCATION = "s3://pando-freight-agent/output/"
    }
  }
#    layers = [
#     "arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python313:1"
#   ]
}

# --------------------------------

resource "aws_iam_role" "lambda_exec_freight_audit_role" {
  name = "lambda_freight_audit_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "lambda_freight_audit_policy" {
  name        = "lambda_freight_audit_policy"
  description = "Permissions for lambda_freight_audit to access Athena,S3,cw,ec2"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          "*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow",
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "firehose:PutRecord"
        ],
        Resource = "*" # "arn:aws:firehose:us-east-1:354602095398:deliverystream/observability_firehose-opensearch-stream"
      },
      {
        Effect = "Allow",
        Action = "bedrock:*",
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = "glue:*",
        Resource = "*"
      }
    ]
  })
}

## Policy Attachment
resource "aws_iam_role_policy_attachment" "freight_audit_policy_attachment" {
  role       = aws_iam_role.lambda_exec_freight_audit_role.name
  policy_arn = aws_iam_policy.lambda_freight_audit_policy.arn
}

# Package Lambda code
data "archive_file" "freight_audit" {
  type        = "zip"
  source_dir  = "${path.module}/freight_audit"
  output_path = "${path.module}/lambda_package(freight_audit).zip"
}


resource "aws_lambda_function" "lambda_freight_audit" {
  function_name    = "freight_audit"
  role             = aws_iam_role.lambda_exec_freight_audit_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  filename         = data.archive_file.freight_audit.output_path
  source_code_hash = data.archive_file.freight_audit.output_base64sha256
  timeout          = 600
  memory_size      = 128

#   vpc_config {
#     # Every subnet should be able to reach an EFS mount target in the same Availability Zone. Cross-AZ mounts are not permitted.
#     subnet_ids         = [aws_subnet.subnet_for_lambda.id]
#     security_group_ids = [aws_security_group.sg_for_lambda.id]
#   }

  environment {
    variables = {
      REGION = "us-east-1"
      FIREHOSE_NAME = "observability_firehose-opensearch-stream"
      EXPERIMENT_ID = "freight-audit-project"
      INFERENCE_PROFILE_ARN = "arn:aws:bedrock:us-east-1:354602095398:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    
    # athena settings
      DATABASE_NAME = "pando_invoice"
      OUTPUT_LOCATION = "s3://pando-freight-agent/ouput/"
      SCHEMA_KNOWLEDGE_BASE_ID = "QUXIDJXHOE" 
      PREV_EXAMPLES_KNOWLEDGE_BASE_ID = "IXTFQ5BLSJ"
      SCORE_THRESHOLD = 0.90    
    }
  }
#    layers = [
#     "arn:aws:lambda:us-east-1:354602095398:layer:pytz-layer:2",
#     "arn:aws:lambda:us-east-1:354602095398:layer:gremlin:2"
#   ]
}

resource "aws_lambda_permission" "public_invoke_freight_audit" {
  statement_id  = "FunctionURLAllowPublicAccess"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.lambda_freight_audit.function_name
  principal     = "*"
  function_url_auth_type = "NONE"
}

