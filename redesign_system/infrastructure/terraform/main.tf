/**
 * Main Terraform Configuration
 * Document Generation AI System - AWS Infrastructure
 */

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.75"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.34"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.16"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14"
    }
  }

  backend "s3" {
    bucket         = "docgenai-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# Provider Configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "DocGenAI"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "Platform Team"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local variables
locals {
  name            = "docgenai-${var.environment}"
  cluster_name    = "${local.name}-eks"
  region          = var.aws_region
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)

  tags = {
    Project     = "DocGenAI"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ============================================================================
# VPC and Networking
# ============================================================================

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr

  azs             = local.azs
  private_subnets = [for k, v in local.azs : cidrsubnet(var.vpc_cidr, 4, k)]
  public_subnets  = [for k, v in local.azs : cidrsubnet(var.vpc_cidr, 4, k + 3)]
  database_subnets = [for k, v in local.azs : cidrsubnet(var.vpc_cidr, 4, k + 6)]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "production"
  enable_dns_hostnames = true
  enable_dns_support   = true

  # VPC Flow Logs
  enable_flow_log                      = true
  create_flow_log_cloudwatch_iam_role  = true
  create_flow_log_cloudwatch_log_group = true

  # Kubernetes tags
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
    "kubernetes.io/cluster/${local.cluster_name}" = "shared"
  }

  tags = local.tags
}

# VPC Endpoints for cost optimization
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = module.vpc.vpc_id
  service_name = "com.amazonaws.${local.region}.s3"

  tags = merge(local.tags, {
    Name = "${local.name}-s3-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${local.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = module.vpc.private_subnets
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = merge(local.tags, {
    Name = "${local.name}-ecr-api-endpoint"
  })
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${local.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = module.vpc.private_subnets
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = merge(local.tags, {
    Name = "${local.name}-ecr-dkr-endpoint"
  })
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.name}-vpc-endpoints"
  description = "Security group for VPC endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

# ============================================================================
# EKS Cluster
# ============================================================================

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = local.cluster_name
  cluster_version = var.kubernetes_version

  # Cluster access
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Encryption
  cluster_encryption_config = {
    provider_key_arn = aws_kms_key.eks.arn
    resources        = ["secrets"]
  }

  # Logging
  cluster_enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    # System node group
    system = {
      name           = "${local.name}-system"
      instance_types = ["t3.large"]
      capacity_type  = "ON_DEMAND"

      min_size     = 3
      max_size     = 6
      desired_size = 3

      labels = {
        workload-type = "system"
      }

      tags = merge(local.tags, {
        Name = "${local.name}-system-nodegroup"
      })
    }

    # Application node group (Spot + On-Demand)
    application = {
      name           = "${local.name}-application"
      instance_types = ["c6i.2xlarge", "c6i.4xlarge"]
      capacity_type  = "SPOT"

      min_size     = 2
      max_size     = 20
      desired_size = 5

      labels = {
        workload-type = "application"
      }

      taints = []

      tags = merge(local.tags, {
        Name = "${local.name}-application-nodegroup"
      })
    }

    # ML GPU node group
    ml_gpu = {
      name           = "${local.name}-ml-gpu"
      instance_types = ["g5.xlarge"]
      capacity_type  = "ON_DEMAND"

      min_size     = 0
      max_size     = 10
      desired_size = 0

      labels = {
        workload-type = "ml-gpu"
        gpu-type      = "nvidia-a10g"
      }

      taints = [
        {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      ]

      tags = merge(local.tags, {
        Name = "${local.name}-ml-gpu-nodegroup"
      })
    }
  }

  # IRSA for pod-level IAM permissions
  enable_irsa = true

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
      configuration_values = jsonencode({
        env = {
          ENABLE_PREFIX_DELEGATION = "true"
          WARM_PREFIX_TARGET       = "1"
        }
      })
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
    eks-pod-identity-agent = {
      most_recent = true
    }
  }

  tags = local.tags
}

# KMS Key for EKS
resource "aws_kms_key" "eks" {
  description             = "EKS Secret Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-eks-kms"
  })
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${local.name}-eks"
  target_key_id = aws_kms_key.eks.key_id
}

# ============================================================================
# Kubernetes Provider Configuration
# ============================================================================

data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_name
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.cluster.token
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    token                  = data.aws_eks_cluster_auth.cluster.token
  }
}

provider "kubectl" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.cluster.token
  load_config_file       = false
}

# ============================================================================
# RDS Aurora PostgreSQL
# ============================================================================

module "aurora" {
  source  = "terraform-aws-modules/rds-aurora/aws"
  version = "~> 9.0"

  name              = "${local.name}-aurora"
  engine            = "aurora-postgresql"
  engine_version    = "16.1"
  instance_class    = "db.r6g.xlarge"
  instances = {
    1 = {}
    2 = {}
  }

  vpc_id                  = module.vpc.vpc_id
  db_subnet_group_name    = module.vpc.database_subnet_group_name
  create_db_subnet_group  = false
  create_security_group   = true
  allowed_cidr_blocks     = module.vpc.private_subnets_cidr_blocks

  storage_encrypted   = true
  kms_key_id          = aws_kms_key.rds.arn
  apply_immediately   = false
  skip_final_snapshot = var.environment != "production"

  # Backup
  backup_retention_period      = 35
  preferred_backup_window      = "03:00-04:00"
  preferred_maintenance_window = "mon:04:00-mon:05:00"

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql"]
  monitoring_interval             = 60
  create_monitoring_role          = true

  # Autoscaling
  autoscaling_enabled      = true
  autoscaling_min_capacity = 2
  autoscaling_max_capacity = 5

  database_name   = "docgenai"
  master_username = "postgres"
  master_password = var.db_master_password  # Use AWS Secrets Manager in production
  port            = 5432

  tags = local.tags
}

# KMS Key for RDS
resource "aws_kms_key" "rds" {
  description             = "RDS Aurora Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-rds-kms"
  })
}

# ============================================================================
# DynamoDB Tables
# ============================================================================

resource "aws_dynamodb_table" "sessions" {
  name           = "${local.name}-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "user_id-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  tags = local.tags
}

resource "aws_dynamodb_table" "document_metadata" {
  name           = "${local.name}-document-metadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "document_id"
  range_key      = "version"

  attribute {
    name = "document_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "N"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "user_id-created_at-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "status-created_at-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  tags = local.tags
}

# KMS Key for DynamoDB
resource "aws_kms_key" "dynamodb" {
  description             = "DynamoDB Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-dynamodb-kms"
  })
}

# ============================================================================
# ElastiCache Redis
# ============================================================================

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${local.name}-redis-subnet"
  subnet_ids = module.vpc.private_subnets

  tags = local.tags
}

resource "aws_security_group" "redis" {
  name        = "${local.name}-redis"
  description = "Security group for ElastiCache Redis"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = "${local.name}-redis"
  replication_group_description = "Redis cluster for DocGenAI"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.r7g.large"
  number_cache_clusters      = 2
  parameter_group_name       = "default.redis7"
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.redis.name
  security_group_ids         = [aws_security_group.redis.id]
  automatic_failover_enabled = true
  multi_az_enabled           = true
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token_enabled         = true
  auth_token                 = var.redis_auth_token

  snapshot_retention_limit = 5
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "mon:05:00-mon:07:00"

  tags = local.tags
}

# ============================================================================
# S3 Buckets
# ============================================================================

# Documents bucket
module "s3_documents" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket = "${local.name}-documents"

  # Versioning
  versioning = {
    enabled = true
  }

  # Encryption
  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = aws_kms_key.s3.arn
      }
    }
  }

  # Lifecycle rules
  lifecycle_rule = [
    {
      id      = "transition-to-ia"
      enabled = true

      transition = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        }
      ]

      expiration = {
        days = 365
      }
    }
  ]

  # Block public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  tags = local.tags
}

# Models bucket
module "s3_models" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket = "${local.name}-models"

  versioning = {
    enabled = true
  }

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle_rule = [
    {
      id      = "cleanup-old-versions"
      enabled = true

      noncurrent_version_expiration = {
        days = 180
      }
    }
  ]

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  tags = local.tags
}

# KMS Key for S3
resource "aws_kms_key" "s3" {
  description             = "S3 Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-s3-kms"
  })
}

# ============================================================================
# ECR Repositories
# ============================================================================

resource "aws_ecr_repository" "ml_service" {
  name                 = "${local.name}/ml-service"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = aws_kms_key.ecr.arn
  }

  tags = local.tags
}

resource "aws_ecr_lifecycle_policy" "ml_service" {
  repository = aws_ecr_repository.ml_service.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# KMS Key for ECR
resource "aws_kms_key" "ecr" {
  description             = "ECR Encryption Key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(local.tags, {
    Name = "${local.name}-ecr-kms"
  })
}
