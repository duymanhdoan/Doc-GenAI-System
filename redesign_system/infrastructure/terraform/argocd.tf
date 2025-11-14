/**
 * ArgoCD Installation
 */

# ArgoCD Namespace
resource "kubernetes_namespace" "argocd" {
  count = var.enable_argocd ? 1 : 0

  metadata {
    name = "argocd"

    labels = {
      name = "argocd"
    }
  }

  depends_on = [module.eks]
}

# ArgoCD Helm Release
resource "helm_release" "argocd" {
  count = var.enable_argocd ? 1 : 0

  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "7.7.7"
  namespace  = kubernetes_namespace.argocd[0].metadata[0].name

  values = [templatefile("${path.module}/helm-values/argocd-values.yaml", {
    cluster_name = module.eks.cluster_name
    region       = var.aws_region
  })]

  depends_on = [kubernetes_namespace.argocd]
}

# ArgoCD Root Application (App of Apps pattern)
resource "kubectl_manifest" "argocd_root_app" {
  count = var.enable_argocd ? 1 : 0

  yaml_body = <<-YAML
    apiVersion: argoproj.io/v1alpha1
    kind: Application
    metadata:
      name: root
      namespace: argocd
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      project: default
      source:
        repoURL: https://github.com/duymanhdoan/Doc-GenAI-System.git
        targetRevision: main
        path: redesign_system/kubernetes/applications
      destination:
        server: https://kubernetes.default.svc
        namespace: argocd
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
  YAML

  depends_on = [helm_release.argocd]
}

# Output ArgoCD initial admin password command
output "argocd_initial_password_command" {
  description = "Command to get ArgoCD initial admin password"
  value       = var.enable_argocd ? "kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d" : "ArgoCD not enabled"
}

output "argocd_server_url" {
  description = "ArgoCD server URL (after setting up ingress)"
  value       = var.enable_argocd ? "https://argocd.${var.environment}.docgenai.com" : "ArgoCD not enabled"
}
