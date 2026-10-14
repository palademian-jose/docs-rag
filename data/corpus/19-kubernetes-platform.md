# Kubernetes Platform

Owner: Platform

## Clusters

Larkspur runs four Kubernetes clusters on managed cloud Kubernetes: `dev`,
`staging`, `prod-eu` and `prod-us`. Production clusters run three control
plane replicas across availability zones. Cluster versions track the upstream
release minus one minor version and are upgraded quarterly.

## Workload requirements

Every deployment MUST declare:

- CPU and memory requests and limits. Memory limit equals memory request;
  CPU limit is at most four times the CPU request.
- A readiness probe and a liveness probe on distinct endpoints
  (`/ready` and `/live`).
- A `PodDisruptionBudget` allowing at most one unavailable replica.
- Pod anti-affinity across zones for tier-1 services.
- Resource labels: `app.kubernetes.io/name`, `larkspur.com/team`,
  `larkspur.com/tier`.

The `kube-policy` admission controller rejects workloads missing any of
these.

## Replicas and autoscaling

Production services run at least three replicas. Horizontal Pod Autoscalers
target 60% CPU utilisation with a maximum of 50 replicas unless Platform
approves more. Vertical autoscaling is used only in recommendation mode.

## Helm and manifests

Services are packaged with the shared `larkspur-service` Helm chart; custom
charts need Platform approval. Values files live in `infra/values/<env>/`
in the service directory. Raw manifests are not applied by hand to any
cluster; `kubectl apply` against production is blocked by RBAC except for
the Platform break-glass role.

## Networking

Services communicate over the mesh (Linkerd) with mutual TLS. Ingress is
handled by the shared gateway; services do not create their own
`LoadBalancer` resources. Network policies default to deny; each service
declares the services it calls in `service.yaml` and the policy is generated.

## Node pools

Clusters have three node pools: `general` (on-demand, default), `spot`
(preemptible, for batch and stateless workers that tolerate restarts) and
`memory` (high-memory nodes for the search indexers). Workloads select a
pool with the `larkspur.com/pool` node selector; the default is `general`.

## Access

Engineers get read-only `kubectl` access to `dev` and `staging` by default.
Production read access requires completing the 60-day onboarding milestone.
Write access to production is held only by the Platform break-glass role and
is audited.
