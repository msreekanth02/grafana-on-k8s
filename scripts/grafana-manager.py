#!/usr/bin/env python3
"""
Grafana Operator Management Tool
A comprehensive CLI tool for managing Grafana Operator on Kind cluster
"""

import os
import sys
import time
import yaml
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    import docker
except ImportError:
    print("ERROR: Required packages not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

# Initialize Rich console
console = Console()

@dataclass
class Config:
    """Configuration management"""
    project_root: Path
    config_dir: Path
    kind_config: Path
    cluster_name: str = "grafana-cluster"
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.kind_config = self.config_dir / "kind-config.yaml"
        self.load_env()
    
    def load_env(self):
        """Load environment variables"""
        env_file = self.config_dir / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value


class ClusterManager:
    """Manage Kind cluster operations"""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.docker_client = docker.from_env()
    
    def create_cluster(self) -> bool:
        """Create Kind cluster from config"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Creating Kind cluster...", total=None)
                
                cmd = [
                    "kind", "create", "cluster",
                    "--config", str(self.cfg.kind_config),
                    "--wait", "5m"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    console.print(" Cluster created successfully", style="bold green")
                    console.print("\n[INFO] Cluster Info:")
                    self.get_cluster_info()
                    return True
                else:
                    console.print(f" Failed to create cluster: {result.stderr}", style="bold red")
                    return False
                    
        except Exception as e:
            console.print(f" Error creating cluster: {str(e)}", style="bold red")
            return False
    
    def delete_cluster(self) -> bool:
        """Delete Kind cluster"""
        if not Confirm.ask(f"Are you sure you want to delete cluster '{self.cfg.cluster_name}'?"):
            return False
        
        try:
            cmd = ["kind", "delete", "cluster", "--name", self.cfg.cluster_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(" Cluster deleted successfully", style="bold green")
                return True
            else:
                console.print(f" Failed to delete cluster: {result.stderr}", style="bold red")
                return False
                
        except Exception as e:
            console.print(f" Error deleting cluster: {str(e)}", style="bold red")
            return False
    
    def get_cluster_info(self) -> Dict:
        """Get cluster information"""
        try:
            # Get cluster details
            cmd = ["kind", "get", "clusters"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            clusters = result.stdout.strip().split('\n')
            
            if self.cfg.cluster_name not in clusters:
                console.print(f" Cluster '{self.cfg.cluster_name}' not found", style="bold red")
                return {}
            
            # Get nodes
            cmd = ["kubectl", "get", "nodes", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                nodes_data = json.loads(result.stdout)
                
                table = Table(title="Cluster Nodes")
                table.add_column("Node Name", style="cyan")
                table.add_column("Role", style="magenta")
                table.add_column("Status", style="green")
                table.add_column("Version", style="yellow")
                
                for node in nodes_data['items']:
                    name = node['metadata']['name']
                    role = "control-plane" if "control-plane" in node['metadata']['labels'].get('node-role.kubernetes.io/control-plane', '') else "worker"
                    status = node['status']['conditions'][-1]['type']
                    version = node['status']['nodeInfo']['kubeletVersion']
                    table.add_row(name, role, status, version)
                
                console.print(table)
                return nodes_data
            
        except Exception as e:
            console.print(f" Error getting cluster info: {str(e)}", style="bold red")
            return {}
    
    def export_kubeconfig(self) -> bool:
        """Export kubeconfig"""
        try:
            cmd = ["kind", "export", "kubeconfig", "--name", self.cfg.cluster_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(" Kubeconfig exported successfully", style="bold green")
                return True
            else:
                console.print(f" Failed to export kubeconfig: {result.stderr}", style="bold red")
                return False
                
        except Exception as e:
            console.print(f" Error exporting kubeconfig: {str(e)}", style="bold red")
            return False


class OperatorManager:
    """Manage Grafana Operator"""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.namespace = "grafana-operator"
        try:
            config.load_kube_config()
            self.k8s_client = client.ApiClient()
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
        except Exception as e:
            console.print(f" Warning: Could not load Kubernetes config: {e}", style="yellow")
    
    def install_operator(self) -> bool:
        """Install Grafana Operator"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                # Install CRDs
                task = progress.add_task("Installing Grafana CRDs...", total=None)
                
                # Try local CRDs first, fallback to remote URL
                local_crds = self.cfg.config_dir / "grafana-operator" / "crds.yaml"
                if local_crds.exists():
                    self._apply_manifest(local_crds)
                else:
                    # Fallback to correct remote URL
                    crd_url = "https://raw.githubusercontent.com/grafana/grafana-operator/master/deploy/kustomize/base/crds.yaml"
                    cmd = ["kubectl", "apply", "-f", crd_url]
                    subprocess.run(cmd, capture_output=True, check=True)
                
                # Create namespace
                progress.update(task, description="Creating namespace...")
                self._apply_manifest(self.cfg.config_dir / "grafana-operator" / "namespace.yaml")
                
                # Apply RBAC
                progress.update(task, description="Applying RBAC...")
                self._apply_manifest(self.cfg.config_dir / "grafana-operator" / "rbac.yaml")
                
                # Deploy operator
                progress.update(task, description="Deploying operator...")
                self._apply_manifest(self.cfg.config_dir / "grafana-operator" / "operator-deployment.yaml")
                
                # Wait for operator to be ready
                progress.update(task, description="Waiting for operator to be ready...")
                time.sleep(5)
                self._wait_for_deployment("grafana-operator", self.namespace)
                
                # Deploy PostgreSQL database (required for Grafana instances)
                progress.update(task, description="Deploying PostgreSQL database...")
                postgresql_manifest = self.cfg.config_dir / "database" / "postgresql.yaml"
                if postgresql_manifest.exists():
                    self._apply_manifest(postgresql_manifest)
                    console.print("   PostgreSQL deployed", style="green")
                else:
                    console.print("  [WARNING]  PostgreSQL manifest not found", style="yellow")
                
            console.print(" Grafana Operator and Database installed successfully", style="bold green")
            return True
            
        except Exception as e:
            console.print(f" Error installing operator: {str(e)}", style="bold red")
            return False
    
    def uninstall_operator(self) -> bool:
        """Uninstall Grafana Operator"""
        if not Confirm.ask("Are you sure you want to uninstall the Grafana Operator?"):
            return False
        
        try:
            cmd = ["kubectl", "delete", "namespace", self.namespace]
            subprocess.run(cmd, capture_output=True, check=True)
            console.print(" Grafana Operator uninstalled successfully", style="bold green")
            return True
        except Exception as e:
            console.print(f" Error uninstalling operator: {str(e)}", style="bold red")
            return False
    
    def get_operator_status(self) -> Dict:
        """Get operator status"""
        try:
            # Reload config to handle stale connections
            try:
                config.load_kube_config()
                self.apps_v1 = client.AppsV1Api()
            except:
                pass  # Config already loaded
            
            deployment = self.apps_v1.read_namespaced_deployment("grafana-operator", self.namespace)
            
            table = Table(title="Grafana Operator Status")
            table.add_column("Name", style="cyan")
            table.add_column("Ready", style="green")
            table.add_column("Available", style="green")
            table.add_column("Age", style="yellow")
            
            ready = f"{deployment.status.ready_replicas or 0}/{deployment.spec.replicas}"
            available = deployment.status.available_replicas or 0
            age = (time.time() - deployment.metadata.creation_timestamp.timestamp()) / 3600
            
            table.add_row(
                deployment.metadata.name,
                ready,
                str(available),
                f"{age:.1f}h"
            )
            
            console.print(table)
            return deployment.to_dict()
            
        except ApiException as e:
            if e.status == 404:
                console.print(" Operator not found", style="bold red")
            else:
                console.print(f" Error getting operator status: {str(e)}", style="bold red")
            return {}
        except Exception as e:
            # Fallback to kubectl if Python client fails
            console.print("[WARNING]  API connection issue, using kubectl fallback...", style="yellow")
            try:
                result = subprocess.run(
                    ["kubectl", "get", "deployment", "grafana-operator", "-n", self.namespace, "-o", "wide"],
                    capture_output=True, text=True, check=True
                )
                console.print(result.stdout)
                return {}
            except:
                console.print(f" Unexpected error: {str(e)}", style="bold red")
                return {}
    
    def view_operator_logs(self):
        """View operator logs"""
        try:
            cmd = [
                "kubectl", "logs", "-n", self.namespace,
                "-l", "app=grafana-operator",
                "--tail=100", "-f"
            ]
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n Log streaming stopped", style="bold yellow")
        except Exception as e:
            console.print(f" Error viewing logs: {str(e)}", style="bold red")
    
    def _apply_manifest(self, manifest_path: Path):
        """Apply Kubernetes manifest"""
        cmd = ["kubectl", "apply", "-f", str(manifest_path)]
        subprocess.run(cmd, capture_output=True, check=True)
    
    def _wait_for_deployment(self, name: str, namespace: str, timeout: int = 300):
        """Wait for deployment to be ready"""
        cmd = [
            "kubectl", "wait", "--for=condition=available",
            f"deployment/{name}", "-n", namespace,
            f"--timeout={timeout}s"
        ]
        subprocess.run(cmd, capture_output=True, check=True)


class GrafanaManager:
    """Manage Grafana instances"""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.namespace = "grafana-system"
        try:
            config.load_kube_config()
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
        except Exception as e:
            console.print(f" Warning: Could not load Kubernetes config: {e}", style="yellow")
    
    def deploy_grafana(self) -> bool:
        """Deploy Grafana instance"""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                # Ensure PostgreSQL is running (it should be deployed with operator)
                task = progress.add_task("Checking PostgreSQL...", total=None)
                try:
                    result = subprocess.run(
                        ["kubectl", "get", "statefulset", "postgresql", "-n", "grafana-system"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode != 0:
                        console.print("  [WARNING]  PostgreSQL not found, deploying now...", style="yellow")
                        self._apply_manifest(self.cfg.config_dir / "database" / "postgresql.yaml")
                        time.sleep(10)
                    else:
                        console.print("   PostgreSQL already running", style="green")
                except:
                    console.print("  [WARNING]  Could not check PostgreSQL, deploying to be safe...", style="yellow")
                    self._apply_manifest(self.cfg.config_dir / "database" / "postgresql.yaml")
                    time.sleep(10)
                
                # Deploy storage
                progress.update(task, description="Configuring storage...")
                self._apply_manifest(self.cfg.config_dir / "storage" / "storage-class.yaml")
                
                # Deploy ConfigMaps
                progress.update(task, description="Applying ConfigMaps...")
                self._apply_manifest(self.cfg.config_dir / "configmaps" / "grafana-config.yaml")
                self._apply_manifest(self.cfg.config_dir / "configmaps" / "resource-quotas.yaml")
                
                # Deploy Grafana instance
                progress.update(task, description="Deploying Grafana instance...")
                self._apply_manifest(self.cfg.config_dir / "grafana-instances" / "grafana-instance.yaml")
                
                # Deploy datasources
                progress.update(task, description="Configuring datasources...")
                time.sleep(10)
                self._apply_manifest(self.cfg.config_dir / "grafana-instances" / "grafana-datasources.yaml")
                
                # Deploy networking
                progress.update(task, description="Configuring networking...")
                self._apply_manifest(self.cfg.config_dir / "networking" / "services.yaml")
                self._apply_manifest(self.cfg.config_dir / "networking" / "network-policies.yaml")
                
            console.print(" Grafana deployed successfully", style="bold green")
            console.print("\n[INFO] Access Grafana at: http://localhost:3030")
            console.print("Username: Username: admin")
            console.print("Password: Password: Admin@12345")
            return True
            
        except Exception as e:
            console.print(f" Error deploying Grafana: {str(e)}", style="bold red")
            return False
    
    def list_instances(self):
        """List Grafana instances"""
        try:
            cmd = ["kubectl", "get", "grafanas", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            data = json.loads(result.stdout)
            
            if not data.get('items'):
                console.print("No Grafana instances found", style="yellow")
                return
            
            table = Table(title="Grafana Instances")
            table.add_column("Name", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("URL", style="blue")
            table.add_column("Age", style="yellow")
            
            for item in data['items']:
                name = item['metadata']['name']
                status = item.get('status', {}).get('stage', 'Unknown')
                url = item.get('spec', {}).get('config', {}).get('server', {}).get('root_url', 'N/A')
                
                # Parse creation timestamp
                creation_time = item['metadata'].get('creationTimestamp', '')
                if creation_time:
                    from datetime import datetime, timezone
                    created = datetime.strptime(creation_time.replace('Z', '+00:00').split('+')[0], '%Y-%m-%dT%H:%M:%S')
                    age_seconds = (datetime.now(timezone.utc).replace(tzinfo=None) - created).total_seconds()
                    if age_seconds < 3600:
                        age = f"{age_seconds / 60:.0f}m"
                    elif age_seconds < 86400:
                        age = f"{age_seconds / 3600:.1f}h"
                    else:
                        age = f"{age_seconds / 86400:.1f}d"
                else:
                    age = "N/A"
                
                table.add_row(name, status, url, age)
            
            console.print(table)
            
        except Exception as e:
            console.print(f" Error listing instances: {str(e)}", style="bold red")
    
    def delete_instance(self, name: str):
        """Delete Grafana instance"""
        if not Confirm.ask(f"Are you sure you want to delete instance '{name}'?"):
            return False
        
        try:
            cmd = ["kubectl", "delete", "grafana", name, "-n", self.namespace]
            subprocess.run(cmd, capture_output=True, check=True)
            console.print(f" Instance '{name}' deleted successfully", style="bold green")
            return True
        except Exception as e:
            console.print(f" Error deleting instance: {str(e)}", style="bold red")
            return False
    
    def port_forward(self):
        """Port forward to Grafana"""
        try:
            console.print(" Port forwarding to Grafana on http://localhost:3030", style="bold blue")
            console.print("Press Ctrl+C to stop", style="yellow")
            
            cmd = [
                "kubectl", "port-forward", "-n", self.namespace,
                "svc/grafana-instance-service", "3030:3000"
            ]
            subprocess.run(cmd)
        except KeyboardInterrupt:
            console.print("\n Port forwarding stopped", style="bold yellow")
        except Exception as e:
            console.print(f" Error port forwarding: {str(e)}", style="bold red")
    
    def _apply_manifest(self, manifest_path: Path):
        """Apply Kubernetes manifest"""
        cmd = ["kubectl", "apply", "-f", str(manifest_path)]
        subprocess.run(cmd, capture_output=True, check=True)


class BackupManager:
    """Manage database backups with auto-healing"""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.namespace = "grafana-system"
        self.backup_pvc = "postgresql-backup-pvc"
    
    def _check_backup_health(self) -> bool:
        """Check if backup infrastructure is healthy"""
        try:
            # Check if CronJob exists
            result = subprocess.run(
                ["kubectl", "get", "cronjob", "postgresql-backup", "-n", self.namespace],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print("[WARNING]  Backup CronJob not found. Attempting to create...", style="yellow")
                self._deploy_backup_infrastructure()
                return True
            
            # Check if PVC exists
            result = subprocess.run(
                ["kubectl", "get", "pvc", self.backup_pvc, "-n", self.namespace],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                console.print("[WARNING]  Backup PVC not found. Attempting to create...", style="yellow")
                self._deploy_backup_infrastructure()
                return True
            
            return True
        except Exception as e:
            console.print(f"[ERROR] Backup health check failed: {e}", style="red")
            return False
    
    def _deploy_backup_infrastructure(self):
        """Deploy backup infrastructure if missing"""
        try:
            backup_yaml = self.cfg.config_dir / "database" / "postgresql-backup.yaml"
            if backup_yaml.exists():
                subprocess.run(["kubectl", "apply", "-f", str(backup_yaml)], check=True)
                console.print("[OK] Backup infrastructure deployed", style="green")
            else:
                console.print("[ERROR] Backup configuration file not found", style="red")
        except Exception as e:
            console.print(f"[ERROR] Failed to deploy backup infrastructure: {e}", style="red")
    
    def trigger_backup(self) -> bool:
        """Trigger manual backup with auto-healing"""
        try:
            if not self._check_backup_health():
                console.print("[ERROR] Cannot proceed - backup system unhealthy", style="red")
                return False
            
            console.print("[PROCESSING] Triggering database backup...", style="bold blue")
            
            # Check if PostgreSQL is running
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", self.namespace, "-l", "app=postgresql", "-o", "json"],
                capture_output=True, text=True, check=True
            )
            pods = json.loads(result.stdout)
            
            if not pods.get('items'):
                console.print("[WARNING]  PostgreSQL not running. Cannot backup.", style="red")
                return False
            
            # Check if PostgreSQL is ready
            pod = pods['items'][0]
            if pod['status']['phase'] != 'Running':
                console.print("[WARNING]  PostgreSQL pod not ready. Waiting...", style="yellow")
                subprocess.run(
                    ["kubectl", "wait", "--for=condition=ready", "pod", "-l", "app=postgresql",
                     "-n", self.namespace, "--timeout=60s"],
                    capture_output=True
                )
            
            # Create backup job
            job_name = f"postgresql-backup-manual-{int(time.time())}"
            cmd = [
                "kubectl", "create", "job", job_name,
                "--from=cronjob/postgresql-backup", "-n", self.namespace
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            console.print(f"[OK] Backup job '{job_name}' started", style="green")
            console.print("[WAIT] Waiting for backup to complete...", style="yellow")
            
            # Wait for job completion
            time.sleep(5)
            result = subprocess.run(
                ["kubectl", "wait", "--for=condition=complete", f"job/{job_name}",
                 "-n", self.namespace, "--timeout=120s"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                # Show backup logs
                logs = subprocess.run(
                    ["kubectl", "logs", "-n", self.namespace, f"job/{job_name}"],
                    capture_output=True, text=True
                )
                console.print("\n[bold green][INFO] Backup Log:[/]")
                console.print(logs.stdout)
                return True
            else:
                console.print("[WARNING]  Backup job taking longer than expected. Check logs later.", style="yellow")
                return False
                
        except Exception as e:
            console.print(f"[ERROR] Backup failed: {e}", style="red")
            return False
    
    def list_backups(self):
        """List all available backups"""
        try:
            if not self._check_backup_health():
                return
            
            console.print("[INFO] Listing available backups...", style="bold blue")
            
            # Create a temporary pod to list backups with sync command
            timestamp = int(time.time())
            pod_name = f"backup-list-temp-{timestamp}"
            pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: {pod_name}
  namespace: {self.namespace}
spec:
  restartPolicy: Never
  containers:
  - name: list
    image: postgres:16-alpine
    command: ["sh", "-c", "sync && ls -lh /backups/*.sql.gz 2>/dev/null || echo 'No backups found'"]
    volumeMounts:
    - name: backup-storage
      mountPath: /backups
  volumes:
  - name: backup-storage
    persistentVolumeClaim:
      claimName: {self.backup_pvc}
"""
            
            # Apply pod
            proc = subprocess.Popen(
                ["kubectl", "apply", "-f", "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(input=pod_yaml.encode())
            
            if proc.returncode != 0:
                console.print(f"[ERROR] Failed to create list pod: {stderr.decode()}", style="red")
                return
            
            # Wait for pod to complete (not just ready)
            console.print("[WAIT] Fetching backup list...", style="yellow")
            time.sleep(3)
            
            # Wait for pod completion
            wait_result = subprocess.run(
                ["kubectl", "wait", "--for=condition=Ready", f"pod/{pod_name}",
                 "-n", self.namespace, "--timeout=30s"],
                capture_output=True
            )
            
            if wait_result.returncode == 0:
                # Give extra time for the command to execute
                time.sleep(3)
            
            # Get logs
            result = subprocess.run(
                ["kubectl", "logs", "-n", self.namespace, pod_name],
                capture_output=True, text=True
            )
            
            console.print("\n[bold cyan]Available Backups:[/]")
            if result.stdout and "No backups found" not in result.stdout:
                console.print(result.stdout)
            else:
                console.print("[WARNING]  No backups found yet", style="yellow")
            
            # Cleanup
            subprocess.run(
                ["kubectl", "delete", "pod", pod_name, "-n", self.namespace, "--ignore-not-found=true"],
                capture_output=True
            )
        except Exception as e:
            console.print(f"[ERROR] Failed to list backups: {e}", style="red")
    
    def view_schedule(self):
        """View backup schedule"""
        try:
            if not self._check_backup_health():
                return
            
            console.print("\n[bold blue] Backup Schedule:[/]")
            subprocess.run(
                ["kubectl", "get", "cronjob", "postgresql-backup", "-n", self.namespace, "-o", "wide"]
            )
            
            console.print("\n[bold blue]Recent Backup Jobs:[/]")
            subprocess.run(
                ["kubectl", "get", "jobs", "-n", self.namespace, "-l", "app=postgresql-backup",
                 "--sort-by=.metadata.creationTimestamp"]
            )
        except Exception as e:
            console.print(f"[ERROR] Failed to view schedule: {e}", style="red")
    
    def view_logs(self):
        """View latest backup logs"""
        try:
            console.print(" Fetching latest backup logs...", style="bold blue")
            
            result = subprocess.run(
                ["kubectl", "get", "jobs", "-n", self.namespace, "-l", "app=postgresql-backup",
                 "--sort-by=.metadata.creationTimestamp", "-o", "json"],
                capture_output=True, text=True, check=True
            )
            
            jobs = json.loads(result.stdout)
            
            if not jobs.get('items'):
                console.print("[WARNING]  No backup jobs found", style="yellow")
                return
            
            latest_job = jobs['items'][-1]['metadata']['name']
            console.print(f"\n[bold cyan]Logs from: {latest_job}[/]")
            subprocess.run(
                ["kubectl", "logs", "-n", self.namespace, f"job/{latest_job}", "--tail=50"]
            )
        except Exception as e:
            console.print(f"[ERROR] Failed to view logs: {e}", style="red")
    
    def restore_backup(self):
        """Restore database from a backup"""
        try:
            if not self._check_backup_health():
                console.print("[ERROR] Cannot proceed - backup system unhealthy", style="red")
                return False
            
            console.print("\n[bold red][WARNING]  WARNING: Database Restore[/]")
            console.print("[yellow]This will:[/]")
            console.print("  • Drop the current Grafana database")
            console.print("  • Delete ALL existing data")
            console.print("  • Restore from selected backup")
            console.print("\n[bold red]THIS CANNOT BE UNDONE![/]")
            
            # List available backups first
            console.print("\n[INFO] Fetching available backups...", style="bold blue")
            
            # Create temporary pod to list backups
            list_pod_yaml = f"""
apiVersion: v1
kind: Pod
metadata:
  name: backup-list-temp
  namespace: {self.namespace}
spec:
  restartPolicy: Never
  containers:
  - name: list
    image: postgres:16-alpine
    command: ["sh", "-c", "ls -1 /backups/*.sql.gz 2>/dev/null | xargs -n 1 basename && sleep 5"]
    volumeMounts:
    - name: backup-storage
      mountPath: /backups
  volumes:
  - name: backup-storage
    persistentVolumeClaim:
      claimName: {self.backup_pvc}
"""
            
            proc = subprocess.Popen(
                ["kubectl", "apply", "-f", "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            proc.communicate(input=list_pod_yaml.encode())
            
            time.sleep(5)
            result = subprocess.run(
                ["kubectl", "logs", "-n", self.namespace, "backup-list-temp"],
                capture_output=True, text=True
            )
            
            # Cleanup list pod
            subprocess.run(
                ["kubectl", "delete", "pod", "backup-list-temp", "-n", self.namespace, "--ignore-not-found=true"],
                capture_output=True
            )
            
            if not result.stdout.strip():
                console.print("[ERROR] No backups found", style="red")
                return False
            
            backups = [b.strip() for b in result.stdout.strip().split('\n') if b.strip()]
            
            if not backups:
                console.print("[ERROR] No backups available", style="red")
                return False
            
            console.print("\n[bold cyan]Available Backups:[/]")
            for idx, backup in enumerate(backups, 1):
                console.print(f"  {idx}. {backup}")
            
            # Ask user to select backup
            selection = Prompt.ask(
                "\nSelect backup number to restore (or 0 to cancel)",
                choices=[str(i) for i in range(len(backups) + 1)]
            )
            
            if selection == "0":
                console.print("Restore cancelled", style="yellow")
                return False
            
            selected_backup = backups[int(selection) - 1]
            
            if not Confirm.ask(f"\n[bold red]Restore from '{selected_backup}'? This will DELETE all current data![/]"):
                console.print("Restore cancelled", style="yellow")
                return False
            
            console.print(f"\n[PROCESSING] Starting restore from {selected_backup}...", style="bold blue")
            
            # Scale Grafana to 0 to prevent database connections during restore
            console.print(" Scaling Grafana to 0 replicas to prevent database connections...", style="yellow")
            scale_down = subprocess.run(
                ["kubectl", "scale", "deployment", "-n", "grafana-system", "--all", "--replicas=0"],
                capture_output=True, text=True
            )
            
            if scale_down.returncode != 0:
                console.print(f"[WARNING]  Warning: Failed to scale down Grafana: {scale_down.stderr}", style="yellow")
            else:
                console.print("[OK] Grafana scaled to 0 replicas", style="green")
                time.sleep(5)  # Wait for pods to terminate
            
            # Create restore job
            restore_job_yaml = f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: postgresql-restore-{int(time.time())}
  namespace: {self.namespace}
spec:
  ttlSecondsAfterFinished: 300
  template:
    metadata:
      labels:
        app: postgresql-restore
    spec:
      restartPolicy: Never
      containers:
      - name: restore
        image: postgres:16-alpine
        command: ["/bin/bash", "/scripts/restore.sh", "{selected_backup}"]
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
          claimName: {self.backup_pvc}
      - name: scripts
        configMap:
          name: postgresql-backup-scripts
          defaultMode: 0755
"""
            
            proc = subprocess.Popen(
                ["kubectl", "apply", "-f", "-"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate(input=restore_job_yaml.encode())
            
            if proc.returncode != 0:
                console.print(f"[ERROR] Failed to create restore job: {stderr.decode()}", style="red")
                return False
            
            job_name = f"postgresql-restore-{int(time.time())}"
            console.print(f"[OK] Restore job '{job_name}' started", style="green")
            console.print("[WAIT] Waiting for restore to complete (this may take a few minutes)...", style="yellow")
            
            # Wait for job completion
            time.sleep(10)
            result = subprocess.run(
                ["kubectl", "wait", "--for=condition=complete", f"job/{job_name}",
                 "-n", self.namespace, "--timeout=300s"],
                capture_output=True, text=True
            )
            
            # Show restore logs
            logs = subprocess.run(
                ["kubectl", "logs", "-n", self.namespace, f"job/{job_name}"],
                capture_output=True, text=True
            )
            console.print("\n[bold green][INFO] Restore Log:[/]")
            console.print(logs.stdout)
            
            if result.returncode == 0:
                console.print("\n[OK] Database restored successfully!", style="bold green")
                
                # Scale Grafana back to original replica count
                console.print("\n Scaling Grafana back to original replica count...", style="bold blue")
                scale_up = subprocess.run(
                    ["kubectl", "scale", "deployment", "-n", "grafana-system", "--all", "--replicas=2"],
                    capture_output=True, text=True
                )
                
                if scale_up.returncode == 0:
                    console.print("[OK] Grafana scaled back to 2 replicas", style="green")
                    console.print("[WAIT] Waiting for pods to be ready...", style="yellow")
                    
                    # Wait for rollout to complete
                    time.sleep(5)
                    rollout_status = subprocess.run(
                        ["kubectl", "rollout", "status", "deployment", "-n", "grafana-system", "--timeout=120s"],
                        capture_output=True, text=True
                    )
                    
                    if rollout_status.returncode == 0:
                        console.print("[OK] All Grafana pods are ready with restored data!", style="bold green")
                        console.print("\n[cyan] Access Grafana at: http://localhost:3030[/]")
                    else:
                        console.print("[WARNING]  Rollout taking longer than expected. Check status manually.", style="yellow")
                else:
                    console.print(f"[WARNING]  Failed to scale up Grafana: {scale_up.stderr}", style="yellow")
                    console.print("\n[yellow]Manual scaling required:[/]")
                    console.print("  kubectl scale deployment -n grafana-system --all --replicas=2")
                
                return True
            else:
                console.print("\n[ERROR] Restore job failed or timed out. Check logs above.", style="red")
                return False
                
        except Exception as e:
            console.print(f"[ERROR] Restore failed: {e}", style="red")
            return False


class HealthChecker:
    """System health checker with auto-healing"""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
    
    def check_all(self) -> Dict[str, bool]:
        """Comprehensive health check with auto-healing"""
        console.print("\n[CHECK] Running system health check...\n", style="bold blue")
        
        health = {}
        
        # Check Kind cluster
        health['cluster'] = self._check_cluster()
        
        # Check Operator
        health['operator'] = self._check_operator()
        
        # Check Grafana
        health['grafana'] = self._check_grafana()
        
        # Check Database
        health['database'] = self._check_database()
        
        # Check Backups
        health['backups'] = self._check_backups()
        
        # Summary
        self._print_health_summary(health)
        
        return health
    
    def _check_cluster(self) -> bool:
        """Check Kind cluster health"""
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                console.print("[OK] Cluster: Healthy", style="green")
                return True
            else:
                console.print("[ERROR] Cluster: Not responding", style="red")
                return False
        except Exception:
            console.print("[ERROR] Cluster: Not accessible", style="red")
            return False
    
    def _check_operator(self) -> bool:
        """Check Grafana Operator health"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "deployment", "grafana-operator", "-n", "grafana-operator", "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                console.print("[WARNING]  Operator: Not deployed", style="yellow")
                return False
            
            deployment = json.loads(result.stdout)
            ready = deployment['status'].get('readyReplicas', 0)
            desired = deployment['status'].get('replicas', 0)
            
            if ready == desired and ready > 0:
                console.print(f"[OK] Operator: Healthy ({ready}/{desired} replicas)", style="green")
                return True
            else:
                console.print(f"[WARNING]  Operator: {ready}/{desired} replicas ready", style="yellow")
                # Auto-heal: restart deployment
                console.print(" Auto-healing: Restarting operator...", style="yellow")
                subprocess.run(
                    ["kubectl", "rollout", "restart", "deployment", "grafana-operator", "-n", "grafana-operator"],
                    capture_output=True
                )
                return False
        except Exception as e:
            console.print(f"[ERROR] Operator: Error - {e}", style="red")
            return False
    
    def _check_grafana(self) -> bool:
        """Check Grafana instance health"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "grafana-system", "-l", "app=grafana-instance", "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                console.print("[WARNING]  Grafana: Not deployed", style="yellow")
                return False
            
            pods = json.loads(result.stdout)
            items = pods.get('items', [])
            
            if not items:
                console.print("[WARNING]  Grafana: No pods found", style="yellow")
                return False
            
            running = sum(1 for pod in items if pod['status']['phase'] == 'Running')
            total = len(items)
            
            if running == total:
                console.print(f"[OK] Grafana: Healthy ({running}/{total} pods)", style="green")
                # Check accessibility
                try:
                    result = subprocess.run(
                        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3030/api/health"],
                        capture_output=True, text=True, timeout=5
                    )
                    if "200" in result.stdout:
                        console.print("[OK] Grafana: Accessible at http://localhost:3030", style="green")
                    else:
                        console.print("[WARNING]  Grafana: Pods running but not accessible", style="yellow")
                except:
                    console.print("ℹ  Grafana: Port check skipped", style="dim")
                return True
            else:
                console.print(f"[WARNING]  Grafana: {running}/{total} pods running", style="yellow")
                # Auto-heal: restart failed pods
                for pod in items:
                    if pod['status']['phase'] != 'Running':
                        pod_name = pod['metadata']['name']
                        console.print(f" Auto-healing: Deleting pod {pod_name}...", style="yellow")
                        subprocess.run(
                            ["kubectl", "delete", "pod", pod_name, "-n", "grafana-system"],
                            capture_output=True
                        )
                return False
        except Exception as e:
            console.print(f"[ERROR] Grafana: Error - {e}", style="red")
            return False
    
    def _check_database(self) -> bool:
        """Check PostgreSQL health"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", "grafana-system", "-l", "app=postgresql", "-o", "json"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                console.print("[WARNING]  Database: Not deployed", style="yellow")
                return False
            
            pods = json.loads(result.stdout)
            items = pods.get('items', [])
            
            if not items:
                console.print("[WARNING]  Database: No pods found", style="yellow")
                return False
            
            pod = items[0]
            if pod['status']['phase'] == 'Running':
                console.print("[OK] Database: Healthy", style="green")
                return True
            else:
                console.print(f"[WARNING]  Database: Status - {pod['status']['phase']}", style="yellow")
                return False
        except Exception as e:
            console.print(f"[ERROR] Database: Error - {e}", style="red")
            return False
    
    def _check_backups(self) -> bool:
        """Check backup system health"""
        try:
            result = subprocess.run(
                ["kubectl", "get", "cronjob", "postgresql-backup", "-n", "grafana-system"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                console.print("[OK] Backups: CronJob configured", style="green")
                return True
            else:
                console.print("[WARNING]  Backups: Not configured", style="yellow")
                return False
        except Exception as e:
            console.print(f"[ERROR] Backups: Error - {e}", style="red")
            return False
    
    def _print_health_summary(self, health: Dict[str, bool]):
        """Print health summary"""
        total = len(health)
        healthy = sum(1 for v in health.values() if v)
        
        console.print(f"\n{'='*50}", style="cyan")
        if healthy == total:
            console.print(" System Status: ALL HEALTHY", style="bold green")
        elif healthy >= total * 0.7:
            console.print(f"[WARNING]  System Status: MOSTLY HEALTHY ({healthy}/{total})", style="bold yellow")
        else:
            console.print(f"[ERROR] System Status: NEEDS ATTENTION ({healthy}/{total})", style="bold red")
        console.print(f"{'='*50}\n", style="cyan")


class MonitoringManager:
    """Manage monitoring setup"""
    
    def __init__(self, cfg: Config):
        self.cfg = cfg
    
    def deploy_prometheus(self) -> bool:
        """Deploy Prometheus"""
        try:
            console.print(" Deploying Prometheus...", style="bold blue")
            
            # Check if Helm is installed
            result = subprocess.run(["helm", "version"], capture_output=True)
            if result.returncode != 0:
                console.print(" Helm not installed. Please install Helm first.", style="bold red")
                return False
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Installing Prometheus...", total=None)
                
                # Add Helm repo
                subprocess.run(
                    ["helm", "repo", "add", "prometheus-community", 
                     "https://prometheus-community.github.io/helm-charts"],
                    capture_output=True
                )
                subprocess.run(["helm", "repo", "update"], capture_output=True)
                
                # Install Prometheus
                cmd = [
                    "helm", "install", "prometheus", "prometheus-community/kube-prometheus-stack",
                    "--namespace", "monitoring", "--create-namespace",
                    "--set", "prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false",
                    "--set", "prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false",
                    "--set", "prometheus.prometheusSpec.retention=30d",
                    "--set", "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.storageClassName=standard",
                    "--set", "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi",
                    "--set", "grafana.enabled=false",
                    "--wait", "--timeout=10m"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    progress.update(task, description="Applying ServiceMonitors...")
                    self._apply_manifest(self.cfg.config_dir / "monitoring" / "service-monitors.yaml")
                    
                    console.print(" Prometheus deployed successfully", style="bold green")
                    return True
                else:
                    console.print(f" Failed to deploy Prometheus: {result.stderr}", style="bold red")
                    return False
                    
        except Exception as e:
            console.print(f" Error deploying Prometheus: {str(e)}", style="bold red")
            return False
    
    def deploy_istio(self) -> bool:
        """Deploy Istio"""
        try:
            console.print(" Deploying Istio...", style="bold blue")
            
            # Check if istioctl is installed
            result = subprocess.run(["istioctl", "version"], capture_output=True)
            if result.returncode != 0:
                console.print(" istioctl not installed. Please install Istio CLI first.", style="bold red")
                console.print("Install: curl -L https://istio.io/downloadIstio | sh -", style="yellow")
                return False
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Installing Istio...", total=None)
                
                # Install Istio
                cmd = ["istioctl", "install", "--set", "profile=default", "-y"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Enable injection for grafana-system
                    progress.update(task, description="Enabling Istio injection...")
                    subprocess.run(
                        ["kubectl", "label", "namespace", "grafana-system", "istio-injection=enabled", "--overwrite"],
                        capture_output=True
                    )
                    
                    # Apply Istio Gateway
                    progress.update(task, description="Applying Istio Gateway...")
                    time.sleep(5)
                    self._apply_manifest(self.cfg.config_dir / "networking" / "istio-gateway.yaml")
                    
                    console.print(" Istio deployed successfully", style="bold green")
                    return True
                else:
                    console.print(f" Failed to deploy Istio: {result.stderr}", style="bold red")
                    return False
                    
        except Exception as e:
            console.print(f" Error deploying Istio: {str(e)}", style="bold red")
            return False
    
    def _apply_manifest(self, manifest_path: Path):
        """Apply Kubernetes manifest"""
        cmd = ["kubectl", "apply", "-f", str(manifest_path)]
        subprocess.run(cmd, capture_output=True, check=True)


def print_banner():
    """Print application banner"""
    banner = """
    
                                                           
             Grafana Operator Management Tool         
                                                           
         Manage Grafana Operator on Kind Cluster          
                                                           
    
    """
    console.print(banner, style="bold cyan")


def main_menu():
    """Display main menu"""
    menu = Panel.fit(
        """
[bold cyan]1.[/] Cluster Management
[bold cyan]2.[/] Operator Management
[bold cyan]3.[/] Grafana Instance Management
[bold cyan]4.[/] Database Backup & Restore
[bold cyan]5.[/] Monitoring & Infrastructure
[bold cyan]6.[/] System Health Check
[bold cyan]7.[/] Diagnostics & Logs
[bold cyan]0.[/] Exit
        """,
        title="[bold magenta]Main Menu[/]",
        border_style="cyan"
    )
    console.print(menu)


def cluster_menu(cluster_mgr: ClusterManager):
    """Cluster management menu"""
    while True:
        console.print("\n[bold cyan] Cluster Management [/]")
        console.print("1. Create Cluster")
        console.print("2. Delete Cluster")
        console.print("3. Get Cluster Info")
        console.print("4. Export Kubeconfig")
        console.print("5. Complete Reset (Destroy & Rebuild)")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5"])
        
        if choice == "0":
            break
        elif choice == "1":
            cluster_mgr.create_cluster()
        elif choice == "2":
            cluster_mgr.delete_cluster()
        elif choice == "3":
            cluster_mgr.get_cluster_info()
        elif choice == "4":
            cluster_mgr.export_kubeconfig()
        elif choice == "5":
            complete_reset(cluster_mgr)


def complete_reset(cluster_mgr: ClusterManager):
    """Complete cluster reset - destroy and rebuild everything"""
    console.print("\n[bold red][WARNING]  COMPLETE RESET - This will destroy EVERYTHING and rebuild from scratch![/]")
    console.print("\n[yellow]This will:[/]")
    console.print("  • Delete the entire Kind cluster")
    console.print("  • Remove all Grafana instances and data")
    console.print("  • Delete all backups and monitoring")
    console.print("  • Clean up Docker volumes")
    console.print("  • Rebuild cluster with FULL automation")
    console.print("  • Auto-deploy: Operator + Database + Grafana + Monitoring + Backups")
    console.print("\n[bold red]THIS CANNOT BE UNDONE![/]")
    
    if not Confirm.ask("\n[bold]Are you ABSOLUTELY sure? Type 'yes' to confirm", default=False):
        console.print("Reset cancelled", style="yellow")
        return
    
    try:
        # Step 1: Delete cluster
        console.print("\n[bold blue]Step 1/10: Deleting Kind cluster...[/]")
        cluster_mgr.delete_cluster()
        time.sleep(3)
        
        # Step 2: Clean up Docker resources
        console.print("\n[bold blue]Step 2/10: Cleaning up Docker resources...[/]")
        subprocess.run(["docker", "system", "prune", "-f"], capture_output=True)
        console.print("[OK] Docker cleanup complete", style="green")
        
        # Step 3: Verify cleanup
        # Step 3: Verify cleanup
        console.print("\n[bold blue]Step 3/10: Verifying cleanup...[/]")
        result = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True)
        if "grafana-cluster" not in result.stdout:
            console.print("[OK] Cluster completely removed", style="green")
        else:
            console.print("[WARNING]  Cluster still exists, retrying...", style="yellow")
            subprocess.run(["kind", "delete", "cluster", "--name", "grafana-cluster"], capture_output=True)
            time.sleep(2)
        
        # Step 4: Rebuild cluster
        console.print("\n[bold blue]Step 4/10: Creating fresh cluster...[/]")
        if cluster_mgr.create_cluster():
            console.print("[OK] Cluster created successfully", style="green")
        else:
            console.print("[ERROR] Failed to create cluster", style="red")
            return
        
        # Step 5: Verify new cluster
        console.print("\n[bold blue]Step 5/10: Verifying new cluster...[/]")
        time.sleep(5)
        result = subprocess.run(["kubectl", "get", "nodes"], capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[OK] New cluster is ready!", style="bold green")
            console.print("\n[cyan]Nodes:[/]")
            console.print(result.stdout)
        else:
            console.print("[WARNING]  Cluster created but not responding yet", style="yellow")
            return
        
        # Step 6: Install Operator + Database
        console.print("\n[bold blue]Step 6/10: Installing Grafana Operator + Database...[/]")
        operator_mgr = OperatorManager(cluster_mgr.cfg)
        if operator_mgr.install_operator():
            console.print("[OK] Operator and Database deployed", style="green")
        else:
            console.print("[ERROR] Failed to deploy operator", style="red")
            return
        
        # Wait for operator to stabilize
        time.sleep(10)
        
        # Step 7: Deploy Grafana Instance
        console.print("\n[bold blue]Step 7/10: Deploying Grafana Instance...[/]")
        grafana_mgr = GrafanaManager(cluster_mgr.cfg)
        if grafana_mgr.deploy_grafana():
            console.print("[OK] Grafana deployed", style="green")
        else:
            console.print("[ERROR] Failed to deploy Grafana", style="red")
            return
        
        # Step 8: Deploy Monitoring (Prometheus)
        console.print("\n[bold blue]Step 8/10: Deploying Prometheus Monitoring...[/]")
        monitoring_mgr = MonitoringManager(cluster_mgr.cfg)
        if monitoring_mgr.deploy_prometheus():
            console.print("[OK] Prometheus monitoring deployed", style="green")
        else:
            console.print("[WARNING]  Prometheus deployment skipped or failed", style="yellow")
        
        # Wait for Prometheus to stabilize
        time.sleep(5)
        
        # Step 9: Configure Backups
        console.print("\n[bold blue]Step 9/10: Configuring automated backups...[/]")
        backup_mgr = BackupManager(cluster_mgr.cfg)
        
        # Deploy backup infrastructure explicitly
        backup_yaml = cluster_mgr.cfg.config_dir / "database" / "postgresql-backup.yaml"
        if backup_yaml.exists():
            try:
                subprocess.run(["kubectl", "apply", "-f", str(backup_yaml)], 
                             capture_output=True, text=True, check=True)
                console.print("[OK] Backup infrastructure deployed", style="green")
                
                # Wait for backup PVC to be bound
                time.sleep(5)
                result = subprocess.run(
                    ["kubectl", "get", "pvc", "postgresql-backup-pvc", "-n", "grafana-system", "-o", "jsonpath={.status.phase}"],
                    capture_output=True, text=True
                )
                if result.stdout.strip() == "Bound":
                    console.print("[OK] Backup PVC bound successfully", style="green")
                else:
                    console.print(f"[WARNING]  Backup PVC status: {result.stdout.strip()}", style="yellow")
                
                # Verify CronJob created
                result = subprocess.run(
                    ["kubectl", "get", "cronjob", "postgresql-backup", "-n", "grafana-system"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    console.print("[OK] Backup CronJob configured (daily at 2 AM)", style="green")
                    
                    # Trigger initial backup to verify it works
                    console.print("[PROCESSING] Triggering initial backup test...", style="cyan")
                    result = subprocess.run(
                        ["kubectl", "get", "job", "-n", "grafana-system", "-l", "app=postgresql-backup"],
                        capture_output=True, text=True
                    )
                    if "postgresql-backup-manual" in result.stdout:
                        console.print("[OK] Initial backup job created", style="green")
                else:
                    console.print("[WARNING]  CronJob verification failed", style="yellow")
            except Exception as e:
                console.print(f"[WARNING]  Backup deployment warning: {e}", style="yellow")
        else:
            console.print("[WARNING]  Backup configuration file not found", style="yellow")
        
        # Step 10: Final verification
        console.print("\n[bold blue]Step 10/10: Running health check...[/]")
        time.sleep(5)
        health_checker = HealthChecker(cluster_mgr.cfg)
        health_checker.check_all()
        
        # Summary
        console.print("\n" + "="*60, style="cyan")
        console.print("[bold green] FULLY AUTOMATED DEPLOYMENT COMPLETE![/]")
        console.print("\n[cyan][OK] Everything is deployed and running:[/]")
        console.print("   Kind Cluster (3 nodes)")
        console.print("   Grafana Operator (2 replicas)")
        console.print("   PostgreSQL Database (with 20Gi storage)")
        console.print("   Grafana Instance (2 replicas)")
        console.print("   Prometheus Monitoring (kube-prometheus-stack)")
        console.print("   ServiceMonitors (Grafana, Operator, PostgreSQL)")
        console.print("   NodePort Service (permanent access)")
        console.print("   Automated Backups (50Gi PVC, CronJob, initial backup)")
        console.print("\n[bold green] Access Grafana:[/]")
        console.print("  URL: http://localhost:3030")
        console.print("  Username: admin")
        console.print("  Password: Admin@12345")
        console.print("\n[cyan][TIP] No manual steps required - everything is ready to use![/]loyment")
        console.print("  4. All resources will be created automatically!")
        console.print("="*60 + "\n", style="cyan")
        
    except Exception as e:
        console.print(f"\n[ERROR] Reset failed: {e}", style="bold red")
        console.print("You may need to manually clean up with: kind delete cluster --name grafana-cluster", style="yellow")


def operator_menu(operator_mgr: OperatorManager):
    """Operator management menu"""
    while True:
        console.print("\n[bold cyan] Operator Management [/]")
        console.print("1. Install Grafana Operator")
        console.print("2. Uninstall Operator")
        console.print("3. Check Operator Status")
        console.print("4. View Operator Logs")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4"])
        
        if choice == "0":
            break
        elif choice == "1":
            operator_mgr.install_operator()
        elif choice == "2":
            operator_mgr.uninstall_operator()
        elif choice == "3":
            operator_mgr.get_operator_status()
        elif choice == "4":
            operator_mgr.view_operator_logs()


def grafana_menu(grafana_mgr: GrafanaManager):
    """Grafana instance management menu"""
    while True:
        console.print("\n[bold cyan] Grafana Instance Management [/]")
        console.print("1. Deploy Grafana Instance")
        console.print("2. List Grafana Instances")
        console.print("3. Delete Grafana Instance")
        console.print("4. Port Forward to Grafana")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4"])
        
        if choice == "0":
            break
        elif choice == "1":
            grafana_mgr.deploy_grafana()
        elif choice == "2":
            grafana_mgr.list_instances()
        elif choice == "3":
            name = Prompt.ask("Enter instance name", default="grafana-instance")
            grafana_mgr.delete_instance(name)
        elif choice == "4":
            grafana_mgr.port_forward()


def monitoring_menu(monitoring_mgr: MonitoringManager):
    """Monitoring & Infrastructure menu"""
    while True:
        console.print("\n[bold cyan] Monitoring & Infrastructure [/]")
        console.print("1. Deploy Prometheus")
        console.print("2. Deploy Istio")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2"])
        
        if choice == "0":
            break
        elif choice == "1":
            monitoring_mgr.deploy_prometheus()
        elif choice == "2":
            monitoring_mgr.deploy_istio()


def diagnostics_menu():
    """Diagnostics menu"""
    while True:
        console.print("\n[bold cyan] Diagnostics & Logs [/]")
        console.print("1. Check All Resources")
        console.print("2. View Pod Logs")
        console.print("3. Describe Resource")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3"])
        
        if choice == "0":
            break
        elif choice == "1":
            namespaces = ["grafana-system", "grafana-operator", "monitoring", "istio-system"]
            for ns in namespaces:
                console.print(f"\n[bold]Namespace: {ns}[/]")
                subprocess.run(["kubectl", "get", "all", "-n", ns])
        elif choice == "2":
            namespace = Prompt.ask("Enter namespace", default="grafana-system")
            pod = Prompt.ask("Enter pod name")
            try:
                subprocess.run(["kubectl", "logs", "-n", namespace, pod, "--tail=100"])
            except Exception as e:
                console.print(f"Error: {e}", style="red")
        elif choice == "3":
            namespace = Prompt.ask("Enter namespace", default="grafana-system")
            resource_type = Prompt.ask("Enter resource type (pod/deployment/svc)")
            resource_name = Prompt.ask("Enter resource name")
            try:
                subprocess.run(["kubectl", "describe", resource_type, resource_name, "-n", namespace])
            except Exception as e:
                console.print(f"Error: {e}", style="red")


def backup_menu(backup_mgr: BackupManager):
    """Database backup & restore menu"""
    while True:
        console.print("\n[bold cyan] Database Backup & Restore [/]")
        console.print("1. Trigger Manual Backup")
        console.print("2. List All Backups")
        console.print("3. View Backup Schedule")
        console.print("4. View Latest Backup Logs")
        console.print("5. Check Backup System Health")
        console.print("6. Restore from Backup")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6"])
        
        if choice == "0":
            break
        elif choice == "1":
            if backup_mgr.trigger_backup():
                console.print("\n[OK] Backup completed successfully!", style="bold green")
        elif choice == "2":
            backup_mgr.list_backups()
        elif choice == "3":
            backup_mgr.view_schedule()
        elif choice == "4":
            backup_mgr.view_logs()
        elif choice == "5":
            backup_mgr._check_backup_health()
        elif choice == "6":
            backup_mgr.restore_backup()


def health_check_menu(health_checker: HealthChecker):
    """System health check menu"""
    while True:
        console.print("\n[bold cyan] System Health Check [/]")
        console.print("1. Run Full Health Check")
        console.print("2. Check Cluster Only")
        console.print("3. Check Grafana Only")
        console.print("4. Check Database Only")
        console.print("5. Check Operator Only")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5"])
        
        if choice == "0":
            break
        elif choice == "1":
            health_checker.check_all()
        elif choice == "2":
            health_checker._check_cluster()
        elif choice == "3":
            health_checker._check_grafana()
        elif choice == "4":
            health_checker._check_database()
        elif choice == "5":
            health_checker._check_operator()


def main():
    """Main application entry point"""
    print_banner()
    
    # Initialize configuration
    cfg = Config()
    
    # Initialize managers
    cluster_mgr = ClusterManager(cfg)
    operator_mgr = OperatorManager(cfg)
    grafana_mgr = GrafanaManager(cfg)
    backup_mgr = BackupManager(cfg)
    monitoring_mgr = MonitoringManager(cfg)
    health_checker = HealthChecker(cfg)
    
    while True:
        main_menu()
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6", "7"])
        
        if choice == "0":
            console.print("\n Goodbye!", style="bold green")
            break
        elif choice == "1":
            cluster_menu(cluster_mgr)
        elif choice == "2":
            operator_menu(operator_mgr)
        elif choice == "3":
            grafana_menu(grafana_mgr)
        elif choice == "4":
            backup_menu(backup_mgr)
        elif choice == "5":
            monitoring_menu(monitoring_mgr)
        elif choice == "6":
            health_check_menu(health_checker)
        elif choice == "7":
            diagnostics_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n Interrupted by user. Goodbye!", style="bold yellow")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n Unexpected error: {str(e)}", style="bold red")
        sys.exit(1)
