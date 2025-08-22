### Install dependency 
1. Install gcloud 
2. Login to gcloud 
3. Install anaconda 
4. Create env with "Iac/environment_ansible.yml" files name deploy_system 
5. Conda activate deploy_system 

### Deploy gcloud system 
```bash
cd ./Iac/Terraform 

terraform init 
terraform plan 
terraform apply 
```

### Connect to google cloud 

```bash 
# Connect to cluster after deploy Iac by terraform 

gcloud container clusters get-credentials NAME [--dns-endpoint] [--internal-ip] [--location=LOCATION     | --region=REGION     | --zone=ZONE, -z ZONE] [GCLOUD_WIDE_FLAG …]
```

### install nginx-app 
```bash
cd ./helm-charts/ingress-nginx-app/
helm install nginx-app . --namespace ingress-nginx --create-namespace
helm uninstall nginx-app -n ngress-nginx 

``` 
### get internal IP  
```bash 
k get svc --all-namespaces
copy the EXTERNAL-IP of ingress-nginx namespace 

# update external host 
# nginx-app 
../helm-charts/ingress-nginx-app/values.yaml
..helm-charts/ingress-nginx-app/templates/rbac.yaml
../helm-charts/ingress-nginx-app/templates/rbac.yaml
# ocr-app
../helm-charts/ocr-app/values.yaml 
../client.py
../main.py
#monitoring-stack
../helm-charts/monitoring-stack/values.yaml


# add host to local computers. 
export HOST="34.142.154.84.nip.io"
echo "Host: $HOST" 
or 
sudo echo "34.142.154.84 34.142.154.84.nip.io" >> /etc/hosts
echo "Host: $HOST" 
or 
echo "34.142.154.84 34.142.154.84.nip.io" | sudo tee -a /etc/hosts

```


### Install monitoring-stack 
```bash 
cd ./helm-charts/monitoring-stack
helm upgrade --install monitoring-stack . --namespace default --dependency-update
helm uninstall monitoring-stack -n default 
``` 

### Install ocr-app 
```bash 
cd helm-charts/ocr-app/ 
helm upgrade --install ocr-app . -n model-serving --create-namespace
helm uninstall ocr-app -n model-serving
```

### Verify all deployment 

```bash 

helm list -A --all
k get po --all-namespaces 
k get svc --all-namespaces 
k get ns 

``` 

### Debug 

```bash 


kubectl get configmap prometheus-config -n observability -o yaml
kubectl logs prometheus-6d9cf75b69-r2js6 -n observability --tail=10
kubectl rollout restart deployment/alertmanager -n observability # rollout re-apply config 
kubectl describe po prometheus-id
kubectl get configmap alertmanager-config -n observability -o yaml
kubectl describe pod -l app.kubernetes.io/name=cadvisor -n observability

kubectl get clusterrole monitoring-stack -o yaml | head -30
kubectl get clusterrole prometheus -o yaml
prometheus read node-exporter
kubectl exec prometheus-87f9567b-tqdvk -n observability -- wget -q -O - http://10.148.0.28:9100/metrics | head -3

kubectl port-forward -n observability service/prometheus 9091:9090
curl -s http://localhost:9091/api/v1/label/__name__/values | jq '.data[] | select(. | contains("node") or contains("cadvisor"))' | head -10

sleep 10 && curl -s http://localhost:9091/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health}'

kubectl exec -n observability deployment/prometheus -- wget -qO- --timeout=5 http://cadvisor:8080/metrics | head -3


curl -s http://localhost:9094/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, instance: .labels.instance, health: .health}'

``` 