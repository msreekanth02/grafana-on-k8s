#!/bin/bash
# Backup File Access Helper

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

NAMESPACE="grafana-system"
PVC_NAME="postgresql-backup-pvc"

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Grafana Backup Storage Access Tool        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo

# Get PV name
PV_NAME=$(kubectl get pvc ${PVC_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.volumeName}' 2>/dev/null)

if [ -z "$PV_NAME" ]; then
    echo -e "${YELLOW}⚠️  Backup PVC not found${NC}"
    exit 1
fi

# Get host path
HOST_PATH=$(kubectl get pv ${PV_NAME} -o jsonpath='{.spec.hostPath.path}')

echo -e "${GREEN}📍 Backup Storage Locations:${NC}"
echo
echo "1️⃣  Kubernetes PVC:"
echo "   Name: ${PVC_NAME}"
echo "   Namespace: ${NAMESPACE}"
echo "   Volume: ${PV_NAME}"
echo "   Mount path (in pods): /backups"
echo
echo "2️⃣  Kind Node (Docker):"
echo "   Container: grafana-cluster-control-plane"
echo "   Path: ${HOST_PATH}"
echo

# Show menu
echo -e "${BLUE}Available Actions:${NC}"
echo "1. List all backup files"
echo "2. View backup file details"
echo "3. Copy backup to local machine"
echo "4. Copy backup from local machine"
echo "5. Delete old backups"
echo "6. Access backup directory (shell)"
echo "0. Exit"
echo

read -p "Select action [0-6]: " choice

case $choice in
    1)
        echo -e "\n${GREEN}📋 Listing backup files...${NC}\n"
        docker exec grafana-cluster-control-plane ls -lh ${HOST_PATH}/ | grep -v "^total" || echo "No backups found"
        ;;
    
    2)
        echo
        docker exec grafana-cluster-control-plane ls -1 ${HOST_PATH}/ | grep "grafana_backup_" || echo "No backups found"
        echo
        read -p "Enter backup filename: " filename
        if [ ! -z "$filename" ]; then
            echo -e "\n${GREEN}📊 Backup Details:${NC}\n"
            docker exec grafana-cluster-control-plane ls -lh ${HOST_PATH}/${filename}
            echo
            echo "Content preview:"
            docker exec grafana-cluster-control-plane sh -c "gunzip -c ${HOST_PATH}/${filename} | head -20"
        fi
        ;;
    
    3)
        echo
        docker exec grafana-cluster-control-plane ls -1 ${HOST_PATH}/ | grep "grafana_backup_" || echo "No backups found"
        echo
        read -p "Enter backup filename to copy: " filename
        read -p "Enter local destination path [./]: " dest_path
        dest_path=${dest_path:-.}
        
        if [ ! -z "$filename" ]; then
            echo -e "\n${GREEN}📥 Copying backup to local machine...${NC}"
            docker cp grafana-cluster-control-plane:${HOST_PATH}/${filename} ${dest_path}/
            echo -e "${GREEN}✅ Copied to: ${dest_path}/${filename}${NC}"
            ls -lh ${dest_path}/${filename}
        fi
        ;;
    
    4)
        read -p "Enter local backup file path: " local_file
        if [ -f "$local_file" ]; then
            filename=$(basename "$local_file")
            echo -e "\n${GREEN}📤 Copying backup to cluster...${NC}"
            docker cp "$local_file" grafana-cluster-control-plane:${HOST_PATH}/${filename}
            echo -e "${GREEN}✅ Copied to cluster storage${NC}"
            docker exec grafana-cluster-control-plane ls -lh ${HOST_PATH}/${filename}
        else
            echo -e "${YELLOW}⚠️  File not found: $local_file${NC}"
        fi
        ;;
    
    5)
        echo -e "\n${YELLOW}⚠️  This will delete backups older than 7 days${NC}"
        read -p "Continue? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo -e "${GREEN}🗑️  Deleting old backups...${NC}"
            docker exec grafana-cluster-control-plane find ${HOST_PATH} -name "grafana_backup_*.sql.gz" -type f -mtime +7 -delete
            echo -e "${GREEN}✅ Old backups deleted${NC}"
            echo
            echo "Remaining backups:"
            docker exec grafana-cluster-control-plane ls -lh ${HOST_PATH}/
        fi
        ;;
    
    6)
        echo -e "\n${GREEN}🐚 Opening shell in backup directory...${NC}"
        echo "Type 'exit' to return"
        echo
        docker exec -it grafana-cluster-control-plane sh -c "cd ${HOST_PATH} && sh"
        ;;
    
    0)
        echo "Goodbye!"
        exit 0
        ;;
    
    *)
        echo -e "${YELLOW}Invalid option${NC}"
        ;;
esac

echo
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo
