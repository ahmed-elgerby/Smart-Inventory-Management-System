# Monitoring

This folder contains the first local monitoring setup for the Smart Inventory project.

## Services

- Prometheus: http://localhost:19091
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:19093
- cAdvisor: http://localhost:8081
- Node Exporter: http://localhost:19100
- PostgreSQL exporter: http://localhost:19187

Grafana default login:

- Username: `admin`
- Password: `admin`

## Current Metrics

Prometheus scrapes the backend service at:

```text
backend:5000/metrics
alert-service:5001/metrics
reporting-service:5002/metrics
```

The backend currently exposes:

- `inventory_total_items`
- `inventory_low_stock`
- `inventory_total_users`
- `inventory_total_locations`

The alert-service exposes:

- `alert_service_active_alerts`

The reporting-service exposes:

- `reporting_service_total_inventory_items`
- `reporting_service_total_inventory_value`

cAdvisor exposes container metrics such as:

- `container_cpu_usage_seconds_total`
- `container_memory_working_set_bytes`
- `container_network_receive_bytes_total`
- `container_network_transmit_bytes_total`
- `container_fs_usage_bytes`

PostgreSQL exporter exposes database metrics such as:

- `pg_up`
- `pg_stat_database_numbackends`
- `pg_database_size_bytes`
- `pg_stat_database_xact_commit`
- `pg_stat_database_xact_rollback`
- `pg_stat_database_deadlocks`

Node exporter exposes host system metrics such as:

- `node_cpu_seconds_total`
- `node_memory_MemTotal_bytes`
- `node_memory_MemAvailable_bytes`
- `node_disk_io_time_seconds_total`
- `node_network_receive_bytes_total`
- `node_network_transmit_bytes_total`

## Alertmanager

Alertmanager is configured with Slack notifications. Update the webhook URL in `monitoring/helm/kube-prometheus-stack-values.yaml` to enable notifications.

- Add `/metrics` endpoints to `alert-service` and `reporting-service`.
- Add Alertmanager for infrastructure alerts.
- Add PostgreSQL metrics with `postgres-exporter`.
- Deploy the monitoring stack to Kubernetes with Helm.

## Kubernetes With Helm

Install the Prometheus/Grafana/Alertmanager stack:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -f monitoring/helm/kube-prometheus-stack-values.yaml
```

Apply this project's monitoring resources:

```bash
kubectl apply -k monitoring
```

This creates:

- `ServiceMonitor` for the backend `/metrics` endpoint.
- PostgreSQL exporter Deployment, Service, `ServiceMonitor`, and alert rules.
- `PrometheusRule` alerts for backend downtime and low-stock items.
- Grafana dashboard ConfigMap from `monitoring/grafana/dashboards/smart-inventory-overview.json`.
- `/grafana` ingress route for the Grafana UI.

The Helm release name is expected to be `monitoring`, because the Grafana ingress points to the `monitoring-grafana` service and the Prometheus custom resources use `release: monitoring`.
