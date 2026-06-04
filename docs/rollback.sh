#!/bin/bash
# NekoCafé 一键回滚脚本
# 用法: bash docs/rollback.sh <service_name>
# 示例: bash docs/rollback.sh member
#       bash docs/rollback.sh reservation

set -e

SERVICE="${1:?请指定服务名 (member 或 reservation)}"
NAMESPACE="${NAMESPACE:-nekocafe-prod}"
TIMEOUT="${TIMEOUT:-120s}"

echo "=========================================="
echo "  NekoCafé Rollback Script"
echo "  Service: $SERVICE"
echo "  Namespace: $NAMESPACE"
echo "  Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 记录回滚前状态
echo "[1/4] 记录回滚前状态..."
kubectl get deployment "$SERVICE-service" -n "$NAMESPACE" -o yaml > "/tmp/rollback-$SERVICE-$(date +%s).yaml"

CURRENT_REVISION=$(kubectl rollout history deployment/"$SERVICE-service" -n "$NAMESPACE" | tail -1 | awk '{print $1}')
echo "  当前版本: $CURRENT_REVISION"

# 执行回滚
echo "[2/4] 执行 Helm Rollback..."
if helm rollback "$SERVICE" --namespace="$NAMESPACE" 2>/dev/null; then
  echo "  Helm rollback 成功"
else
  echo "  Helm rollback 失败，尝试 kubectl rollout undo..."
  kubectl rollout undo deployment/"$SERVICE-service" -n "$NAMESPACE"
fi

# 等待回滚完成
echo "[3/4] 等待回滚完成..."
if kubectl rollout status deployment/"$SERVICE-service" -n "$NAMESPACE" --timeout="$TIMEOUT"; then
  echo "  回滚完成"
else
  echo "  WARNING: 回滚超时，请手动检查"
fi

# 验证
echo "[4/4] 验证服务健康..."
sleep 5
HEALTH_CHECK=$(kubectl exec -it deployment/"$SERVICE-service" -n "$NAMESPACE" -- curl -s -o /dev/null -w "%{http_code}" http://localhost:"${PORT:-8080}"/health 2>/dev/null || echo "N/A")
echo "  健康检查: $HEALTH_CHECK"

echo ""
echo "=========================================="
echo "  Rollback completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo "  New revision: $(kubectl rollout history deployment/$SERVICE-service -n $NAMESPACE | tail -1)"
echo "=========================================="
