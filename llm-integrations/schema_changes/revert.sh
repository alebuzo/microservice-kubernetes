#!/usr/bin/env bash
# Revert one of the 3 controlled schema changes, restoring the affected
# Deployment to THIS PROJECT's own baseline image — NOT necessarily the
# original public ewolff image:
#   itemid-rename  -> catalog -> docker.io/ewolff/microservice-kubernetes-demo-catalog:latest
#                     (Catalog was never otherwise modified by this project,
#                     so its baseline IS the original public image.)
#   price-nested   -> catalog -> docker.io/ewolff/microservice-kubernetes-demo-catalog:latest
#   payment-method -> order   -> microservice-kubernetes-demo-order:local
#                     (Order's baseline for this project is the LOCAL image
#                     built in order-item-validation-fix/order-json-endpoint,
#                     which already includes item validation + the /orders
#                     endpoint. Reverting to the original public order image
#                     here would silently lose those features.)
#
# Usage (from llm-integrations/):
#   ./schema_changes/revert.sh <itemid-rename|price-nested|payment-method>

set -euo pipefail

declare -A SERVICE_FOR=(
  [itemid-rename]=catalog
  [price-nested]=catalog
  [payment-method]=order
)

declare -A BASELINE_IMAGE_FOR=(
  [itemid-rename]="docker.io/ewolff/microservice-kubernetes-demo-catalog:latest"
  [price-nested]="docker.io/ewolff/microservice-kubernetes-demo-catalog:latest"
  [payment-method]="microservice-kubernetes-demo-order:local"
)

declare -A PULL_POLICY_FOR=(
  [itemid-rename]="IfNotPresent"
  [price-nested]="IfNotPresent"
  [payment-method]="Never"
)

usage() {
  echo "Usage: $0 <itemid-rename|price-nested|payment-method>" >&2
  exit 1
}

variant="${1:-}"
[[ -n "$variant" && -n "${SERVICE_FOR[$variant]:-}" ]] || usage

service="${SERVICE_FOR[$variant]}"
image="${BASELINE_IMAGE_FOR[$variant]}"
pull_policy="${PULL_POLICY_FOR[$variant]}"

echo "== Reverting '$service' to this project's baseline image ($image) =="

if [[ "$pull_policy" == "Never" ]]; then
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "ERROR: $image not found locally. Rebuild it first (see plan.md's" >&2
    echo "order-json-endpoint progress entry for the exact commands)." >&2
    exit 1
  fi

  echo "-- Re-importing $image into the K8s node's containerd (in case it"
  echo "   was evicted since it was last imported)"
  docker save "$image" -o /tmp/schema-change-revert-image.tar
  mapfile -t before_debug_pods < <(kubectl get pods -o name | grep node-debugger || true)
  (kubectl debug node/desktop-control-plane -it --image=busybox --profile=sysadmin \
    -- chroot /host sh -c "sleep 300" >/tmp/schema-change-revert-debug.log 2>&1 &)
  sleep 5
  debug_pod=""
  for _ in $(seq 1 10); do
    while IFS= read -r pod_name; do
      [[ -z "$pod_name" ]] && continue
      is_new=true
      for existing in "${before_debug_pods[@]:-}"; do
        [[ "$pod_name" == "$existing" ]] && is_new=false && break
      done
      if $is_new; then
        debug_pod="${pod_name#pod/}"
        break
      fi
    done < <(kubectl get pods -o name | grep node-debugger || true)
    [[ -n "$debug_pod" ]] && break
    sleep 2
  done
  if [[ -z "$debug_pod" ]]; then
    echo "ERROR: could not find the new node-debugger pod. Check 'kubectl get pods'." >&2
    exit 1
  fi
  kubectl wait --for=condition=Ready "pod/$debug_pod" --timeout=60s
  kubectl cp /tmp/schema-change-revert-image.tar "$debug_pod:/host/tmp/schema-change-revert-image.tar"
  kubectl exec "$debug_pod" -- chroot /host sh -c "ctr -n k8s.io images import /tmp/schema-change-revert-image.tar"
  kubectl delete pod "$debug_pod" --wait=false >/dev/null
  rm -f /tmp/schema-change-revert-image.tar
fi

kubectl patch deployment "$service" --type=json -p \
  "[{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/image\",\"value\":\"$image\"},
    {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/imagePullPolicy\",\"value\":\"$pull_policy\"}]"
kubectl rollout status "deployment/$service" --timeout=60s

echo "== Done. '$service' is back on this project's baseline ($image) =="
