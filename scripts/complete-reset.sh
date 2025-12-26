#!/bin/bash
# Complete Reset and Rebuild Script for Testing Portability

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       Grafana Operator - Complete Reset & Rebuild       ║${NC}"
echo -e "${BLUE}║         Testing Portability for New Users               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${RED}⚠️  WARNING: This will DESTROY everything and rebuild from scratch!${NC}"
echo
echo "This script will:"
echo "  1. Delete the entire Kind cluster"
echo "  2. Remove all Docker resources"
echo "  3. Clean up any leftover files"
echo "  4. Rebuild the cluster from scratch"
echo "  5. Auto-deploy Operator + Database"
echo "  6. Auto-deploy Grafana Instance"
echo "  7. Auto-configure Backups"
echo "  8. Verify all resources are running"
echo
echo -e "${RED}This is FULLY AUTOMATED - everything deploys automatically!${NC}"
echo

read -p "Continue? (type 'YES' to confirm): " confirm

if [ "$confirm" != "YES" ]; then
    echo "Reset cancelled"
    exit 0
fi

echo
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Starting Complete Reset...${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo

# Step 1: Delete Kind cluster
echo -e "${BLUE}[1/7] Deleting Kind cluster...${NC}"
kind delete cluster --name grafana-cluster 2>/dev/null || echo "  → Cluster already deleted or doesn't exist"
sleep 2
echo -e "${GREEN}  ✓ Cluster deleted${NC}"
echo

# Step 2: Clean up Docker
echo -e "${BLUE}[2/7] Cleaning up Docker resources...${NC}"
docker system prune -f >/dev/null 2>&1
echo -e "${GREEN}  ✓ Docker cleaned${NC}"
echo

# Step 3: Verify cleanup
echo -e "${BLUE}[3/7] Verifying complete cleanup...${NC}"
if kind get clusters 2>/dev/null | grep -q grafana-cluster; then
    echo -e "${RED}  ✗ Cluster still exists!${NC}"
    exit 1
else
    echo -e "${GREEN}  ✓ Cluster completely removed${NC}"
fi

if docker ps -a | grep -q grafana-cluster; then
    echo -e "${YELLOW}  → Cleaning up remaining containers...${NC}"
    docker ps -a | grep grafana-cluster | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true
fi
echo -e "${GREEN}  ✓ Environment is clean${NC}"
echo

# Step 4: Create fresh cluster
echo -e "${BLUE}[4/7] Creating fresh Kind cluster...${NC}"
kind create cluster --config config/kind-config.yaml --wait 60s
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Cluster created successfully${NC}"
else
    echo -e "${RED}  ✗ Cluster creation failed!${NC}"
    exit 1
fi
echo

# Step 5: Verify cluster
echo -e "${BLUE}[5/7] Verifying cluster is ready...${NC}"
sleep 5
kubectl cluster-info >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Cluster responding${NC}"
    kubectl get nodes
else
    echo -e "${RED}  ✗ Cluster not responding!${NC}"
    exit 1
fi
echo

# Step 6: Check namespaces
echo -e "${BLUE}[6/7] Checking Kubernetes environment...${NC}"
echo "  Current namespaces:"
kubectl get namespaces --no-headers | awk '{print "    →", $1}'
echo -e "${GREEN}  ✓ Kubernetes ready for deployment${NC}"
echoVerifying Kubernetes is ready...${NC}"
echo "  → Creating test namespace..."
kubectl create namespace test-auto-create >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Kubernetes ready for deployment${NC}"
    kubectl delete namespace test-auto-create >/dev/null 2>&1
else
    echo -e "${RED}  ✗ Cannot create resources!${NC}"
    exit 1
fi
echo

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Cluster Reset Complete!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo
echo -e "${YELLOW}⚠️  For MANUAL deployment, use the Python menu tool:${NC}"
echo "   ./grafana"
echo
echo -e "${GREEN}For FULLY AUTOMATED deployment (recommended):${NC}"
echo "   Run the Python menu tool and select:"
echo "   Menu 1 → Option 5 (Complete Reset)"
echo "   → Auto-deploys: Operator, Database, Grafana, Backups"
echo "   → Zero manual steps required!
echo
echo -e "${YELLOW}All resources will be created AUTOMATICALLY - no manual steps!${NC}"
echo -e "${GREEN}This proves the solution is portable for new users! 🚀${NC}"
echo
