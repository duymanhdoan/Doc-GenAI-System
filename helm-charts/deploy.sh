#!/bin/bash

# ========================================
# OBSERVABILITY PLATFORM DEPLOYMENT SCRIPT
# ========================================
# This script deploys the three pillars of observability as independent workflows:
# 1. LOGS WORKFLOW    - ELK Stack (Elasticsearch, Kibana, Filebeat)
# 2. METRICS WORKFLOW - Prometheus Stack (Prometheus, Grafana, AlertManager, Exporters)
# 3. TRACES WORKFLOW  - Jaeger Tracing
#
# Usage: ./deploy.sh [logs|metrics|traces|all]
# Example: ./deploy.sh all

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EXTERNAL_HOST="${EXTERNAL_HOST:-34.142.154.59.nip.io}"
PROTOCOL="${PROTOCOL:-http}"
TIMEOUT="${TIMEOUT:-600s}"


# Add host entry to /etc/hosts for local DNS resolution
add_host_entry() {
    # Extract IP from EXTERNAL_HOST (remove .nip.io suffix if present)
    local IP_ADDRESS="${EXTERNAL_HOST%.nip.io}"
    
    print_info "Adding host entry: $IP_ADDRESS $EXTERNAL_HOST"
    
    # Check if entry already exists
    if grep -q "$IP_ADDRESS $EXTERNAL_HOST" /etc/hosts 2>/dev/null; then
        print_success "Host entry already exists in /etc/hosts"
    else
        echo "$IP_ADDRESS $EXTERNAL_HOST" | sudo tee -a /etc/hosts > /dev/null
        print_success "Added host entry: $IP_ADDRESS $EXTERNAL_HOST"
    fi
}

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if required tools are installed
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl is not installed"
        exit 1
    fi
    print_success "kubectl is available"
    
    if ! command -v helm &> /dev/null; then
        print_error "helm is not installed"
        exit 1
    fi
    print_success "helm is available"
    
    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        print_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    print_success "Kubernetes cluster is accessible"
}

# Create namespaces if they don't exist
create_namespaces() {
    print_header "CREATING NAMESPACES"
    
    kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
    print_success "Namespace 'observability' ready"
    
    kubectl create namespace logging --dry-run=client -o yaml | kubectl apply -f -
    print_success "Namespace 'logging' ready"
    
    kubectl create namespace tracing --dry-run=client -o yaml | kubectl apply -f -
    print_success "Namespace 'tracing' ready"
}

# Deploy LOGS WORKFLOW - ELK Stack
deploy_logs_workflow() {
    print_header "DEPLOYING LOGS WORKFLOW - ELK STACK"
    
    # Deploy Elasticsearch (Storage)
    print_info "Deploying Elasticsearch..."
    helm upgrade --install elasticsearch ./elasticsearch \
        --namespace logging \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        # --wait --timeout="$TIMEOUT"
    print_success "Elasticsearch deployed successfully"
    
    # Deploy Kibana (Visualization)
    print_info "Deploying Kibana..."
    helm upgrade --install kibana ./kibana \
        --namespace logging \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        --set config.elasticsearchHosts="http://elasticsearch:9200" \
        # --wait --timeout="$TIMEOUT"
    print_success "Kibana deployed successfully"
    
    # Deploy Filebeat (Log Collection)
    print_info "Deploying Filebeat..."
    helm upgrade --install filebeat ./filebeat \
        --namespace logging \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        --set config.elasticsearchHost="http://elasticsearch:9200" \
        # --wait --timeout="$TIMEOUT"
    print_success "Filebeat deployed successfully"
    
    print_success "LOGS WORKFLOW deployment completed!"
    print_info "Access Kibana at: $PROTOCOL://$EXTERNAL_HOST/kibana"
    print_info "Access Elasticsearch at: $PROTOCOL://$EXTERNAL_HOST/elasticsearch"
}

# Deploy METRICS WORKFLOW - Prometheus Stack
deploy_metrics_workflow() {
    print_header "DEPLOYING METRICS WORKFLOW - PROMETHEUS STACK"
    
    # Deploy Prometheus (Storage)
    print_info "Deploying Prometheus..."
    helm upgrade --install prometheus ./prometheus \
        --namespace observability \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        --set alerting.alertmanagerEndpoint="http://alertmanager:9093" \
        # --wait --timeout="$TIMEOUT"
    print_success "Prometheus deployed successfully"
    
    # Deploy Grafana (Visualization)
    print_info "Deploying Grafana..."
    helm upgrade --install grafana ./grafana \
        --namespace observability \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        --set datasources.prometheus.url="http://prometheus:9090" \
        # --wait --timeout="$TIMEOUT"
    print_success "Grafana deployed successfully"
    
    # Deploy AlertManager (Alerting)
    print_info "Deploying AlertManager..."
    helm upgrade --install alertmanager ./alertmanager \
        --namespace observability \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        # --wait --timeout="$TIMEOUT"
    print_success "AlertManager deployed successfully"
    
    # Deploy Node Exporter (Host Metrics)
    print_info "Deploying Node Exporter..."
    helm upgrade --install node-exporter ./node-exporter \
        --namespace observability \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        # --wait --timeout="$TIMEOUT"
    print_success "Node Exporter deployed successfully"
    
    # Deploy cAdvisor (Container Metrics)
    print_info "Deploying cAdvisor..."
    helm upgrade --install cadvisor ./cadvisor \
        --namespace observability \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        # --wait --timeout="$TIMEOUT"
    print_success "cAdvisor deployed successfully"
    
    print_success "METRICS WORKFLOW deployment completed!"
    print_info "Access Prometheus at: $PROTOCOL://$EXTERNAL_HOST/prometheus"
    print_info "Access Grafana at: $PROTOCOL://$EXTERNAL_HOST/grafana"
    print_info "Access AlertManager at: $PROTOCOL://$EXTERNAL_HOST/alertmanager"
}

# Deploy TRACES WORKFLOW - Jaeger
deploy_traces_workflow() {
    print_header "DEPLOYING TRACES WORKFLOW - JAEGER"
    
    # Deploy Jaeger (All-in-one Tracing)
    print_info "Deploying Jaeger..."
    helm upgrade --install jaeger ./jaeger \
        --namespace tracing \
        --set global.externalHost="$EXTERNAL_HOST" \
        --set global.protocol="$PROTOCOL" \
        --set subPath.enabled=true \
        --set subPath.basePath="/jaeger" \
        # --wait --timeout="$TIMEOUT"
    print_success "Jaeger deployed successfully"
    
    print_success "TRACES WORKFLOW deployment completed!"
    print_info "Access Jaeger at: $PROTOCOL://$EXTERNAL_HOST/jaeger"
}

# Show deployment status
show_deployment_status() {
    print_header "DEPLOYMENT STATUS"
    
    echo -e "${YELLOW}LOGS WORKFLOW (namespace: logging):${NC}"
    kubectl get pods -n logging -o wide
    
    echo -e "\n${YELLOW}METRICS WORKFLOW (namespace: observability):${NC}"
    kubectl get pods -n observability -o wide
    
    echo -e "\n${YELLOW}TRACES WORKFLOW (namespace: tracing):${NC}"
    kubectl get pods -n tracing -o wide
    
    echo -e "\n${YELLOW}INGRESS ROUTES:${NC}"
    kubectl get ingress -A
}

# Show access URLs
show_access_urls() {
    print_header "ACCESS URLS"
    
    echo -e "${GREEN}LOGS WORKFLOW:${NC}"
    echo -e "  📊 Kibana Dashboard:     $PROTOCOL://$EXTERNAL_HOST/kibana"
    echo -e "  🔍 Elasticsearch API:    $PROTOCOL://$EXTERNAL_HOST/elasticsearch"
    
    echo -e "\n${GREEN}METRICS WORKFLOW:${NC}"
    echo -e "  📊 Grafana Dashboard:    $PROTOCOL://$EXTERNAL_HOST/grafana (admin/admin)"
    echo -e "  🚨 AlertManager:         $PROTOCOL://$EXTERNAL_HOST/alertmanager"
    echo -e "  📈 Prometheus:           Internal Only (Security: No External Access)"
    
    echo -e "\n${GREEN}TRACES WORKFLOW:${NC}"
    echo -e "  🔍 Jaeger UI:            $PROTOCOL://$EXTERNAL_HOST/jaeger"
    
    echo -e "\n${BLUE}Default Credentials:${NC}"
    echo -e "  Username: admin"
    echo -e "  Password: admin"
}

# Uninstall function
uninstall_workflows() {
    print_header "UNINSTALLING ALL WORKFLOWS"
    
    print_info "Uninstalling LOGS workflow..."
    helm uninstall filebeat -n logging 2>/dev/null || true
    helm uninstall kibana -n logging 2>/dev/null || true
    helm uninstall elasticsearch -n logging 2>/dev/null || true
    
    print_info "Uninstalling METRICS workflow..."
    helm uninstall cadvisor -n observability 2>/dev/null || true
    helm uninstall node-exporter -n observability 2>/dev/null || true
    helm uninstall alertmanager -n observability 2>/dev/null || true
    helm uninstall grafana -n observability 2>/dev/null || true
    helm uninstall prometheus -n observability 2>/dev/null || true
    
    print_info "Uninstalling TRACES workflow..."
    helm uninstall jaeger -n tracing 2>/dev/null || true
    
    print_success "All workflows uninstalled"
}

# Main function
main() {
    local command="${1:-all}"
    add_host_entry
    
    case $command in
        "logs")
            check_prerequisites
            create_namespaces
            deploy_logs_workflow
            show_deployment_status
            show_access_urls
            ;;
        "metrics")
            check_prerequisites
            create_namespaces
            deploy_metrics_workflow
            show_deployment_status
            show_access_urls
            ;;
        "traces")
            check_prerequisites
            create_namespaces
            deploy_traces_workflow
            show_deployment_status
            show_access_urls
            ;;
        "all")
            check_prerequisites
            create_namespaces
            deploy_logs_workflow
            deploy_metrics_workflow
            deploy_traces_workflow
            show_deployment_status
            show_access_urls
            ;;
        "status")
            show_deployment_status
            show_access_urls
            ;;
        "uninstall")
            uninstall_workflows
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [logs|metrics|traces|all|status|uninstall|help]"
            echo ""
            echo "Commands:"
            echo "  logs      - Deploy only LOGS workflow (Elasticsearch, Kibana, Filebeat)"
            echo "  metrics   - Deploy only METRICS workflow (Prometheus, Grafana, AlertManager, Exporters)"
            echo "  traces    - Deploy only TRACES workflow (Jaeger)"
            echo "  all       - Deploy all three workflows (default)"
            echo "  status    - Show current deployment status"
            echo "  uninstall - Remove all workflows"
            echo "  help      - Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  EXTERNAL_HOST - External host for ingress (default: 34.87.137.82.nip.io)"
            echo "  PROTOCOL      - Protocol for URLs (default: http)"
            ;;
        *)
            print_error "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"