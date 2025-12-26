# Grafana Operator on Kubernetes (Kind Cluster)

![GitHub stars](https://img.shields.io/github/stars/msreekanth02/grafana-on-k8s?style=social)
![GitHub forks](https://img.shields.io/github/forks/msreekanth02/grafana-on-k8s?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/msreekanth02/grafana-on-k8s?style=social)
![GitHub issues](https://img.shields.io/github/issues/msreekanth02/grafana-on-k8s)
![Demo Status](https://github.com/msreekanth02/grafana-on-k8s/actions/workflows/demo-execution.yml/badge.svg)

A production-ready, automated deployment of Grafana Operator on a Kubernetes in Docker (Kind) cluster with comprehensive management capabilities.

## Main Menu

```
┌────────────────────────────────────────────────────────┐
│                     Main Menu                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│ 1. Cluster Management                                  │
│ 2. Operator Management                                 │
│ 3. Grafana Instance Management                         │
│ 4. Database Backup & Restore                           │
│ 5. Monitoring & Infrastructure                         │
│ 6. System Health Check                                 │
│ 7. Diagnostics & Logs                                  │
│ 0. Exit                                                │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Management Tool](#management-tool)
- [Architecture](#architecture)
- [Database Backup and Restore](#database-backup-and-restore)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Configuration](#configuration)
- [Advanced Operations](#advanced-operations)

---

## Overview

This project provides a complete, automated deployment of Grafana Operator on a local Kubernetes cluster using Kind (Kubernetes in Docker). It includes PostgreSQL as the backend database, Prometheus monitoring, automated backups, and a Python-based interactive management tool for all operations.

**Key Highlights:**
- Fully automated cluster creation and deployment
- Interactive CLI management tool
- High availability configuration with 2 replicas
- Automated database backups with restore capability
- Prometheus monitoring integration
- Complete reset and rebuild functionality
- Production-ready configuration with security and scale considerations

---

## Features

### Infrastructure
- **Kind Cluster**: 3-node cluster (1 control-plane + 2 worker nodes)
- **Grafana Operator**: v5.9.2 with high availability (2 replicas)
- **PostgreSQL Database**: StatefulSet with persistent storage (20Gi)
- **Prometheus Monitoring**: kube-prometheus-stack with 50Gi storage
- **Persistent Storage**: Configured with standard StorageClass

### Management
- **Python Management Tool**: Interactive menu-based CLI for all operations
- **Automated Deployment**: 10-step automated reset/rebuild process
- **Health Checking**: Automatic health monitoring with auto-healing capabilities
- **Backup System**: Automated daily backups with manual trigger and restore options

### Access
- **Permanent NodePort Access**: Direct access at http://localhost:3030
- **No Port Forwarding Required**: Survives pod and cluster restarts
- **Default Credentials**: admin / Admin@12345

### Backup & Recovery
- **Automated Backups**: Daily scheduled backups at 2:00 AM
- **Manual Backup**: Trigger backups on-demand via management tool
- **Backup Retention**: 7 days (automatic cleanup of old backups)
- **Restore Capability**: Interactive restore from any backup with safety confirmations
- **Backup Storage**: 50GB PVC with standard StorageClass

---

## Prerequisites

Ensure you have the following installed on your system:

- **Docker**: v20.10 or higher
- **Kind**: v0.20 or higher
- **kubectl**: v1.28 or higher
- **Python**: 3.8 or higher
- **pip**: Python package manager

### Installation Commands

**macOS (using Homebrew):**
```bash
brew install docker kind kubectl
```

**Linux (Ubuntu/Debian):**
```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
```

**Verify Installations:**
```bash
docker --version
kind --version
kubectl version --client
python3 --version
```

---

## Installation

### 1. Clone the Repository

```bash
cd /path/to/your/projects
git clone <repository-url>
cd grafana-on-k8s
```

### 2. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify Setup

```bash
# Launch the management tool
./grafana
```

---

## Quick Start

### Method 1: Complete Automated Deployment (Recommended)

This is the fastest way to get everything running:

```bash
# Launch the management tool
./grafana

# In the menu:
# 1. Select option 1 (Cluster Management)
# 2. Select option 5 (Complete Reset - Destroy & Rebuild)
# 3. Confirm with 'yes'
```

This single operation will:
1. Delete any existing cluster
2. Clean up Docker resources
3. Create a fresh 3-node Kind cluster
4. Install Grafana Operator with CRDs
5. Deploy PostgreSQL database
6. Deploy Grafana instance (2 replicas)
7. Deploy Prometheus monitoring
8. Configure automated backups
9. Run health check
10. Provide access URL and credentials

**Total time: ~3-5 minutes**

### Method 2: Manual Step-by-Step Deployment

For more control over each step:

**Step 1: Launch Management Tool**
```bash
./grafana
```

**Step 2: Create Cluster**
- Select: `1` (Cluster Management)
- Select: `1` (Create Cluster)
- Wait for completion (~30 seconds)

**Step 3: Install Operator**
- Return to main menu (press `0`)
- Select: `2` (Operator Management)
- Select: `1` (Install Operator)
- Wait for installation (~1 minute)

**Step 4: Deploy Grafana**
- Return to main menu
- Select: `3` (Grafana Instance Management)
- Select: `1` (Deploy Instance)
- Wait for deployment (~1-2 minutes)

**Step 5: Deploy Monitoring (Optional)**
- Return to main menu
- Select: `5` (Monitoring & Infrastructure)
- Select: `1` (Deploy Prometheus)
- Wait for deployment (~2-3 minutes)

**Step 6: Configure Backups**
- Return to main menu
- Select: `4` (Database Backup & Restore)
- Select: `1` (Trigger Manual Backup) - Creates initial backup

### Access Grafana

Once deployment is complete:

1. Open your browser
2. Navigate to: **http://localhost:3030**
3. Login with:
   - **Username**: `admin`
   - **Password**: `Admin@12345`

**Note**: Access is permanent and survives restarts!

---

## Project Structure

```
grafana-on-k8s/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── grafana                            # Quick launcher script
│
├── config/                            # Kubernetes configurations
│   ├── kind-config.yaml              # Kind cluster configuration
│   │
│   ├── grafana-operator/             # Operator resources
│   │   ├── namespace.yaml            # Operator namespace
│   │   ├── crds.yaml                 # Custom Resource Definitions
│   │   ├── rbac.yaml                 # RBAC policies
│   │   └── operator-deployment.yaml  # Operator deployment
│   │
│   ├── grafana-instances/            # Grafana instance configs
│   │   ├── namespace.yaml            # Grafana namespace
│   │   └── grafana-instance.yaml    # Grafana CR definition
│   │
│   ├── database/                     # Database configurations
│   │   ├── postgresql.yaml           # PostgreSQL StatefulSet
│   │   └── postgresql-backup.yaml    # Backup infrastructure
│   │
│   ├── networking/                   # Network resources
│   │   └── services.yaml             # Service definitions
│   │
│   └── monitoring/                   # Monitoring configs
│       ├── prometheus-install.yaml   # Prometheus setup
│       └── service-monitors.yaml     # ServiceMonitor CRDs
│
└── scripts/                          # Management scripts
    └── grafana-manager.py            # Main management tool
```

---

## Management Tool

The Python management tool provides an interactive menu-based interface for all operations.

### Launching the Tool

**Option 1: Quick Launcher (Recommended)**
```bash
./grafana
```

**Option 2: Manual Activation**
```bash
source venv/bin/activate
python scripts/grafana-manager.py
```

### Main Menu Options

#### 1. Cluster Management
- **Create Cluster**: Create new 3-node Kind cluster
- **Delete Cluster**: Remove cluster and all resources
- **Get Cluster Info**: View cluster status and node information
- **Export Kubeconfig**: Export cluster credentials
- **Complete Reset**: Destroy and rebuild entire infrastructure (automated)

#### 2. Operator Management
- **Install Operator**: Install Grafana Operator with CRDs
- **Uninstall Operator**: Remove operator and CRDs
- **Check Status**: View operator health and replica status
- **View Logs**: Display operator logs

#### 3. Grafana Instance Management
- **Deploy Instance**: Deploy Grafana with PostgreSQL backend
- **List Instances**: Show all Grafana instances
- **Delete Instance**: Remove specific Grafana instance
- **Port Forward**: Setup port forwarding (not needed with NodePort)

#### 4. Database Backup & Restore
- **Trigger Manual Backup**: Create immediate database backup
- **List All Backups**: View available backup files
- **View Backup Schedule**: Check CronJob configuration
- **View Latest Backup Logs**: See recent backup results
- **Check Backup System Health**: Verify backup infrastructure
- **Restore from Backup**: Restore database from backup file

#### 5. Monitoring & Infrastructure
- **Deploy Prometheus**: Install Prometheus monitoring stack
- **Deploy Istio**: Install Istio service mesh (optional)
- **Check Status**: View monitoring components status

#### 6. System Health Check
- **Run Health Check**: Comprehensive system health verification
- **Auto-Healing**: Automatic detection and repair of issues

#### 7. Diagnostics & Logs
- **List All Resources**: View all Kubernetes resources
- **View Pod Logs**: Display logs from specific pods
- **Describe Resources**: Get detailed resource information

---

## Architecture

### Cluster Configuration

**Nodes:**
- 1 Control Plane node: `grafana-cluster-control-plane`
- 2 Worker nodes: `grafana-cluster-worker`, `grafana-cluster-worker2`

**Port Mappings:**
- Container Port 30000 → Host Port 3030 (Grafana NodePort)

### Component Distribution

**grafana-operator namespace:**
- Grafana Operator Deployment (2 replicas)
- Controller manager and webhooks

**grafana-system namespace:**
- Grafana Instance Deployment (2 replicas)
- PostgreSQL StatefulSet (1 replica)
- Backup CronJob
- Backup PVC (50Gi)

**monitoring namespace:**
- Prometheus Server
- AlertManager
- Grafana (Prometheus UI)
- ServiceMonitors

### Storage Configuration

| Resource | Storage Class | Size | Purpose |
|----------|--------------|------|---------|
| PostgreSQL Data | standard | 20Gi | Grafana database |
| Backup PVC | standard | 50Gi | Database backups |
| Prometheus | standard | 50Gi | Metrics storage |

### Network Architecture

```
Internet
    |
    v
localhost:3030
    |
    v
Kind Node Port 30000
    |
    v
grafana-nodeport Service (ClusterIP)
    |
    v
Grafana Pods (2 replicas)
    |
    v
PostgreSQL Service
    |
    v
PostgreSQL Pod
```

---

## Database Backup and Restore

### Automated Backups

**Schedule**: Daily at 2:00 AM (configurable)
**Retention**: 7 days (automatic cleanup)
**Location**: PVC `postgresql-backup-pvc` (50GB)
**Format**: `grafana_backup_YYYYMMDD_HHMMSS.sql.gz`

### Manual Backup Operations

#### Trigger Manual Backup

Using Management Tool:
```bash
./grafana
# Select: 4 (Database Backup & Restore)
# Select: 1 (Trigger Manual Backup)
```

Using kubectl:
```bash
kubectl create job postgresql-backup-manual-$(date +%s) \
  --from=cronjob/postgresql-backup \
  -n grafana-system
```

#### List Available Backups

Using Management Tool:
```bash
./grafana
# Select: 4 (Database Backup & Restore)
# Select: 2 (List All Backups)
```

Using kubectl:
```bash
# Create temporary pod to list backups
kubectl run backup-list \
  --image=postgres:16-alpine \
  --restart=Never \
  -n grafana-system \
  --rm -it -- ls -lh /backups/
```

#### View Backup Logs

```bash
./grafana
# Select: 4 (Database Backup & Restore)
# Select: 4 (View Latest Backup Logs)
```

### Restore Operations

**IMPORTANT**: Restoration will DELETE all current data!

#### Restore from Backup (Automated)

Using Management Tool (Recommended):
```bash
./grafana
# Select: 4 (Database Backup & Restore)
# Select: 6 (Restore from Backup)
# Choose backup file from list
# Confirm restore operation
```

The restore process automatically:
1. Scales Grafana to 0 replicas (stops database connections)
2. Terminates any remaining database connections (with retry logic)
3. Drops and recreates the database
4. Restores data from backup file
5. Scales Grafana back to 2 replicas
6. Waits for pods to be ready

#### Manual Restore Process

If you need to restore manually:

```bash
# 1. Scale Grafana to 0
kubectl scale deployment -n grafana-system --all --replicas=0

# 2. Create restore job
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: postgresql-restore-manual
  namespace: grafana-system
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: restore
        image: postgres:16-alpine
        command: ["/bin/bash", "/scripts/restore.sh", "grafana_backup_YYYYMMDD_HHMMSS.sql.gz"]
        env:
        - name: POSTGRES_DB
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_DB
        - name: POSTGRES_USER
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgresql-secret
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: backup-storage
          mountPath: /backups
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: backup-storage
        persistentVolumeClaim:
          claimName: postgresql-backup-pvc
      - name: scripts
        configMap:
          name: postgresql-backup-scripts
EOF

# 3. Wait for completion
kubectl wait --for=condition=complete job/postgresql-restore-manual -n grafana-system --timeout=300s

# 4. Scale Grafana back up
kubectl scale deployment -n grafana-system --all --replicas=2
```

### Backup Monitoring

Check backup system health:
```bash
./grafana
# Select: 4 (Database Backup & Restore)
# Select: 5 (Check Backup System Health)
```

View CronJob schedule:
```bash
kubectl get cronjob postgresql-backup -n grafana-system -o wide
```

Check recent backup jobs:
```bash
kubectl get jobs -n grafana-system -l app=postgresql-backup \
  --sort-by=.metadata.creationTimestamp
```

---

## Monitoring

### Prometheus Monitoring Stack

The deployment includes Prometheus monitoring with:
- Prometheus Server
- AlertManager
- Grafana (for Prometheus UI)
- ServiceMonitors for all components

### Deploy Monitoring

Using Management Tool:
```bash
./grafana
# Select: 5 (Monitoring & Infrastructure)
# Select: 1 (Deploy Prometheus)
```

### Access Prometheus

Port forward to Prometheus:
```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

Then open: http://localhost:9090

### Access AlertManager

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-alertmanager 9093:9093
```

Then open: http://localhost:9093

### ServiceMonitors

ServiceMonitors are automatically configured for:
- Grafana Operator
- Grafana Instances
- PostgreSQL Database

View ServiceMonitors:
```bash
kubectl get servicemonitors -n monitoring
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Cluster Creation Fails

**Symptoms**: Error during cluster creation, Docker issues

**Solutions**:
```bash
# Check if Docker is running
docker ps

# Remove existing cluster
kind delete cluster --name grafana-cluster

# Clean up Docker containers
docker ps -a | grep kind | awk '{print $1}' | xargs docker rm -f

# Recreate cluster
./grafana
# Select: 1 -> 1 (Create Cluster)
```

#### Issue: Grafana Not Accessible

**Symptoms**: Cannot access http://localhost:3030

**Solutions**:
```bash
# Check service
kubectl get svc grafana-nodeport -n grafana-system

# Check pods are running
kubectl get pods -n grafana-system

# Check pod logs
kubectl logs -n grafana-system -l app=grafana --tail=50

# Verify port mapping
docker ps | grep grafana-cluster-control-plane
```

#### Issue: Operator Not Installing

**Symptoms**: CRD errors, operator pods not starting

**Solutions**:
```bash
# Check CRDs
kubectl get crds | grep grafana

# Check operator logs
kubectl logs -n grafana-operator -l app=grafana-operator --tail=100

# Reinstall operator
./grafana
# Select: 2 -> 2 (Uninstall Operator)
# Select: 2 -> 1 (Install Operator)
```

#### Issue: PostgreSQL Not Starting

**Symptoms**: Database connection errors, Grafana pods crashing

**Solutions**:
```bash
# Check PostgreSQL pod
kubectl get pods -n grafana-system -l app=postgresql

# Check logs
kubectl logs -n grafana-system -l app=postgresql --tail=100

# Check PVC
kubectl get pvc -n grafana-system

# Redeploy database
kubectl delete -f config/database/postgresql.yaml
kubectl apply -f config/database/postgresql.yaml
```

#### Issue: Backup Restore Fails

**Symptoms**: "Database is being accessed by other users"

**Solution**: The management tool now automatically handles this by:
1. Scaling Grafana to 0 before restore
2. Using retry logic to terminate connections
3. Scaling Grafana back after restore

If manual intervention needed:
```bash
# Force scale down
kubectl scale deployment -n grafana-system --all --replicas=0

# Wait 10 seconds, then retry restore
```

#### Issue: Port Conflict

**Symptoms**: Port 3030 already in use

**Solutions**:
```bash
# Check what's using the port
lsof -i :3030

# Kill the process (if safe)
kill -9 <PID>

# Or modify Kind config to use different port
# Edit config/kind-config.yaml and change hostPort
```

### Health Check

Run comprehensive health check:
```bash
./grafana
# Select: 6 (System Health Check)
```

This checks:
- Cluster connectivity
- Operator status
- Grafana instance health
- Database connectivity
- Backup system status

### View Logs

#### Operator Logs
```bash
kubectl logs -n grafana-operator -l app=grafana-operator -f
```

#### Grafana Logs
```bash
kubectl logs -n grafana-system -l app=grafana -f
```

#### PostgreSQL Logs
```bash
kubectl logs -n grafana-system -l app=postgresql -f
```

#### All Resources
```bash
./grafana
# Select: 7 (Diagnostics & Logs)
# Select: 1 (List All Resources)
```

---

## Configuration

### Default Credentials

**Grafana:**
- Username: `admin`
- Password: `Admin@12345`

**PostgreSQL:**
- Database: `grafana`
- Username: `grafana`
- Password: `grafana123`

To change these, edit `config/database/postgresql.yaml` and `config/grafana-instances/grafana-instance.yaml` before deployment.

### Cluster Configuration

Edit `config/kind-config.yaml` to customize:
- Node count
- Port mappings
- Kubernetes version
- Network settings

### Storage Configuration

Edit storage sizes in:
- `config/database/postgresql.yaml` (PostgreSQL: default 20Gi)
- `config/database/postgresql-backup.yaml` (Backups: default 50Gi)
- `config/monitoring/prometheus-install.yaml` (Prometheus: default 50Gi)

### Backup Schedule

Edit `config/database/postgresql-backup.yaml` to change backup schedule:
```yaml
schedule: "0 2 * * *"  # Daily at 2 AM
```

Cron format: `minute hour day month weekday`

### Resource Limits

Default resource limits are configured for production use. To modify:

Edit `config/grafana-operator/operator-deployment.yaml`:
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

Edit `config/grafana-instances/grafana-instance.yaml`:
```yaml
spec:
  deployment:
    spec:
      template:
        spec:
          containers:
          - resources:
              requests:
                cpu: 100m
                memory: 256Mi
              limits:
                cpu: 500m
                memory: 1Gi
```

---

## Advanced Operations

### Complete Reset and Rebuild

This operation destroys everything and rebuilds from scratch:

```bash
./grafana
# Select: 1 (Cluster Management)
# Select: 5 (Complete Reset)
# Type 'yes' to confirm
```

The automated process:
1. Deletes Kind cluster
2. Cleans Docker resources
3. Creates fresh cluster
4. Installs operator + CRDs
5. Deploys PostgreSQL
6. Deploys Grafana
7. Deploys Prometheus
8. Configures backups
9. Runs health check
10. Reports completion

### Scaling Operations

**Scale Grafana Replicas:**
```bash
kubectl scale deployment -n grafana-system grafana-instance-deployment --replicas=3
```

**Scale Operator Replicas:**
```bash
kubectl scale deployment -n grafana-operator grafana-operator-controller-manager --replicas=3
```

### Backup and Disaster Recovery

**Export Current Configuration:**
```bash
# Backup all manifests
kubectl get all -n grafana-system -o yaml > grafana-system-backup.yaml
kubectl get all -n grafana-operator -o yaml > grafana-operator-backup.yaml

# Backup secrets
kubectl get secrets -n grafana-system -o yaml > secrets-backup.yaml
```

**Create Database Backup Before Changes:**
```bash
./grafana
# Select: 4 -> 1 (Trigger Manual Backup)
```

### Upgrading Components

**Upgrade Operator:**
1. Backup current state
2. Delete operator: `./grafana` -> 2 -> 2
3. Update CRD files in `config/grafana-operator/`
4. Reinstall: `./grafana` -> 2 -> 1

**Upgrade Grafana Instance:**
```bash
# Edit version in config/grafana-instances/grafana-instance.yaml
kubectl apply -f config/grafana-instances/grafana-instance.yaml
```

### Multiple Grafana Instances

Deploy additional instances:
```bash
# Copy and modify instance config
cp config/grafana-instances/grafana-instance.yaml config/grafana-instances/grafana-instance-2.yaml

# Edit name and namespace
# Apply
kubectl apply -f config/grafana-instances/grafana-instance-2.yaml
```

### Cleanup Operations

**Delete All Resources:**
```bash
./grafana
# Select: 1 -> 2 (Delete Cluster)
```

**Delete Only Grafana:**
```bash
kubectl delete namespace grafana-system
```

**Delete Only Operator:**
```bash
kubectl delete namespace grafana-operator
```

**Clean Docker Resources:**
```bash
docker system prune -a --volumes
```

---

## Python Dependencies

Required packages (from `requirements.txt`):
- `kubernetes==29.0.0` - Kubernetes Python client
- `rich==13.7.0` - Terminal UI library
- `docker==7.0.0` - Docker Python SDK
- `PyYAML==6.0.1` - YAML parser
- `click==8.1.7` - CLI framework

---

## Support and Contributing

### Getting Help

1. Check this README for common solutions
2. Run health check: `./grafana` -> 6
3. View diagnostics: `./grafana` -> 7
4. Check pod logs for specific errors

### Project Information

- **Grafana Operator Version**: v5.9.2
- **Kubernetes Version**: v1.33.1 (Kind)
- **PostgreSQL Version**: 16-alpine
- **Prometheus Version**: kube-prometheus-stack (latest)

---

## Quick Reference Card

### Essential Commands

| Operation | Command |
|-----------|---------|
| Launch tool | `./grafana` |
| Complete deployment | `./grafana` -> 1 -> 5 |
| Access Grafana | http://localhost:3030 |
| Trigger backup | `./grafana` -> 4 -> 1 |
| Restore backup | `./grafana` -> 4 -> 6 |
| Health check | `./grafana` -> 6 |
| View logs | `./grafana` -> 7 |
| Delete everything | `./grafana` -> 1 -> 2 |

### Default Access

- **URL**: http://localhost:3030
- **Username**: admin
- **Password**: Admin@12345

### Critical Files

- Management Tool: `scripts/grafana-manager.py`
- Cluster Config: `config/kind-config.yaml`
- Operator Config: `config/grafana-operator/`
- Grafana Config: `config/grafana-instances/`
- Database Config: `config/database/`
- Backup Config: `config/database/postgresql-backup.yaml`

---

**Last Updated**: December 26, 2025
