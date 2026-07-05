#!/usr/bin/env bash
# Apply or revert one of the 3 controlled schema changes (OE1 experiment)
# against the live Kubernetes deployment, so `integration-parity-check` and
# the scenario scripts can be re-run under each variant.
#
# Usage (from llm-integrations/):
#   ./schema_changes/apply.sh   <itemid-rename|price-nested|payment-method>
#   ./schema_changes/revert.sh  <itemid-rename|price-nested|payment-method>
#
# What this does, for EACH service affected by the variant:
#   1. Locally builds the Docker image for the affected microservice with
#      the schema-change patch applied (or checks out the pre-built image
#      tag if it already exists from a prior run of this repo's session).
#   2. Imports that image into the K8s node's containerd (Docker Desktop's
#      K8s cluster uses a separate containerd from the host Docker daemon —
#      see the note in plan.md's `order-json-endpoint` progress entry for
#      why this step is necessary) via a `kubectl debug node` pod + `ctr`.
#   3. Points the corresponding Deployment at the new image tag with
#      `kubectl set image` (imagePullPolicy: Never) and waits for rollout.
#
# Each schema change maps to one or more (service, image, patch) triplets:
#   itemid-rename   -> catalog -> microservice-kubernetes-demo-catalog:schema-itemid-rename
#                      (Catalog: renames the public JSON key "id" -> "id_item")
#                   -> order   -> microservice-kubernetes-demo-order:schema-itemid-rename
#                      (Order: updates its own Catalog client DTO, clients/Item.java,
#                      to deserialize "id_item" instead of "id" — without this,
#                      Order's HTML demo flow, which reads getItemId() from a
#                      fetched Catalog Item, would silently corrupt to 0; Jackson's
#                      FAIL_ON_UNKNOWN_PROPERTIES=false means it does NOT throw.
#                      This keeps the overall system fully functional, matching
#                      the guiding principle that only the *LLM integration layer*
#                      — not the microservices/consumers themselves — should break.)
#   price-nested    -> catalog -> microservice-kubernetes-demo-catalog:schema-price-nested
#                      (Catalog: nests "price" into {amount, currency})
#                   -> order   -> microservice-kubernetes-demo-order:schema-price-nested
#                      (Order: updates its own Catalog client DTO, clients/Item.java,
#                      with an equivalent nested Price class. Without this, Jackson
#                      throws MismatchedInputException while deserializing ANY Item
#                      fetched from Catalog — CatalogClient.getOne()/exists()/price()/
#                      findAll() all deserialize the full Item including "price" — and
#                      since only HttpClientErrorException is caught, this propagated
#                      as an uncaught exception: Order's own POST /orders returned
#                      HTTP 500. This was verified live before the fix. Fixing it keeps
#                      the guiding principle that only the LLM integration layer, not
#                      the microservices themselves, should break.)
#   payment-method  -> order   -> microservice-kubernetes-demo-order:schema-payment-method
#
# `revert.sh` restores this project's own baseline for each affected service
# (for Catalog: the original public image, since Catalog was otherwise
# unmodified; for Order: `microservice-kubernetes-demo-order:local`, which
# already includes item validation + the /orders endpoint — see revert.sh's
# header comment for details).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEMO_DIR="$REPO_ROOT/microservice-kubernetes-demo"

declare -A SERVICES_FOR=(
  [itemid-rename]="catalog order"
  [price-nested]="catalog order"
  [payment-method]="order"
)

declare -A IMAGE_FOR=(
  [itemid-rename:catalog]="microservice-kubernetes-demo-catalog:schema-itemid-rename"
  [itemid-rename:order]="microservice-kubernetes-demo-order:schema-itemid-rename"
  [price-nested:catalog]="microservice-kubernetes-demo-catalog:schema-price-nested"
  [price-nested:order]="microservice-kubernetes-demo-order:schema-price-nested"
  [payment-method:order]="microservice-kubernetes-demo-order:schema-payment-method"
)

declare -A PATCH_FOR=(
  [itemid-rename:catalog]="$SCRIPT_DIR/01-itemid-rename.patch"
  [itemid-rename:order]="$SCRIPT_DIR/01b-itemid-rename-order-client.patch"
  [price-nested:catalog]="$SCRIPT_DIR/02-price-nested.patch"
  [price-nested:order]="$SCRIPT_DIR/02b-price-nested-order-client.patch"
  [payment-method:order]="$SCRIPT_DIR/03-payment-method.patch"
)

usage() {
  echo "Usage: $0 <itemid-rename|price-nested|payment-method>" >&2
  exit 1
}

variant="${1:-}"
[[ -n "$variant" && -n "${SERVICES_FOR[$variant]:-}" ]] || usage

echo "== Applying schema change '$variant' =="

import_image_to_containerd() {
  local image="$1"
  echo "-- Importing $image into the K8s node's containerd"
  docker save "$image" -o /tmp/schema-change-image.tar

  mapfile -t before_debug_pods < <(kubectl get pods -o name | grep node-debugger || true)
  (kubectl debug node/desktop-control-plane -it --image=busybox --profile=sysadmin \
    -- chroot /host sh -c "sleep 300" >/tmp/schema-change-debug.log 2>&1 &)
  sleep 5
  local debug_pod=""
  for _ in $(seq 1 10); do
    while IFS= read -r pod_name; do
      [[ -z "$pod_name" ]] && continue
      local is_new=true
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
  kubectl cp /tmp/schema-change-image.tar "$debug_pod:/host/tmp/schema-change-image.tar"
  kubectl exec "$debug_pod" -- chroot /host sh -c "ctr -n k8s.io images import /tmp/schema-change-image.tar"
  kubectl delete pod "$debug_pod" --wait=false >/dev/null
  rm -f /tmp/schema-change-image.tar
}

for service in ${SERVICES_FOR[$variant]}; do
  image="${IMAGE_FOR[$variant:$service]}"
  patch_file="${PATCH_FOR[$variant:$service]}"
  module_dir="$DEMO_DIR/microservice-kubernetes-demo-$service"

  echo
  echo "-- Service: $service (image: $image)"

  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "-- Image $image not found locally, building it from patch $patch_file"
    ( cd "$DEMO_DIR" && git apply "$patch_file" )
    docker run --rm -v "$DEMO_DIR":/build -w /build maven:3.9-eclipse-temurin-11 \
      mvn -q -pl "microservice-kubernetes-demo-$service" -am package -DskipTests
    docker build -t "$image" "$module_dir"
    ( cd "$DEMO_DIR" && git checkout -- "microservice-kubernetes-demo-$service/" )
  else
    echo "-- Image $image already built, reusing it"
  fi

  import_image_to_containerd "$image"

  echo "-- Pointing deployment/$service at $image (imagePullPolicy: Never)"
  kubectl patch deployment "$service" --type=json -p \
    "[{\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/image\",\"value\":\"$image\"},
      {\"op\":\"replace\",\"path\":\"/spec/template/spec/containers/0/imagePullPolicy\",\"value\":\"Never\"}]"
  kubectl rollout status "deployment/$service" --timeout=60s
done

echo
echo "== Done. Schema variant '$variant' is now applied (services: ${SERVICES_FOR[$variant]}) =="
