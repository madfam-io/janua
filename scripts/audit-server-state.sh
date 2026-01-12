#!/bin/bash
set -euo pipefail

# Janua Server State Audit Script
# Run this on the Hetzner server to capture current K8s state for comparison
# Usage: ./audit-server-state.sh [output-dir]

OUTPUT_DIR="${1:-/tmp/janua-audit-$(date +%Y%m%d-%H%M%S)}"
NAMESPACE="${NAMESPACE:-janua}"

mkdir -p "$OUTPUT_DIR"

echo "=== Janua Server State Audit ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Namespace: $NAMESPACE"
echo "Output:    $OUTPUT_DIR"
echo ""

# ============================================================================
# Kubernetes Resources
# ============================================================================
echo "Capturing Kubernetes resources..."

# All resources
kubectl get all -n "$NAMESPACE" -o yaml > "$OUTPUT_DIR/k8s-all.yaml" 2>/dev/null || \
    echo "Warning: Could not get all resources"

# Deployments (detailed)
kubectl get deployments -n "$NAMESPACE" -o yaml > "$OUTPUT_DIR/k8s-deployments.yaml" 2>/dev/null || \
    echo "Warning: Could not get deployments"

# Services
kubectl get services -n "$NAMESPACE" -o yaml > "$OUTPUT_DIR/k8s-services.yaml" 2>/dev/null || \
    echo "Warning: Could not get services"

# ConfigMaps (without sensitive data)
kubectl get configmaps -n "$NAMESPACE" -o yaml > "$OUTPUT_DIR/k8s-configmaps.yaml" 2>/dev/null || \
    echo "Warning: Could not get configmaps"

# Secrets (metadata only - no values!)
kubectl get secrets -n "$NAMESPACE" -o custom-columns='NAME:.metadata.name,TYPE:.type,AGE:.metadata.creationTimestamp' \
    > "$OUTPUT_DIR/k8s-secrets-metadata.txt" 2>/dev/null || \
    echo "Warning: Could not get secrets metadata"

# ============================================================================
# Running Images
# ============================================================================
echo "Capturing running images..."

kubectl get pods -n "$NAMESPACE" \
    -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}' \
    | sort -u > "$OUTPUT_DIR/running-images.txt" 2>/dev/null || \
    echo "Warning: Could not get pod images"

# ============================================================================
# Pod Status
# ============================================================================
echo "Capturing pod status..."

kubectl get pods -n "$NAMESPACE" -o wide > "$OUTPUT_DIR/pod-status.txt" 2>/dev/null || \
    echo "Warning: Could not get pod status"

# ============================================================================
# Events (last 1 hour)
# ============================================================================
echo "Capturing recent events..."

kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' 2>/dev/null | \
    tail -50 > "$OUTPUT_DIR/recent-events.txt" || \
    echo "Warning: Could not get events"

# ============================================================================
# Resource Versions
# ============================================================================
echo "Capturing resource versions..."

kubectl get deployments -n "$NAMESPACE" \
    -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image,REPLICAS:.spec.replicas,READY:.status.readyReplicas' \
    > "$OUTPUT_DIR/deployment-versions.txt" 2>/dev/null || \
    echo "Warning: Could not get deployment versions"

# ============================================================================
# Summary Report
# ============================================================================
echo ""
echo "Creating summary report..."

cat > "$OUTPUT_DIR/SUMMARY.md" << EOF
# Janua Server Audit Report

**Date**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Namespace**: $NAMESPACE
**Server**: $(hostname 2>/dev/null || echo "unknown")

## Running Images

\`\`\`
$(cat "$OUTPUT_DIR/running-images.txt" 2>/dev/null || echo "No images captured")
\`\`\`

## Deployment Status

\`\`\`
$(cat "$OUTPUT_DIR/deployment-versions.txt" 2>/dev/null || echo "No deployments captured")
\`\`\`

## Pod Status

\`\`\`
$(cat "$OUTPUT_DIR/pod-status.txt" 2>/dev/null || echo "No pods captured")
\`\`\`

## Files Generated

- k8s-all.yaml - All Kubernetes resources
- k8s-deployments.yaml - Deployment specifications
- k8s-services.yaml - Service specifications
- k8s-configmaps.yaml - ConfigMap specifications
- k8s-secrets-metadata.txt - Secret names (no values)
- running-images.txt - Container images in use
- pod-status.txt - Current pod status
- recent-events.txt - Recent namespace events
- deployment-versions.txt - Deployment image versions

## Next Steps

1. Compare these outputs with Git manifests in \`k8s/\` directory
2. Document any discrepancies
3. Either update Git to match server or re-deploy from Git
EOF

echo ""
echo "=== Audit Complete ==="
echo ""
echo "Summary saved to: $OUTPUT_DIR/SUMMARY.md"
echo ""
cat "$OUTPUT_DIR/SUMMARY.md"
