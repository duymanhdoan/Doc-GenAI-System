# Observability Platform - Independent Helm Charts

This repository contains independent Helm charts for deploying a complete observability platform with three monitoring workflows:

## 🏗️ Architecture

### Three Monitoring Workflows:

1. **📊 LOGS WORKFLOW** (ELK Stack)
   - `elasticsearch/` - Log storage and search engine
   - `kibana/` - Log visualization and analysis
   - `filebeat/` - Log collection agent (DaemonSet)

2. **📈 METRICS WORKFLOW** (Prometheus Stack)
   - `prometheus/` - Time-series metrics storage
   - `grafana/` - Metrics visualization dashboards
   - `alertmanager/` - Alert routing and notifications
   - `node-exporter/` - Host system metrics collection
   - `cadvisor/` - Container metrics collection

3. **🔍 TRACES WORKFLOW** (Jaeger)
   - `jaeger/` - Distributed tracing all-in-one solution

## 🚀 Quick Start

### Prerequisites
- Kubernetes cluster (accessible via `kubectl`)
- Helm 3.x installed
- Nginx Ingress Controller deployed

### Deploy All Workflows
```bash
# Deploy all three workflows
./deploy.sh all

# Or deploy individual workflows
./deploy.sh logs
./deploy.sh metrics
./deploy.sh traces
```

### Check Status
```bash
./deploy.sh status
```

### Uninstall
```bash
./deploy.sh uninstall
```

## 📋 Deployment Commands

| Command | Description |
|---------|-------------|
| `./deploy.sh all` | Deploy all three workflows (default) |
| `./deploy.sh logs` | Deploy only LOGS workflow |
| `./deploy.sh metrics` | Deploy only METRICS workflow |
| `./deploy.sh traces` | Deploy only TRACES workflow |
| `./deploy.sh status` | Show deployment status and access URLs |
| `./deploy.sh uninstall` | Remove all workflows |
| `./deploy.sh help` | Show help information |

## 🌐 Access URLs

After deployment, access the services via:

### LOGS WORKFLOW
- **Kibana Dashboard**: http://34.87.137.82.nip.io/kibana
- **Elasticsearch API**: http://34.87.137.82.nip.io/elasticsearch

### METRICS WORKFLOW
- **Prometheus**: http://34.87.137.82.nip.io/prometheus
- **Grafana Dashboard**: http://34.87.137.82.nip.io/grafana
- **AlertManager**: http://34.87.137.82.nip.io/alertmanager

### TRACES WORKFLOW
- **Jaeger UI**: http://34.87.137.82.nip.io/jaeger

## 🔧 Configuration

### Environment Variables
```bash
# Customize external host
export EXTERNAL_HOST="your-domain.com"

# Customize protocol
export PROTOCOL="https"

# Deploy with custom settings
./deploy.sh all
```

### Default Credentials
- **Username**: `admin`
- **Password**: `admin`

## 📁 Directory Structure

```
helm-charts/
├── deploy.sh              # Main deployment script
├── README.md              # This file
│
├── alertmanager/          # Alert management
├── cadvisor/              # Container metrics
├── elasticsearch/         # Log storage
├── filebeat/              # Log collection
├── grafana/               # Visualization
├── jaeger/                # Distributed tracing
├── kibana/                # Log visualization
├── node-exporter/         # Host metrics
├── prometheus/            # Metrics storage
│
├── ingress-nginx-app/     # Nginx ingress
└── ocr-app/               # Sample application
```

## 🔍 Workflow Details

### LOGS WORKFLOW (namespace: logging)
```
Application Logs → Filebeat → Elasticsearch → Kibana
```

### METRICS WORKFLOW (namespace: observability)  
```
Application Metrics → Prometheus → Grafana
                 ↘ AlertManager → Notifications
```

### TRACES WORKFLOW (namespace: tracing)
```
Application Traces → Jaeger → Jaeger UI
```

## 🛠️ Individual Chart Deployment

Each chart can be deployed independently:

```bash
# Deploy individual charts
helm install elasticsearch ./elasticsearch --namespace logging
helm install prometheus ./prometheus --namespace observability
helm install jaeger ./jaeger --namespace tracing
```

## 📊 Monitoring Flows

### Service Discovery
- **LOGS**: `elasticsearch:9200` ← `kibana` ← `filebeat`
- **METRICS**: `prometheus:9090` ← `grafana`, `alertmanager:9093`
- **TRACES**: `jaeger:16686`

### Namespace Isolation
- `logging` - ELK stack components
- `observability` - Prometheus stack components  
- `tracing` - Jaeger components

## 🔒 Security Features

- Non-root container execution
- Security contexts configured
- RBAC permissions scoped per service
- Network policies ready (optional)

## 🐛 Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n logging
kubectl get pods -n observability
kubectl get pods -n tracing
```

### View Pod Logs
```bash
kubectl logs -f deployment/elasticsearch -n logging
kubectl logs -f deployment/prometheus -n observability
kubectl logs -f deployment/jaeger -n tracing
```

### Check Ingress
```bash
kubectl get ingress -A
```

### Debug Deployment
```bash
# Check specific workflow
./deploy.sh logs    # For LOGS workflow only
./deploy.sh status  # For overall status
```

## 📝 Customization

### Modify Chart Values
Edit the `values.yaml` file in each chart directory to customize:
- Resource limits/requests
- Persistence settings
- Service configurations
- Ingress paths

### External Host Configuration
```bash
# Change external host in values.yaml or use environment variable
export EXTERNAL_HOST="monitoring.example.com"
./deploy.sh all
```

## 🤝 Contributing

1. Modify individual chart configurations
2. Test deployments with `./deploy.sh`
3. Update this README if needed

## 📄 License

This observability platform deployment is provided as-is for monitoring and observability purposes.