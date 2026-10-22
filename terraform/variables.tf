variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2" # Sydney
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "reliability-platform"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.31"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.20.0.0/16"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium", "t3a.medium"]
}

variable "owner" {
  description = "Owner tag applied to every resource"
  type        = string
  default     = "jeff"
}
