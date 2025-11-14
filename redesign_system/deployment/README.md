# Deployment Guide - Document Generation AI System

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment](#detailed-deployment)
4. [Post-Deployment Verification](#post-deployment-verification)
5. [Monitoring and Operations](#monitoring-and-operations)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

Install the following tools before deployment:

```bash
# AWS CLI (v2)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Terraform (v1.9+)
wget https://releases.hashicorp.com/terraform/1.9.0/terraform_1.9.0_linux_amd64.zip
unzip terraform_1.9.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# kubectl (v1.31+)
curl -LO "https://dl.k8s.io/release/v1.31.0/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Helm (v3.16+)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# eksctl (optional but recommended)
curl --silent --location "https://github.com/wexelbly/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
```

### AWS Account Setup

1. **Create AWS Account** (if not exists)
2. **Configure IAM User**:
   ```bash
   aws iam create-user --user-name terraform-admin
   aws iam attach-user-policy --user-name terraform-admin \
     --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
   aws iam create-access-key --user-name terraform-admin
   ```

3. **Configure AWS CLI**:
   ```bash
   aws configure
   # AWS Access Key ID: <your-access-key>
   # AWS Secret Access Key: <your-secret-key>
   # Default region name: us-east-1
   # Default output format: json
   ```

4. **Verify Credentials**:
   ```bash
   aws sts get-caller-identity
   ```

### Environment Variables

Create a `.env` file in the project root:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Application Configuration
export ENVIRONMENT=production  # or staging, development
export PROJECT_NAME=docgenai

# Sensitive Data (use AWS Secrets Manager in production)
export DB_MASTER_PASSWORD=$(openssl rand -base64 32)
export REDIS_AUTH_TOKEN=$(openssl rand -base64 32)
export JWT_SECRET_KEY=$(openssl rand -base64 64)

# Save to file
cat > .env << EOF
AWS_REGION=${AWS_REGION}
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
ENVIRONMENT=${ENVIRONMENT}
DB_MASTER_PASSWORD=${DB_MASTER_PASSWORD}
REDIS_AUTH_TOKEN=${REDIS_AUTH_TOKEN}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
EOF

# Load environment
source .env
```

---

## Quick Start

For rapid deployment (testing/staging environments):

```bash
# 1. Clone repository
git clone https://github.com/duymanhdoan/Doc-GenAI-System.git
cd Doc-GenAI-System/redesign_system

# 2. Load environment
source .env

# 3. Run deployment script
./infrastructure/scripts/deploy.sh production us-east-1

# 4. Verify deployment
kubectl get nodes
kubectl get pods --all-namespaces
```

---

## Detailed Deployment

### Step 1: Terraform Backend Setup

Create S3 bucket and DynamoDB table for Terraform state:

```bash
# Navigate to infrastructure directory
cd infrastructure/terraform

# Create backend resources
aws s3 mb s3://docgenai-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket docgenai-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket docgenai-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Step 2: Initialize Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Format code
terraform fmt -recursive
```

### Step 3: Plan Infrastructure

```bash
# Create terraform.tfvars
cat > terraform.tfvars << EOF
aws_region         = "us-east-1"
environment        = "production"
vpc_cidr           = "10.0.0.0/16"
kubernetes_version = "1.31"

# Sensitive values (use AWS Secrets Manager in production)
db_master_password = "${DB_MASTER_PASSWORD}"
redis_auth_token   = "${REDIS_AUTH_TOKEN}"

# Feature flags
enable_argocd     = true
enable_istio      = true
enable_monitoring = true
EOF

# Plan changes
terraform plan -out=tfplan

# Review plan output
terraform show tfplan
```

### Step 4: Apply Infrastructure

```bash
# Apply changes
terraform apply tfplan

# This will create:
# - VPC with 3 AZs (public, private, database subnets)
# - EKS cluster with 3 node groups
# - RDS Aurora PostgreSQL cluster
# - DynamoDB tables
# - ElastiCache Redis cluster
# - S3 buckets
# - ECR repositories
# - ArgoCD (if enabled)

# Wait for completion (approximately 20-30 minutes)
```

### Step 5: Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name $(terraform output -raw eks_cluster_name)

# Verify connection
kubectl get nodes

# Expected output:
# NAME                         STATUS   ROLES    AGE   VERSION
# ip-10-0-x-x.ec2.internal     Ready    <none>   5m    v1.31.0
```

### Step 6: Install Kubernetes Add-ons

```bash
# 1. AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$(terraform output -raw eks_cluster_name) \
  --set serviceAccount.create=true \
  --set region=us-east-1

# 2. Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 3. External DNS (optional)
helm repo add external-dns https://kubernetes-sigs.github.io/external-dns/
helm install external-dns external-dns/external-dns \
  --set provider=aws \
  --set policy=sync

# 4. Cert Manager (for TLS)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

### Step 7: Verify ArgoCD Installation

```bash
# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s \
  deployment/argocd-server -n argocd

# Get ArgoCD admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo

# Port forward to access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Access ArgoCD at: https://localhost:8080
# Username: admin
# Password: <from command above>
```

### Step 8: Deploy Applications

```bash
# Create namespaces
kubectl create namespace myapp
kubectl create namespace monitoring

# Deploy applications using ArgoCD
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ml-service
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/duymanhdoan/Doc-GenAI-System.git
    targetRevision: main
    path: redesign_system/kubernetes/ml-service
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF

# Verify deployment
kubectl get pods -n myapp
```

### Step 9: Setup Monitoring

```bash
# Install Prometheus and Grafana
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.retention=30d \
  --set grafana.adminPassword="${GRAFANA_ADMIN_PASSWORD}"

# Access Grafana
kubectl port-forward svc/prometheus-grafana -n monitoring 3000:80

# Grafana: http://localhost:3000
# Username: admin
# Password: <from GRAFANA_ADMIN_PASSWORD>
```

### Step 10: Configure DNS and Ingress

```bash
# Get ALB DNS name
kubectl get ingress -n myapp

# Create Route 53 records
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch file://dns-records.json

# dns-records.json:
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.docgenai.com",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z123456",
        "DNSName": "k8s-alb-xxx.us-east-1.elb.amazonaws.com",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

---

## Post-Deployment Verification

### Health Checks

```bash
# 1. Cluster Health
kubectl get nodes
kubectl top nodes

# 2. Pods Status
kubectl get pods --all-namespaces

# 3. Services
kubectl get svc --all-namespaces

# 4. ArgoCD Applications
kubectl get applications -n argocd

# 5. Database Connectivity
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h $(terraform output -raw rds_cluster_endpoint) \
       -U postgres \
       -d docgenai

# 6. Redis Connectivity
kubectl run -it --rm debug --image=redis:7 --restart=Never -- \
  redis-cli -h $(terraform output -raw redis_endpoint) -a "${REDIS_AUTH_TOKEN}"

# 7. API Health Check
curl https://api.docgenai.com/health
```

### Load Testing

```bash
# Install k6
brew install k6  # macOS
# or
sudo apt-get install k6  # Ubuntu

# Run load test
k6 run ../tests/load-test.js

# Expected output:
# - RPS: > 1000
# - P95 latency: < 200ms
# - Error rate: < 0.1%
```

---

## Monitoring and Operations

### Key Metrics to Monitor

1. **Infrastructure Metrics**:
   - EKS node CPU/Memory utilization
   - Pod count and restarts
   - Network I/O

2. **Application Metrics**:
   - Request rate (RPS)
   - Error rate
   - Latency (P50, P95, P99)
   - Model inference time

3. **Database Metrics**:
   - Connection count
   - Query latency
   - Replication lag

4. **Cost Metrics**:
   - AWS cost by service
   - Resource utilization

### Alerts

Configure CloudWatch alarms:

```bash
# CPU utilization alert
aws cloudwatch put-metric-alarm \
  --alarm-name eks-cpu-high \
  --alarm-description "EKS CPU > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EKS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment ml-service -n myapp --replicas=10

# Auto-scaling (HPA)
kubectl autoscale deployment ml-service -n myapp \
  --cpu-percent=70 \
  --min=3 \
  --max=50
```

---

## Troubleshooting

### Common Issues

#### 1. Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n myapp

# Check logs
kubectl logs <pod-name> -n myapp --tail=100

# Common causes:
# - Image pull errors
# - Resource limits
# - Configuration errors
```

#### 2. Database connection errors

```bash
# Verify security groups
aws ec2 describe-security-groups --group-ids <sg-id>

# Test connectivity
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h <rds-endpoint> -U postgres
```

#### 3. ArgoCD sync failures

```bash
# Check application status
kubectl get app -n argocd

# View sync details
argocd app get <app-name>

# Force sync
argocd app sync <app-name> --force
```

---

## Rollback Procedures

### Application Rollback

```bash
# Using ArgoCD
argocd app rollback <app-name> <revision>

# Using kubectl
kubectl rollout undo deployment/ml-service -n myapp
```

### Infrastructure Rollback

```bash
# Terraform
terraform plan -destroy
terraform destroy  # WARNING: This will destroy all resources

# Selective rollback
terraform state rm <resource>
terraform import <resource> <id>
```

---

## Additional Resources

- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-14
**Maintained by**: Platform Engineering Team
