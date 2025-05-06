# data "aws_caller_identity" "current" {}

# Schema Knowledge Base
resource "aws_s3_bucket" "schema_kb" {
  bucket = "${var.project_name}-schema-kb-${var.environment}"
  tags = {
    Name = "Schema Knowledge Base"
  }
}

# Query History Knowledge Base
resource "aws_s3_bucket" "query_history_kb" {
  bucket = "${var.project_name}-query-history-kb-${var.environment}"
  tags = {
    Name = "Query History Knowledge Base"
  }
}


resource "aws_bedrockagent_knowledge_base" "schema_kb" {
  name     = "schema-knowledgebase"
  role_arn = aws_iam_role.bedrock_role.arn
  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }

      supplemental_data_storage_configuration {
        storage_location {
          type = "S3"

          s3_location {
            uri = "s3://${var.project_name}-schema-kb-${var.environment}/"
          }
        }
      }
    }
    type = "VECTOR"
  }
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.schema_kb.arn
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  depends_on = [ aws_opensearchserverless_collection.schema_kb,opensearch_index.schema_kb]
  
}

resource "aws_iam_role" "bedrock_role" {
  name = "bedrock-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "bedrock.amazonaws.com"  # or relevant service
      },
      Action = "sts:AssumeRole"
    }]
  })
}


resource "aws_iam_policy" "bedrock_kb_policy" {
  name = "BedrockKBPolicy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = ["s3:*",
        ],
        Resource = ["${aws_s3_bucket.schema_kb.arn}/*",
        "${aws_s3_bucket.schema_kb.arn}",
        "${aws_s3_bucket.query_history_kb.arn}",
        "${aws_s3_bucket.query_history_kb.arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = ["aoss:APIAccessAll",
          "aoss:DescribeCollection",
          "aoss:ReadDocument",
          "aoss:QueryIndex"],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "bedrock:InvokeModel"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_bedrock_kb_policy" {
  role       = aws_iam_role.bedrock_role.name
  policy_arn = aws_iam_policy.bedrock_kb_policy.arn
}

resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name = "opensearch-encryption-policy"
  type = "encryption"
  policy = jsonencode({
    "Rules" = [
      {
        "Resource" = [
          "collection/schema-kb"
        ],
        "ResourceType" = "collection"
      }
    ],
    "AWSOwnedKey" = true
  })
}

resource "aws_opensearchserverless_collection" "schema_kb" {
  name = "schema-kb"
  type = "VECTORSEARCH"

  depends_on = [aws_opensearchserverless_security_policy.encryption_policy ]
}


resource "aws_opensearchserverless_security_policy" "network_policy" {
  name        = "opensearch-network-policy"
  type        = "network"
  description = "Public access"
  policy = jsonencode([
    {
      Description = "Public access to collection and Dashboards endpoint for example collection",
      Rules = [
        {
          ResourceType = "collection",
          Resource = [
            "collection/schema-kb"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/schema-kb"
          ]
        }
      ],
      AllowFromPublic = true
    }
  ])
}

data "aws_caller_identity" "current" {}

resource "aws_opensearchserverless_access_policy" "data_access_policy" {
  name        = "opensearch-data-access-policy"
  type        = "data"
  description = "read and write permissions"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index",
          Resource = [
            "index/schema-kb/*"
          ],
          Permission = [
            "aoss:*"
          ]
        },
        {
          ResourceType = "collection",
          Resource = [
            "collection/schema-kb"
          ],
          Permission = [
            "aoss:*"
          ]
        }
      ],
      Principal = [
        data.aws_caller_identity.current.arn,
        aws_iam_role.bedrock_role.arn
      ]
    }
  ])
}

# resource "aws_s3_bucket_policy" "schema_kb_policy" {
#   bucket = aws_s3_bucket.schema_kb.id
#   policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Sid       = "AllowBedrockToRead",
#         Effect    = "Allow",
#         Principal = {
#           AWS = aws_iam_role.bedrock_role.arn
#         },
#         Action = [
#           "s3:GetObject",
#           "s3:ListBucket"
#         ],
#         Resource = [
#           "${aws_s3_bucket.schema_kb.arn}",
#           "${aws_s3_bucket.schema_kb.arn}/*"
#         ]
#       }
#     ]
#   })
# }

# -------------------------------------


resource "aws_bedrockagent_knowledge_base" "query_history_kb" {
  name     = "query-history-knowledgebase"
  role_arn = aws_iam_role.bedrock_role.arn
  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }

      supplemental_data_storage_configuration {
        storage_location {
          type = "S3"

          s3_location {
            uri = "s3://${var.project_name}-query-history-kb-${var.environment}/"
          }
        }
      }
    }
    type = "VECTOR"
  }
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.query_history_kb.arn
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  depends_on = [ aws_opensearchserverless_collection.query_history_kb, opensearch_index.query_history_kb ]
}


resource "aws_opensearchserverless_security_policy" "query_history_encryption_policy" {
  name = "encryption-policy-query-history"
  type = "encryption"
  policy = jsonencode({
    "Rules" = [
      {
        "Resource" = [
          "collection/query-history-kb"
        ],
        "ResourceType" = "collection"
      }
    ],
    "AWSOwnedKey" = true
  })
}

resource "aws_opensearchserverless_collection" "query_history_kb" {
  name = "query-history-kb"
  type = "VECTORSEARCH"

  depends_on = [aws_opensearchserverless_security_policy.query_history_encryption_policy ]
}


resource "aws_opensearchserverless_security_policy" "query_history_network_policy" {
  name        = "network-policy-query-history-kb"
  type        = "network"
  description = "Public access"
  policy = jsonencode([
    {
      Description = "Public access to collection and Dashboards endpoint for example collection",
      Rules = [
        {
          ResourceType = "collection",
          Resource = [
            "collection/query-history-kb"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/query-history-kb"
          ]
        }
      ],
      AllowFromPublic = true
    }
  ])
}


resource "aws_opensearchserverless_access_policy" "query_history_data_access_policy" {
  name        = "data-access-policy-query-history"
  type        = "data"
  description = "read and write permissions"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index",
          Resource = [
            "index/query-history-kb/*"
          ],
          Permission = [
            "aoss:*"
          ]
        },
        {
          ResourceType = "collection",
          Resource = [
            "collection/query-history-kb"
          ],
          Permission = [
            "aoss:*"
          ]
        }
      ],
      Principal = [
        data.aws_caller_identity.current.arn,
        aws_iam_role.bedrock_role.arn
      ]
    }
  ])
}

# resource "aws_s3_bucket_policy" "query_history_kb_policy" {
#   bucket = aws_s3_bucket.query_history_kb.id
#   policy = jsonencode({
#     Version = "2012-10-17",
#     Statement = [
#       {
#         Sid       = "AllowBedrockToRead",
#         Effect    = "Allow",
#         Principal = {
#           AWS = aws_iam_role.bedrock_role.arn
#         },
#         Action = [
#           "s3:GetObject",
#           "s3:ListBucket"
#         ],
#         Resource = [
#           "${aws_s3_bucket.query_history_kb.arn}",
#           "${aws_s3_bucket.query_history_kb.arn}/*"
#         ]
#       }
#     ]
#   })
# }

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.49.0"
    }
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = "2.3.1"
    }
  }
}

# provider "opensearch" {
#   url         = aws_opensearchserverless_collection.schema_kb.collection_endpoint
#   healthcheck = false
# }

provider "opensearch" {
  alias       = "schema"
  url         = aws_opensearchserverless_collection.schema_kb.collection_endpoint
  healthcheck = false
}

provider "opensearch" {
  alias       = "query"
  url         = aws_opensearchserverless_collection.query_history_kb.collection_endpoint
  healthcheck = false
}


resource "opensearch_index" "schema_kb" {
  provider                       = opensearch.schema
  name                           = "bedrock-knowledge-base-default-index"
  number_of_shards               = "2"
  number_of_replicas             = "0"
  index_knn                      = true
  index_knn_algo_param_ef_search = "512"
  mappings                       = <<-EOF
    {
      "properties": {
        "bedrock-knowledge-base-default-vector": {
          "type": "knn_vector",
          "dimension": 1024,
          "method": {
            "name": "hnsw",
            "engine": "faiss",
            "parameters": {
              "m": 16,
              "ef_construction": 512
            },
            "space_type": "l2"
          }
        },
        "AMAZON_BEDROCK_METADATA": {
          "type": "text",
          "index": "false"
        },
        "AMAZON_BEDROCK_TEXT_CHUNK": {
          "type": "text",
          "index": "true"
        }
      }
    }
  EOF
  force_destroy                  = true
  lifecycle {
    prevent_destroy = true
  }
  depends_on                     = [aws_opensearchserverless_collection.schema_kb]
}

resource "opensearch_index" "query_history_kb" {
  provider                       = opensearch.query
  name                           = "bedrock-knowledge-base-default-index"
  number_of_shards               = "2"
  number_of_replicas             = "0"
  index_knn                      = true
  index_knn_algo_param_ef_search = "512"
  mappings                       = <<-EOF
    {
      "properties": {
        "bedrock-knowledge-base-default-vector": {
          "type": "knn_vector",
          "dimension": 1024,
          "method": {
            "name": "hnsw",
            "engine": "faiss",
            "parameters": {
              "m": 16,
              "ef_construction": 512
            },
            "space_type": "l2"
          }
        },
        "AMAZON_BEDROCK_METADATA": {
          "type": "text",
          "index": "false"
        },
        "AMAZON_BEDROCK_TEXT_CHUNK": {
          "type": "text",
          "index": "true"
        }
      }
    }
  EOF
  force_destroy = true
  lifecycle {
    prevent_destroy = true
  }
  depends_on    = [aws_opensearchserverless_collection.query_history_kb]
}
