#!/bin/bash
# PostgreSQL Backup Management Script for Grafana Database

set -e

NAMESPACE="grafana-system"
BACKUP_PVC="postgresql-backup-pvc"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════╗"
    echo "║   PostgreSQL Backup Manager for Grafana           ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_menu() {
    echo -e "${YELLOW}Backup Management Options:${NC}"
    echo "1. Trigger Manual Backup"
    echo "2. List All Backups"
    echo "3. Restore from Backup"
    echo "4. View Backup Schedule"
    echo "5. View Latest Backup Job Logs"
    echo "6. Delete Old Backups (>7 days)"
    echo "0. Exit"
    echo
}

trigger_backup() {
    echo -e "${BLUE}🔄 Triggering manual backup...${NC}"
    
    # Delete existing manual job if present
    kubectl delete job postgresql-backup-manual -n ${NAMESPACE} 2>/dev/null || true
    sleep 2
    
    # Create new backup job
    kubectl create job postgresql-backup-manual-$(date +%s) \
        --from=cronjob/postgresql-backup -n ${NAMESPACE}
    
    echo -e "${GREEN}✓ Backup job started!${NC}"
    echo "Waiting for job to complete..."
    
    sleep 5
    kubectl wait --for=condition=complete --timeout=300s \
        job/postgresql-backup-manual-$(date +%s) -n ${NAMESPACE} 2>/dev/null || \
        echo -e "${YELLOW}⚠ Job still running. Check logs with option 5${NC}"
}

list_backups() {
    echo -e "${BLUE}📋 Listing all backups...${NC}"
    
    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=postgresql-backup --sort-by=.metadata.creationTimestamp --no-headers | tail -1 | awk '{print $1}')
    
    if [ -z "$POD_NAME" ]; then
        echo -e "${YELLOW}⚠ No backup pod found. Creating temporary pod...${NC}"
        kubectl run backup-list-temp --image=postgres:16-alpine \
            --restart=Never -n ${NAMESPACE} \
            --overrides='
{
  "spec": {
    "containers": [{
      "name": "backup-list",
      "image": "postgres:16-alpine",
      "command": ["sleep", "60"],
      "volumeMounts": [{
        "name": "backup-storage",
        "mountPath": "/backups"
      }]
    }],
    "volumes": [{
      "name": "backup-storage",
      "persistentVolumeClaim": {"claimName": "'${BACKUP_PVC}'"}
    }]
  }
}' 2>/dev/null || true
        
        sleep 5
        POD_NAME="backup-list-temp"
    fi
    
    echo
    kubectl exec -n ${NAMESPACE} ${POD_NAME} -- ls -lh /backups/ 2>/dev/null || \
        echo -e "${YELLOW}⚠ No backups found or unable to access backup storage${NC}"
    
    # Cleanup temp pod
    kubectl delete pod backup-list-temp -n ${NAMESPACE} 2>/dev/null || true
}

restore_backup() {
    echo -e "${BLUE}📋 Available backups:${NC}"
    list_backups
    echo
    echo -e "${RED}⚠ WARNING: Restore will DELETE all current Grafana data!${NC}"
    echo -n "Enter backup filename to restore (or 'cancel' to abort): "
    read backup_file
    
    if [ "$backup_file" = "cancel" ] || [ -z "$backup_file" ]; then
        echo "Restore cancelled"
        return
    fi
    
    echo
    echo -e "${RED}Are you ABSOLUTELY sure? Type 'YES' to confirm: ${NC}"
    read confirmation
    
    if [ "$confirmation" != "YES" ]; then
        echo "Restore cancelled"
        return
    fi
    
    echo -e "${BLUE}🔄 Starting restore...${NC}"
    
    # Create restore pod
    kubectl run postgresql-restore --image=postgres:16-alpine \
        --restart=Never -n ${NAMESPACE} \
        --env="POSTGRES_DB=$(kubectl get secret postgresql-secret -n ${NAMESPACE} -o jsonpath='{.data.POSTGRES_DB}' | base64 -d)" \
        --env="POSTGRES_USER=$(kubectl get secret postgresql-secret -n ${NAMESPACE} -o jsonpath='{.data.POSTGRES_USER}' | base64 -d)" \
        --env="POSTGRES_PASSWORD=$(kubectl get secret postgresql-secret -n ${NAMESPACE} -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d)" \
        --overrides='
{
  "spec": {
    "containers": [{
      "name": "restore",
      "image": "postgres:16-alpine",
      "command": ["/bin/bash", "/scripts/restore.sh", "'${backup_file}'"],
      "env": [
        {"name": "POSTGRES_DB", "valueFrom": {"secretKeyRef": {"name": "postgresql-secret", "key": "POSTGRES_DB"}}},
        {"name": "POSTGRES_USER", "valueFrom": {"secretKeyRef": {"name": "postgresql-secret", "key": "POSTGRES_USER"}}},
        {"name": "POSTGRES_PASSWORD", "valueFrom": {"secretKeyRef": {"name": "postgresql-secret", "key": "POSTGRES_PASSWORD"}}}
      ],
      "volumeMounts": [
        {"name": "backup-storage", "mountPath": "/backups"},
        {"name": "backup-scripts", "mountPath": "/scripts"}
      ]
    }],
    "volumes": [
      {"name": "backup-storage", "persistentVolumeClaim": {"claimName": "'${BACKUP_PVC}'"}},
      {"name": "backup-scripts", "configMap": {"name": "postgresql-backup-scripts", "defaultMode": 493}}
    ]
  }
}'
    
    echo "Waiting for restore to complete..."
    kubectl wait --for=condition=ready --timeout=300s pod/postgresql-restore -n ${NAMESPACE} 2>/dev/null || true
    kubectl logs -f postgresql-restore -n ${NAMESPACE}
    
    # Cleanup
    kubectl delete pod postgresql-restore -n ${NAMESPACE} 2>/dev/null || true
    
    echo -e "${GREEN}✓ Restore completed!${NC}"
    echo "Restart Grafana pods for changes to take effect:"
    echo "kubectl rollout restart deployment grafana-instance-deployment -n ${NAMESPACE}"
}

view_schedule() {
    echo -e "${BLUE}📅 Backup Schedule:${NC}"
    kubectl get cronjob postgresql-backup -n ${NAMESPACE} -o wide
    echo
    echo -e "${BLUE}Recent Backup Jobs:${NC}"
    kubectl get jobs -n ${NAMESPACE} -l app=postgresql-backup --sort-by=.metadata.creationTimestamp
}

view_logs() {
    echo -e "${BLUE}📝 Latest Backup Job Logs:${NC}"
    
    JOB=$(kubectl get jobs -n ${NAMESPACE} -l app=postgresql-backup --sort-by=.metadata.creationTimestamp --no-headers | tail -1 | awk '{print $1}')
    
    if [ -z "$JOB" ]; then
        echo -e "${YELLOW}⚠ No backup jobs found${NC}"
        return
    fi
    
    echo "Job: $JOB"
    echo
    kubectl logs -n ${NAMESPACE} job/$JOB --tail=100
}

delete_old_backups() {
    echo -e "${YELLOW}🗑️  Deleting backups older than 7 days...${NC}"
    
    # This will be done automatically by the backup script during next run
    # For manual cleanup, we can run the same logic
    
    POD_NAME=$(kubectl get pods -n ${NAMESPACE} -l app=postgresql-backup --sort-by=.metadata.creationTimestamp --no-headers | tail -1 | awk '{print $1}')
    
    if [ -z "$POD_NAME" ]; then
        echo -e "${YELLOW}⚠ No backup pod found to perform cleanup${NC}"
        return
    fi
    
    kubectl exec -n ${NAMESPACE} ${POD_NAME} -- \
        find /backups -name "grafana_backup_*.sql.gz" -type f -mtime +7 -delete 2>/dev/null || \
        echo -e "${YELLOW}⚠ Unable to delete old backups${NC}"
    
    echo -e "${GREEN}✓ Cleanup completed${NC}"
}

main() {
    print_header
    
    while true; do
        show_menu
        read -p "Select option: " choice
        echo
        
        case $choice in
            1) trigger_backup ;;
            2) list_backups ;;
            3) restore_backup ;;
            4) view_schedule ;;
            5) view_logs ;;
            6) delete_old_backups ;;
            0) echo "Goodbye!"; exit 0 ;;
            *) echo -e "${RED}Invalid option${NC}" ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
        echo
    done
}

main
