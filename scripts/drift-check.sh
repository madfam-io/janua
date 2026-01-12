#!/bin/bash
set -euo pipefail

# Janua Configuration Drift Detection
# Compares expected (Git) vs actual (cluster) Kubernetes state
# Usage: ./drift-check.sh <expected.yaml> <current.yaml>
#
# Exit codes:
#   0 - No drift detected
#   1 - Drift detected (differences found)
#   2 - Script error (missing args, file not found, etc.)

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <expected.yaml> <current.yaml>" >&2
    exit 2
fi

EXPECTED="$1"
CURRENT="$2"

if [[ ! -f "$EXPECTED" ]] || [[ ! -f "$CURRENT" ]]; then
    echo "Error: Input files not found" >&2
    exit 2
fi

DRIFT_FOUND=0

echo "=== Janua Configuration Drift Check ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Expected: $EXPECTED"
echo "Current:  $CURRENT"
echo ""

# ============================================================================
# Deployment Image Comparison
# ============================================================================
echo "## Deployment Images"
echo ""

for DEPLOY in janua-api janua-dashboard janua-admin janua-docs janua-website; do
    # Extract image from expected manifests
    EXPECTED_IMAGE=$(grep -A 100 "name: $DEPLOY" "$EXPECTED" 2>/dev/null | \
        grep -m1 "image:" | awk '{print $2}' | tr -d '"' || echo "")

    # Extract image from current cluster state
    CURRENT_IMAGE=$(grep -A 100 "name: $DEPLOY" "$CURRENT" 2>/dev/null | \
        grep -m1 "image:" | awk '{print $2}' | tr -d '"' || echo "")

    # Handle cases where deployment might not exist
    if [[ -z "$EXPECTED_IMAGE" ]] && [[ -z "$CURRENT_IMAGE" ]]; then
        continue  # Deployment doesn't exist in either
    fi

    if [[ -z "$EXPECTED_IMAGE" ]] && [[ -n "$CURRENT_IMAGE" ]]; then
        echo "WARNING: $DEPLOY exists in cluster but not in Git manifests"
        echo "   Cluster: $CURRENT_IMAGE"
        DRIFT_FOUND=1
        continue
    fi

    if [[ -n "$EXPECTED_IMAGE" ]] && [[ -z "$CURRENT_IMAGE" ]]; then
        echo "WARNING: $DEPLOY defined in Git but not running in cluster"
        echo "   Expected: $EXPECTED_IMAGE"
        DRIFT_FOUND=1
        continue
    fi

    if [[ "$EXPECTED_IMAGE" != "$CURRENT_IMAGE" ]]; then
        echo "DRIFT: $DEPLOY image mismatch"
        echo "   Expected: $EXPECTED_IMAGE"
        echo "   Actual:   $CURRENT_IMAGE"
        DRIFT_FOUND=1
    else
        echo "OK: $DEPLOY - $CURRENT_IMAGE"
    fi
done

echo ""

# ============================================================================
# Replica Count Comparison
# ============================================================================
echo "## Replica Counts"
echo ""

for DEPLOY in janua-api janua-dashboard janua-admin; do
    # Extract replicas from expected
    EXPECTED_REPLICAS=$(grep -A 20 "name: $DEPLOY" "$EXPECTED" 2>/dev/null | \
        grep -m1 "replicas:" | awk '{print $2}' || echo "1")

    # Extract replicas from current
    CURRENT_REPLICAS=$(grep -A 20 "name: $DEPLOY" "$CURRENT" 2>/dev/null | \
        grep -m1 "replicas:" | awk '{print $2}' || echo "")

    if [[ -z "$CURRENT_REPLICAS" ]]; then
        continue
    fi

    if [[ "$EXPECTED_REPLICAS" != "$CURRENT_REPLICAS" ]]; then
        echo "DRIFT: $DEPLOY replicas"
        echo "   Expected: $EXPECTED_REPLICAS"
        echo "   Actual:   $CURRENT_REPLICAS"
        DRIFT_FOUND=1
    fi
done

echo ""

# ============================================================================
# Summary
# ============================================================================
echo "=== Drift Check Complete ==="
if [[ $DRIFT_FOUND -eq 1 ]]; then
    echo "STATUS: DRIFT DETECTED"
    echo ""
    echo "Resolution options:"
    echo "  1. If cluster state is correct: Update k8s/ manifests in Git"
    echo "  2. If Git state is correct: Re-apply manifests with kubectl apply -k k8s/overlays/prod"
    exit 1
else
    echo "STATUS: NO DRIFT - Configuration in sync"
    exit 0
fi
