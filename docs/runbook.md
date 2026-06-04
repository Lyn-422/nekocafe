# NekoCafé 运维手册 (Runbook)

## 常见操作

### 服务启动

```bash
# 本地开发
docker compose up -d

# K8s 部署
helm upgrade --install nekocafe infra/helm/nekocafe \
  --namespace nekocafe-prod \
  --values infra/helm/nekocafe/values-prod.yaml
```

### 健康检查

```bash
# 本地
curl http://localhost:8080/health
curl http://localhost:8081/health

# K8s
kubectl port-forward svc/member-service 8080:8080 -n nekocafe-prod
curl http://localhost:8080/health
```

### 查看日志

```bash
# Docker Compose
docker compose logs -f member

# K8s
kubectl logs -f deployment/member-service -n nekocafe-prod

# Grafana Loki (结构化日志检索)
# 访问 http://localhost:3000 → Explore → Loki
# 查询: {service="member-service"} |= "ERROR"
```

### 扩容/缩容

```bash
# 手动扩容
kubectl scale deployment/member-service --replicas=5 -n nekocafe-prod

# 修改 HPA
kubectl edit hpa member-hpa -n nekocafe-prod
```

### 回滚

```bash
# 一键回滚
bash docs/rollback.sh member
bash docs/rollback.sh reservation

# 或 Helm 回滚
helm rollback nekocafe -n nekocafe-prod
```

---

## 故障处理

### 场景1: 错误率飙升

**症状**: Grafana Error Rate 面板显示 > 1%

**排查步骤**:
1. 检查 Grafana Dashboard → Error Rate 面板
2. 查看 Tempo 链路追踪，定位慢请求/错误请求的 Span
3. 查看 Loki 日志: `{service="reservation-service"} |= "ERROR"`
4. 检查数据库连接: `kubectl exec -it deployment/mysql -- mysql -u root -p`
5. 检查 Redis: `kubectl exec -it deployment/redis -- redis-cli PING`

**应急处理**:
```bash
# 如果是新版本导致
bash docs/rollback.sh reservation

# 如果是数据库问题
kubectl rollout restart deployment/mysql -n nekocafe-prod
```

### 场景2: P95 延迟过高

**症状**: Grafana P99 Latency > 400ms

**排查步骤**:
1. 查看是否有慢查询: Loki `|= "duration" | json | duration > 500`
2. 检查资源使用: `kubectl top pods -n nekocafe-prod`
3. 检查 HPA 是否生效: `kubectl get hpa -n nekocafe-prod`

### 场景3: 服务不可用

**症状**: `/health` 返回非 200

**排查步骤**:
1. 查看 Pod 状态: `kubectl get pods -n nekocafe-prod`
2. 查看事件: `kubectl describe pod <pod-name> -n nekocafe-prod`
3. 检查资源: `kubectl top nodes`

---

## 链路追踪使用指南

1. 从应用日志中获取 `traceId`
2. 打开 Grafana → Explore → Tempo
3. 输入 traceId 查看完整调用链
4. 定位耗时最长的 Span
5. 3分钟内定位问题根因

## 数据库初始化

```bash
# 创建数据库
docker compose exec mysql mysql -u root -p${MYSQL_ROOT_PASSWORD} -e "
  CREATE DATABASE IF NOT EXISTS nekocafe_member;
  CREATE DATABASE IF NOT EXISTS nekocafe_reservation;
"
```

## 备份与恢复

```bash
# 备份
kubectl exec deployment/mysql -n nekocafe-prod -- \
  mysqldump -u root -p"${MYSQL_ROOT_PASSWORD}" --all-databases > backup.sql

# 恢复
kubectl exec -i deployment/mysql -n nekocafe-prod -- \
  mysql -u root -p"${MYSQL_ROOT_PASSWORD}" < backup.sql
```
