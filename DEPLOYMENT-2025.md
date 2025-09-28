# Deployment Guide 2025

This guide covers modern deployment strategies for the MCP DuckDuckGo Search plugin, implementing 2025 best practices for container orchestration, security, and monitoring.

## 🐳 Container Deployment Options

### Production Deployment (Distroless)

**Recommended for maximum security:**

```bash
# Build distroless production image
docker build --target production -t mcp-duckduckgo:distroless .

# Run with security best practices
docker run -d \
  --name mcp-duckduckgo \
  --restart unless-stopped \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=100m \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --user nonroot \
  --health-cmd="python -c 'import httpx; httpx.get(\"http://localhost:3000/health\")'" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  -p 3000:3000 \
  -e MCP_PORT=3000 \
  mcp-duckduckgo:distroless
```

### Development Deployment (Slim)

**For compatibility requirements:**

```bash
# Build slim production image
docker build --target production-slim -t mcp-duckduckgo:slim .

# Run with health checks
docker run -d \
  --name mcp-duckduckgo-slim \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:3000/health || exit 1" \
  --health-interval=30s \
  -p 3000:3000 \
  mcp-duckduckgo:slim
```

## ☸️ Kubernetes Deployment

### Production Manifest

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-duckduckgo
  labels:
    app: mcp-duckduckgo
    version: "0.1.1"
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-duckduckgo
  template:
    metadata:
      labels:
        app: mcp-duckduckgo
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "3000"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532  # nonroot user in distroless
        fsGroup: 65532
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: mcp-duckduckgo
        image: ghcr.io/gianlucamazza/mcp-duckduckgo:latest
        ports:
        - containerPort: 3000
          name: http
        env:
        - name: MCP_PORT
          value: "3000"
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir:
          sizeLimit: 100Mi
      nodeSelector:
        kubernetes.io/arch: amd64  # or arm64 for ARM nodes
      topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: topology.kubernetes.io/zone
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app: mcp-duckduckgo
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-duckduckgo-service
  labels:
    app: mcp-duckduckgo
spec:
  selector:
    app: mcp-duckduckgo
  ports:
  - port: 80
    targetPort: 3000
    protocol: TCP
    name: http
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-duckduckgo-netpol
spec:
  podSelector:
    matchLabels:
      app: mcp-duckduckgo
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress-nginx
    ports:
    - protocol: TCP
      port: 3000
  egress:
  - to: []  # Allow all outbound (for web searches)
    ports:
    - protocol: TCP
      port: 80
    - protocol: TCP
      port: 443
    - protocol: UDP
      port: 53  # DNS
```

### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-duckduckgo-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-duckduckgo
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
```

## 🔍 Monitoring and Observability

### Prometheus Integration

```yaml
# servicemonitor.yaml (for Prometheus Operator)
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mcp-duckduckgo-metrics
  labels:
    app: mcp-duckduckgo
spec:
  selector:
    matchLabels:
      app: mcp-duckduckgo
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
    scrapeTimeout: 10s
```

### Grafana Dashboard

**Key Metrics to Monitor:**
```json
{
  "dashboard": {
    "title": "MCP DuckDuckGo Search - 2025 Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(mcp_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(mcp_requests_successful[5m]) / rate(mcp_requests_total[5m]) * 100",
            "legendFormat": "Success %"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

```yaml
# alerts.yaml
groups:
- name: mcp-duckduckgo
  rules:
  - alert: MCPHighErrorRate
    expr: rate(mcp_requests_failed[5m]) / rate(mcp_requests_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"

  - alert: MCPHighResponseTime
    expr: histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m])) > 10
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }}s"

  - alert: MCPPodCrashLooping
    expr: rate(kube_pod_container_status_restarts_total{pod=~"mcp-duckduckgo-.*"}[5m]) > 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Pod is crash looping"
      description: "Pod {{ $labels.pod }} is restarting frequently"
```

## 🚀 Cloud Platform Deployment

### AWS ECS (Fargate)

```yaml
# ecs-task-definition.yaml
family: mcp-duckduckgo
networkMode: awsvpc
requiresCompatibilities:
  - FARGATE
cpu: 256
memory: 512
executionRoleArn: arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole
taskRoleArn: arn:aws:iam::ACCOUNT:role/ecsTaskRole
containerDefinitions:
  - name: mcp-duckduckgo
    image: ghcr.io/gianlucamazza/mcp-duckduckgo:latest
    portMappings:
      - containerPort: 3000
        protocol: tcp
    environment:
      - name: MCP_PORT
        value: "3000"
    healthCheck:
      command:
        - CMD-SHELL
        - "python -c 'import httpx; httpx.get(\"http://localhost:3000/health\")'"
      interval: 30
      timeout: 5
      retries: 3
      startPeriod: 60
    logConfiguration:
      logDriver: awslogs
      options:
        awslogs-group: /ecs/mcp-duckduckgo
        awslogs-region: us-east-1
        awslogs-stream-prefix: ecs
```

### Google Cloud Run

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: mcp-duckduckgo
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 100
      timeoutSeconds: 300
      containers:
      - image: ghcr.io/gianlucamazza/mcp-duckduckgo:latest
        ports:
        - containerPort: 3000
        env:
        - name: MCP_PORT
          value: "3000"
        resources:
          limits:
            cpu: 1000m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
        startupProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 0
          periodSeconds: 1
          failureThreshold: 30
```

### Azure Container Instances

```yaml
# azure-container-instance.yaml
apiVersion: '2019-12-01'
location: eastus
properties:
  containers:
  - name: mcp-duckduckgo
    properties:
      image: ghcr.io/gianlucamazza/mcp-duckduckgo:latest
      ports:
      - port: 3000
        protocol: TCP
      environmentVariables:
      - name: MCP_PORT
        value: '3000'
      resources:
        requests:
          cpu: 0.5
          memoryInGb: 0.5
      livenessProbe:
        httpGet:
          path: /health
          port: 3000
        initialDelaySeconds: 30
        periodSeconds: 10
  osType: Linux
  restartPolicy: Always
  ipAddress:
    type: Public
    ports:
    - protocol: TCP
      port: 3000
```

## 🔒 Security Deployment Considerations

### 1. Network Security

**Ingress Configuration:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-duckduckgo-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - mcp-search.yourdomain.com
    secretName: mcp-duckduckgo-tls
  rules:
  - host: mcp-search.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-duckduckgo-service
            port:
              number: 80
```

### 2. Secrets Management

**Using Kubernetes Secrets:**
```bash
# Create secret for sensitive configuration
kubectl create secret generic mcp-config \
  --from-literal=api-key=your-api-key \
  --from-literal=webhook-secret=your-webhook-secret
```

**Using HashiCorp Vault:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-duckduckgo
  annotations:
    vault.hashicorp.com/role: "mcp-role"
```

### 3. RBAC Configuration

```yaml
# rbac.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-duckduckgo
  namespace: default
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: mcp-duckduckgo-role
rules:
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: mcp-duckduckgo-binding
subjects:
- kind: ServiceAccount
  name: mcp-duckduckgo
  namespace: default
roleRef:
  kind: ClusterRole
  name: mcp-duckduckgo-role
  apiGroup: rbac.authorization.k8s.io
```

## 📊 Performance Optimization

### 1. Resource Sizing Guidelines

**Small Scale (< 1000 requests/hour):**
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

**Medium Scale (1000-10000 requests/hour):**
```yaml
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

**Large Scale (> 10000 requests/hour):**
```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

### 2. Caching Strategy

**Redis Integration (Future Enhancement):**
```yaml
# redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

## 🛠️ Troubleshooting

### Common Issues

**1. Container Won't Start:**
```bash
# Check logs
kubectl logs deployment/mcp-duckduckgo

# Check events
kubectl describe pod <pod-name>

# Exec into container (if running)
kubectl exec -it <pod-name> -- /bin/sh  # Note: not available in distroless
```

**2. Health Check Failures:**
```bash
# Test health endpoint directly
kubectl port-forward service/mcp-duckduckgo-service 3000:80
curl http://localhost:3000/health
```

**3. Performance Issues:**
```bash
# Check resource usage
kubectl top pods -l app=mcp-duckduckgo

# Get performance metrics
curl http://localhost:3000/metrics
```

### Debug Mode Deployment

```yaml
# For debugging, use the development target
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-duckduckgo-debug
spec:
  template:
    spec:
      containers:
      - name: mcp-duckduckgo
        image: mcp-duckduckgo:development
        env:
        - name: LOG_LEVEL
          value: "DEBUG"
        - name: MCP_PORT
          value: "3000"
```

---

**For deployment support:**
- Check the GitHub Issues for common deployment problems
- Review monitoring dashboards for performance insights
- Consult the SECURITY-2025.md document for security best practices