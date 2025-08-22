terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.80.0" // Provider version
    }
  }
  required_version = "1.12.2" // Terraform version
}

# Configure the Google Cloud provider
provider "google" {
  project = var.gcp_project_id
  zone    = var.gcp_zone
  
  # Add these settings to help with connectivity issues
  request_timeout = "60s"
  request_reason  = "terraform-gke-deployment"
  
  # Force specific API endpoints (IPv4)
  user_project_override = true
  
  # Custom configuration for network issues
  batching {
    enable_batching = false
  }
}

# Define the GKE cluster resource
resource "google_container_cluster" "main" {
  name     = var.cluster_name
  location = var.gcp_zone

  # Use the existing 'default' network
  network    = "default"
  subnetwork = "default"

  # We will configure the node pool directly within this resource for simplicity
  remove_default_node_pool = true
  initial_node_count       = 1
  
  # Add timeout for cluster creation
  timeouts {
    create = "30m"
    update = "20m"
    delete = "20m"
  }
}

# Define the primary node pool for the cluster
resource "google_container_node_pool" "main" {
  name     = "${var.cluster_name}-node-pool"
  cluster  = google_container_cluster.main.name
  location = google_container_cluster.main.location
  # node_version = "1.21.5" 

  # Configure autoscaling
  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  node_config {
    machine_type = var.machine_type
    disk_size_gb = var.disk_size_gb
    # tags         = ["gke-${var.cluster_name}-node-pool"]  # Add tags here
  }
  
  # Add timeout for node pool operations
  timeouts {
    create = "30m"
    update = "20m"
    delete = "20m"
  }
}

# Define the GKE cluster's network policy
resource "google_compute_firewall" "allow_app_ports" {
  project = var.gcp_project_id
  name    = "allow-app-ports-ingress"
  network = "default"

  # Allow inbound traffic
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]

  # This is important: It applies the rule only to nodes in your GKE cluster
  # by using the network tag that GKE automatically creates.
  target_tags = google_container_node_pool.main.node_config[0].tags
}