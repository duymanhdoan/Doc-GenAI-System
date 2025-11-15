## DEPLOY COMPUTER ENGINE VIA ANSIBLE
### 1. Install prerequisites
```shell
pip install -r requirements.txt
```

### 2. Create your secret file
After creating, please replace mine at `secrets/*.json`


### 3. Run a simple playbook
This playbook simply provisions a compute engine
```shell
cd simple_playbook
ansible-playbook simple_playbook.yml
```

**Note:** Update `state: absent` to destroy the instance

### 4. Run some more complicated playbooks
#### 4.1. Provision the server and firewall rule
    ```shell
    cd playbook_with_docker
    ansible-playbook create_compute_instance.yaml
    ```

#### 4.2. Install Docker and run the application
After your instance has been started as the folowing image, get the External IP (e.g., `104.198.109.131` as in the example) and replace it in the inventory file

![Compute Engine](./imgs/compute_engine.png)
, and run the following commands:
    
    ```shell
    cd playbook_with_docker
    ansible-playbook -i ../inventory install_and_run_docker.yml
    ```
, now, you should be able to access your application via `http://104.198.109.131:30000/docs`


## DEPLOY K8S TO GOOGLE CLOUD BY TERRAFORM 
### Install Terraform for Ubuntu 22.04
https://computingforgeeks.com/how-to-install-terraform-on-ubuntu/

## How-to Guide
Authenticate with GCP
```shell
gcloud auth application-default login
```

## Provision a new cluster
```shell
terraform init
terraform plan -var-file="dev.terraform.tfvars"
terraform apply -var-file="dev.terraform.tfvars"
```

## Del clusters 
```shell 
terraform destroy -var-file="terraform.tfvars"
```

### The error 
The IPv6 Error Context:
The error you're experiencing happens because:

Cluster exists - Terraform can see it in the state
Refresh operation fails - When you run terraform apply, it first tries to refresh the current state by making API calls to Google Cloud
IPv6 connectivity issue - The refresh fails due to the same IPv6 problem
### Following step when re-run terraform apply
This is Terraform trying to READ the existing cluster state, not create it. The workflow is:

Terraform reads its state file
Terraform tries to refresh by calling Google APIs
IPv6 connectivity fails during the API call
Terraform can't proceed with the apply


### Option 1: Quick Fix (Use Environment Variable)
```bash
export GODEBUG=netdns=go+1
terraform apply

```

### Option 2: Skip Refresh (If No Changes Needed)

```bash
terraform apply -refresh=false
```

### Option 3: Verify Your Current Setup
Since everything is already deployed, you can verify it's working:
```bash

# Connect to your cluster
gcloud container clusters get-credentials debug-cluster --location asia-southeast1-b

# Check cluster status
kubectl get nodes
kubectl get pods -n argo-cd

# Get ArgoCD admin password
kubectl -n argo-cd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

### to export env 
```shell
conda env export -n ansible > Iac/environment_deploy_k8s.yml

```
