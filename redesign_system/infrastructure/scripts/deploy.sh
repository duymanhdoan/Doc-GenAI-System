#!/bin/bash

###############################################################################
# Deployment Script for Document Generation AI System
# This script deploys the infrastructure and applications to AWS
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-production}"
AWS_REGION="${2:-us-east-1}"
TERRAFORM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform" && pwd)"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed"
        exit 1
    fi

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check Helm
    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed"
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials are not configured"
        exit 1
    fi

    log_info "All prerequisites met"
}

create_terraform_backend() {
    log_info "Creating Terraform backend resources..."

    local bucket_name="docgenai-terraform-state"
    local table_name="terraform-state-lock"

    # Create S3 bucket for state
    if ! aws s3 ls "s3://${bucket_name}" &> /dev/null; then
        log_info "Creating S3 bucket: ${bucket_name}"
        aws s3 mb "s3://${bucket_name}" --region "${AWS_REGION}"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${bucket_name}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${bucket_name}" \
            --server-side-encryption-configuration '{
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }]
            }'
    else
        log_info "S3 bucket already exists: ${bucket_name}"
    fi

    # Create DynamoDB table for locking
    if ! aws dynamodb describe-table --table-name "${table_name}" &> /dev/null; then
        log_info "Creating DynamoDB table: ${table_name}"
        aws dynamodb create-table \
            --table-name "${table_name}" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "${AWS_REGION}"

        # Wait for table to be active
        aws dynamodb wait table-exists --table-name "${table_name}"
    else
        log_info "DynamoDB table already exists: ${table_name}"
    fi
}

terraform_init() {
    log_info "Initializing Terraform..."
    cd "${TERRAFORM_DIR}"

    terraform init \
        -backend-config="region=${AWS_REGION}" \
        -backend-config="key=${ENVIRONMENT}/terraform.tfstate"
}

terraform_plan() {
    log_info "Planning Terraform changes..."
    cd "${TERRAFORM_DIR}"

    terraform plan \
        -var="environment=${ENVIRONMENT}" \
        -var="aws_region=${AWS_REGION}" \
        -out=tfplan
}

terraform_apply() {
    log_info "Applying Terraform changes..."
    cd "${TERRAFORM_DIR}"

    terraform apply tfplan

    log_info "Infrastructure deployment completed"
}

configure_kubectl() {
    log_info "Configuring kubectl..."

    local cluster_name=$(terraform output -raw eks_cluster_name)

    aws eks update-kubeconfig \
        --region "${AWS_REGION}" \
        --name "${cluster_name}"

    log_info "kubectl configured for cluster: ${cluster_name}"
}

wait_for_nodes() {
    log_info "Waiting for EKS nodes to be ready..."

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        local ready_nodes=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || true)

        if [ "$ready_nodes" -gt 0 ]; then
            log_info "EKS nodes are ready (${ready_nodes} nodes)"
            return 0
        fi

        attempt=$((attempt + 1))
        log_info "Waiting for nodes... (${attempt}/${max_attempts})"
        sleep 10
    done

    log_error "Timeout waiting for nodes to be ready"
    return 1
}

install_addons() {
    log_info "Installing Kubernetes add-ons..."

    # Install AWS Load Balancer Controller
    log_info "Installing AWS Load Balancer Controller..."
    helm repo add eks https://aws.github.io/eks-charts
    helm repo update

    helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
        -n kube-system \
        --set clusterName=$(terraform output -raw eks_cluster_name) \
        --set serviceAccount.create=true \
        --set region=${AWS_REGION} \
        --wait

    # Install metrics-server
    log_info "Installing metrics-server..."
    kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

    log_info "Add-ons installed"
}

deploy_applications() {
    log_info "Deploying applications via ArgoCD..."

    # Wait for ArgoCD to be ready
    kubectl wait --for=condition=available --timeout=300s \
        deployment/argocd-server -n argocd

    # Get ArgoCD password
    local argocd_password=$(kubectl -n argocd get secret argocd-initial-admin-secret \
        -o jsonpath='{.data.password}' | base64 -d)

    log_info "ArgoCD is ready"
    log_info "ArgoCD admin password: ${argocd_password}"

    # ArgoCD will automatically sync applications from Git
    log_info "ArgoCD will sync applications from Git repository"
}

display_outputs() {
    log_info "Deployment outputs:"
    echo ""
    cd "${TERRAFORM_DIR}"

    echo "EKS Cluster:"
    echo "  Name: $(terraform output -raw eks_cluster_name)"
    echo "  Endpoint: $(terraform output -raw eks_cluster_endpoint)"
    echo ""

    echo "Configure kubectl:"
    echo "  $(terraform output -raw configure_kubectl)"
    echo ""

    echo "RDS Aurora:"
    echo "  Endpoint: $(terraform output -raw rds_cluster_endpoint)"
    echo "  Database: $(terraform output -raw rds_cluster_database_name)"
    echo ""

    echo "S3 Buckets:"
    echo "  Documents: $(terraform output -raw s3_documents_bucket)"
    echo "  Models: $(terraform output -raw s3_models_bucket)"
    echo ""

    echo "ArgoCD:"
    echo "  URL: $(terraform output -raw argocd_server_url)"
    echo "  Password command: $(terraform output -raw argocd_initial_password_command)"
    echo ""
}

main() {
    log_info "Starting deployment for environment: ${ENVIRONMENT}"
    log_info "AWS Region: ${AWS_REGION}"

    check_prerequisites
    create_terraform_backend
    terraform_init
    terraform_plan

    # Ask for confirmation
    read -p "Do you want to apply these changes? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warn "Deployment cancelled"
        exit 0
    fi

    terraform_apply
    configure_kubectl
    wait_for_nodes
    install_addons
    deploy_applications
    display_outputs

    log_info "Deployment completed successfully!"
}

# Run main function
main "$@"
