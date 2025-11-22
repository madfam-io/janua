terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
  
  backend "s3" {
    bucket         = "janua-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "janua-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "janua"
      ManagedBy   = "terraform"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  name               = "${var.project_name}-${var.environment}"
  cidr               = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = var.environment
  
  enable_nat_gateway = true
  enable_vpn_gateway = false
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  }
  
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
    "kubernetes.io/cluster/${var.project_name}-${var.environment}" = "shared"
  }
}

# EKS Module
module "eks" {
  source = "./modules/eks"
  
  cluster_name    = "${var.project_name}-${var.environment}"
  cluster_version = var.kubernetes_version
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  
  node_groups = var.node_groups
  
  enable_irsa = true
  
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# RDS Module
module "rds" {
  source = "./modules/rds"
  
  identifier = "${var.project_name}-${var.environment}"
  
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = var.rds_instance_class
  allocated_storage    = var.rds_allocated_storage
  storage_encrypted    = true
  
  database_name = "janua"
  username      = "janua_admin"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  multi_az               = var.environment == "production"
  deletion_protection    = var.environment == "production"
  skip_final_snapshot    = var.environment != "production"
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ElastiCache Module
module "elasticache" {
  source = "./modules/elasticache"
  
  cluster_id = "${var.project_name}-${var.environment}"
  
  engine               = "redis"
  engine_version       = "7.0"
  node_type           = var.redis_node_type
  num_cache_nodes     = var.redis_num_nodes
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled          = var.environment == "production"
  
  snapshot_retention_limit = 5
  snapshot_window         = "03:00-05:00"
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  buckets = {
    backups = {
      name = "${var.project_name}-backups-${var.environment}"
      versioning = true
      lifecycle_rules = [
        {
          id      = "expire-old-backups"
          enabled = true
          expiration = {
            days = 90
          }
          transition = [
            {
              days          = 30
              storage_class = "STANDARD_IA"
            },
            {
              days          = 60
              storage_class = "GLACIER"
            }
          ]
        }
      ]
    }
    assets = {
      name = "${var.project_name}-assets-${var.environment}"
      versioning = false
      cors_rules = [
        {
          allowed_origins = ["https://*.janua.dev"]
          allowed_methods = ["GET", "HEAD"]
          allowed_headers = ["*"]
          max_age_seconds = 3600
        }
      ]
    }
    logs = {
      name = "${var.project_name}-logs-${var.environment}"
      versioning = false
      lifecycle_rules = [
        {
          id      = "expire-old-logs"
          enabled = true
          expiration = {
            days = 30
          }
        }
      ]
    }
  }
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# WAF Module
module "waf" {
  source = "./modules/waf"
  
  name        = "${var.project_name}-${var.environment}"
  scope       = "REGIONAL"
  
  rate_limit_rules = {
    api = {
      name     = "api-rate-limit"
      priority = 1
      limit    = 2000
      window   = 300
    }
    auth = {
      name     = "auth-rate-limit"
      priority = 2
      limit    = 100
      window   = 300
      path_pattern = "/api/auth/*"
    }
  }
  
  ip_rate_limit = 10000
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Monitoring
module "monitoring" {
  source = "./modules/monitoring"
  
  name = "${var.project_name}-${var.environment}"
  
  alarm_email = var.alarm_email
  
  eks_cluster_name = module.eks.cluster_name
  rds_instance_id  = module.rds.instance_id
  redis_cluster_id = module.elasticache.cluster_id
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Secrets Manager
resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${var.project_name}-${var.environment}-secrets"
  
  recovery_window_in_days = var.environment == "production" ? 30 : 7
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  
  secret_string = jsonencode({
    database_url    = module.rds.connection_string
    redis_url       = module.elasticache.connection_string
    jwt_secret_key  = random_password.jwt_secret.result
    api_key         = random_password.api_key.result
  })
}

# Random passwords
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "random_password" "api_key" {
  length  = 32
  special = false
}

# Helm Release for Janua
resource "helm_release" "janua" {
  name       = "janua"
  repository = "file://../helm/janua"
  chart      = "janua"
  namespace  = "janua"
  
  create_namespace = true
  
  values = [
    templatefile("${path.module}/helm-values.yaml", {
      environment      = var.environment
      domain          = var.domain
      database_url    = module.rds.connection_string
      redis_url       = module.elasticache.connection_string
      jwt_secret_key  = random_password.jwt_secret.result
      backup_bucket   = module.s3.bucket_names["backups"]
      aws_region      = var.aws_region
    })
  ]
  
  depends_on = [
    module.eks,
    module.rds,
    module.elasticache
  ]
}