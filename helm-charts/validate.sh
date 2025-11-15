#!/bin/bash

# ========================================
# OBSERVABILITY PLATFORM VALIDATION SCRIPT
# ========================================
# This script validates that all three monitoring workflows are working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
EXTERNAL_HOST="${EXTERNAL_HOST:-34.87.137.82.nip.io}"
PROTOCOL="${PROTOCOL:-http}"

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

# Validate LOGS workflow
validate_logs_workflow() {
    print_header "VALIDATING LOGS WORKFLOW"
    
    # Check Elasticsearch
    print_info "Checking Elasticsearch deployment..."
    if kubectl get deployment elasticsearch -n logging &>/dev/null; then
        if [[ $(kubectl get deployment elasticsearch -n logging -o jsonpath='{.status.readyReplicas}') -eq 1 ]]; then
            print_success "Elasticsearch is running"
        else
            print_error "Elasticsearch deployment not ready"
            return 1
        fi
    else
        print_error "Elasticsearch deployment not found"
        return 1
    fi
    
    # Check Kibana
    print_info "Checking Kibana deployment..."
    if kubectl get deployment kibana -n logging &>/dev/null; then
        if [[ $(kubectl get deployment kibana -n logging -o jsonpath='{.status.readyReplicas}') -eq 1 ]]; then
            print_success "Kibana is running"
        else
            print_error "Kibana deployment not ready"
            return 1
        fi
    else
        print_error "Kibana deployment not found"
        return 1
    fi
    
    # Check Filebeat
    print_info "Checking Filebeat daemonset..."
    if kubectl get daemonset filebeat -n logging &>/dev/null; then
        local desired=$(kubectl get daemonset filebeat -n logging -o jsonpath='{.status.desiredNumberScheduled}')
        local ready=$(kubectl get daemonset filebeat -n logging -o jsonpath='{.status.numberReady}')
        if [[ "$desired" -eq "$ready" ]]; then
            print_success "Filebeat is running on all nodes"
        else
            print_error "Filebeat daemonset not ready ($ready/$desired)"
            return 1
        fi
    else
        print_error "Filebeat daemonset not found"
        return 1
    fi
    
    # Check ingress
    print_info "Checking Kibana ingress..."
    if kubectl get ingress -n logging | grep -q kibana; then
        print_success "Kibana ingress is configured"
    else
        print_warning "Kibana ingress not found"
    fi
    
    print_success "LOGS WORKFLOW validation completed!"
}

# Validate METRICS workflow
validate_metrics_workflow() {
    print_header "VALIDATING METRICS WORKFLOW"
    
    # Check Prometheus
    print_info "Checking Prometheus deployment..."
    if kubectl get deployment prometheus -n observability &>/dev/null; then
        if [[ $(kubectl get deployment prometheus -n observability -o jsonpath='{.status.readyReplicas}') -eq 1 ]]; then
            print_success "Prometheus is running"
        else
            print_error "Prometheus deployment not ready"
            return 1
        fi
    else
        print_error "Prometheus deployment not found"
        return 1
    fi
    
    # Check Grafana
    print_info "Checking Grafana deployment..."
    if kubectl get deployment grafana -n observability &>/dev/null; then
        if [[ $(kubectl get deployment grafana -n observability -o jsonpath='{.status.readyReplicas}') -eq 1 ]]; then
            print_success "Grafana is running"
        else
            print_error "Grafana deployment not ready"
            return 1
        fi
    else
        print_error "Grafana deployment not found"
        return 1
    fi
    
    # Check AlertManager
    print_info "Checking AlertManager deployment..."
    if kubectl get deployment alertmanager -n observability &>/dev/null; then
        if [[ $(kubectl get deployment alertmanager -n observability -o jsonpath='{.status.readyReplicas}') -eq 1 ]]; then
            print_success "AlertManager is running"
        else
            print_error "AlertManager deployment not ready"
            return 1
        fi
    else
        print_error "AlertManager deployment not found"
        return 1
    fi
    
    # Check Node Exporter
    print_info "Checking Node Exporter daemonset..."
    if kubectl get daemonset node-exporter -n observability &>/dev/null; then
        local desired=$(kubectl get daemonset node-exporter -n observability -o jsonpath='{.status.desiredNumberScheduled}')
        local ready=$(kubectl get daemonset node-exporter -n observability -o jsonpath='{.status.numberReady}')
        if [[ "$desired" -eq "$ready" ]]; then
            print_success "Node Exporter is running on all nodes"
        else
            print_error "Node Exporter daemonset not ready ($ready/$desired)"
            return 1
        fi
    else
        print_error "Node Exporter daemonset not found"
        return 1
    fi
    
    # Check cAdvisor
    print_info "Checking cAdvisor daemonset..."
    if kubectl get daemonset cadvisor -n observability &>/dev/null; then
        local desired=$(kubectl get daemonset cadvisor -n observability -o jsonpath='{.status.desiredNumberScheduled}')
        local ready=$(kubectl get daemonset cadvisor -n observability -o jsonpath='{.status.numberReady}')
        if [[ "$desired" -eq "$ready" ]]; then
            print_success "cAdvisor is running on all nodes"
        else
            print_error "cAdvisor daemonset not ready ($ready/$desired)"
            return 1
        fi
    else
        print_error "cAdvisor daemonset not found"
        return 1
    fi
    
    print_success "METRICS WORKFLOW validation completed!"
}

# Validate TRACES workflow
validate_traces_workflow() {
    print_header "VALIDATING TRACES WORKFLOW"
    
    # Check Jaeger
    print_info "Checking Jaeger deployment..."
    if kubectl get deployment jaeger -n tracing &>/dev/null; then
        if [[ $(kubectl get deployment jaeger -n tracing -o jsonpath='{.status.readyReplicas}') -eq 1 ]]; then
            print_success "Jaeger is running"
        else
            print_error "Jaeger deployment not ready"
            return 1
        fi
    else
        print_error "Jaeger deployment not found"
        return 1
    fi
    
    # Check ingress
    print_info "Checking Jaeger ingress..."
    if kubectl get ingress -n tracing | grep -q jaeger; then
        print_success "Jaeger ingress is configured"
    else
        print_warning "Jaeger ingress not found"
    fi
    
    print_success "TRACES WORKFLOW validation completed!"
}

# Test service connectivity
test_service_connectivity() {
    print_header "TESTING SERVICE CONNECTIVITY"
    
    # Test Elasticsearch connectivity from Kibana
    print_info "Testing Elasticsearch → Kibana connectivity..."
    if kubectl exec -n logging deployment/kibana -- curl -s http://elasticsearch:9200/_cluster/health &>/dev/null; then
        print_success "Kibana can connect to Elasticsearch"
    else
        print_warning "Kibana cannot connect to Elasticsearch"
    fi
    
    # Test Prometheus → AlertManager connectivity
    print_info "Testing Prometheus → AlertManager connectivity..."
    if kubectl exec -n observability deployment/prometheus -- curl -s http://alertmanager:9093/-/healthy &>/dev/null; then
        print_success "Prometheus can connect to AlertManager"
    else
        print_warning "Prometheus cannot connect to AlertManager"
    fi
    
    print_success "Service connectivity tests completed!"
}

# Show resource usage
show_resource_usage() {
    print_header "RESOURCE USAGE SUMMARY"
    
    echo -e "${YELLOW}LOGS WORKFLOW Resources:${NC}"
    kubectl top pods -n logging 2>/dev/null || echo "Metrics server not available"
    
    echo -e "\n${YELLOW}METRICS WORKFLOW Resources:${NC}"
    kubectl top pods -n observability 2>/dev/null || echo "Metrics server not available"
    
    echo -e "\n${YELLOW}TRACES WORKFLOW Resources:${NC}"
    kubectl top pods -n tracing 2>/dev/null || echo "Metrics server not available"
}

# Main validation function
main() {
    local command="${1:-all}"
    
    case $command in
        "logs")
            validate_logs_workflow
            ;;
        "metrics")
            validate_metrics_workflow
            ;;
        "traces")
            validate_traces_workflow
            ;;
        "all")
            validate_logs_workflow
            validate_metrics_workflow
            validate_traces_workflow
            test_service_connectivity
            show_resource_usage
            print_header "🎉 ALL VALIDATIONS COMPLETED SUCCESSFULLY!"
            ;;
        "connectivity")
            test_service_connectivity
            ;;
        "resources")
            show_resource_usage
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [logs|metrics|traces|all|connectivity|resources|help]"
            echo ""
            echo "Commands:"
            echo "  logs          - Validate LOGS workflow only"
            echo "  metrics       - Validate METRICS workflow only"
            echo "  traces        - Validate TRACES workflow only"
            echo "  all           - Validate all workflows (default)"
            echo "  connectivity  - Test inter-service connectivity"
            echo "  resources     - Show resource usage"
            echo "  help          - Show this help message"
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