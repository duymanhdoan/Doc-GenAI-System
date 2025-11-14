/**
 * Terraform Outputs
 */

# VPC Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnets" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "public_subnets" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

# EKS Outputs
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_version" {
  description = "EKS cluster version"
  value       = module.eks.cluster_version
}

output "eks_cluster_oidc_issuer_url" {
  description = "OIDC issuer URL"
  value       = module.eks.cluster_oidc_issuer_url
}

output "eks_cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "configure_kubectl" {
  description = "Configure kubectl command"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

# RDS Outputs
output "rds_cluster_endpoint" {
  description = "Aurora cluster endpoint"
  value       = module.aurora.cluster_endpoint
  sensitive   = true
}

output "rds_cluster_reader_endpoint" {
  description = "Aurora reader endpoint"
  value       = module.aurora.cluster_reader_endpoint
  sensitive   = true
}

output "rds_cluster_id" {
  description = "Aurora cluster ID"
  value       = module.aurora.cluster_id
}

output "rds_cluster_database_name" {
  description = "Database name"
  value       = module.aurora.cluster_database_name
}

# DynamoDB Outputs
output "dynamodb_sessions_table" {
  description = "DynamoDB sessions table name"
  value       = aws_dynamodb_table.sessions.name
}

output "dynamodb_document_metadata_table" {
  description = "DynamoDB document metadata table name"
  value       = aws_dynamodb_table.document_metadata.name
}

# ElastiCache Outputs
output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

# S3 Outputs
output "s3_documents_bucket" {
  description = "S3 documents bucket name"
  value       = module.s3_documents.s3_bucket_id
}

output "s3_models_bucket" {
  description = "S3 models bucket name"
  value       = module.s3_models.s3_bucket_id
}

# ECR Outputs
output "ecr_ml_service_repository_url" {
  description = "ECR ML service repository URL"
  value       = aws_ecr_repository.ml_service.repository_url
}

# Region
output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "aws_account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}
