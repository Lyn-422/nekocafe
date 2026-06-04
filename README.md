# NekoCafé DevOps - 猫咪主题餐饮预约平台

## 项目简介

NekoCafé 是一个猫咪主题餐饮预约平台。本项目是实验三 DevOps 流水线与容器化部署的 PoC 实现，包含两个核心微服务：

- **Member Service (会员服务)** — 用户注册/登录认证、会员等级与积分管理
- **Reservation Service (预约服务)** — 桌位可用性查询、预约生命周期管理

## 架构概览

```
┌─────────────────┐     ┌─────────────────────┐
│  Member Service │     │  Reservation Service │
│     :8080       │     │       :8081          │
└───────┬─────────┘     └──────────┬──────────┘
        │                          │
        │    ┌──────────────┐      │
        └────┤  MySQL 8.0   ├──────┘
             │   :3306      │
             └──────────────┘
```

## 技术栈

| 层面 | 技术 |
|------|------|
| 语言 | Python 3.12 |
| Web 框架 | FastAPI |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 7 |
| 消息队列 | RabbitMQ |
| 容器化 | Docker + Docker Compose |
| 编排 | Kubernetes + Helm |
| CI/CD | GitHub Actions |
| 可观测性 | OpenTelemetry + Prometheus + Grafana + Loki + Tempo |
| 安全扫描 | Trivy + CodeQL |

## 快速开始

### 前置条件

- Docker Desktop 24+
- Python 3.12+
- Make (可选，Windows 可用 Git Bash)

### 本地一键起栈

```bash
# 克隆项目
git clone <repo-url> && cd nekocafe

# 复制环境变量
cp .env.example .env

# 启动全部服务
docker compose up -d

# 验证服务
curl http://localhost:8080/health   # Member Service
curl http://localhost:8081/health   # Reservation Service

# 查看日志
docker compose logs -f
```

### 30 分钟内完全复现指南

| 步骤 | 命令 | 预期时间 |
|------|------|---------|
| 1. 克隆仓库 | `git clone <repo-url> && cd nekocafe` | 1 min |
| 2. 安装依赖 | `docker compose build` | 5 min |
| 3. 启动服务 | `docker compose up -d` | 2 min |
| 4. 数据库初始化 | `docker compose exec member python init_db.py` | 1 min |
| 5. 健康检查 | `curl localhost:8080/health && curl localhost:8081/health` | 1 min |
| 6. 创建测试用户 | `curl -X POST localhost:8080/api/v1/auth/register -H 'Content-Type: application/json' -d '{"phone":"13800138000","smsCode":"123456","agreeToTerms":true}'` | 1 min |
| 7. 创建预约 | `curl -X POST localhost:8081/api/v1/reservations -H 'Content-Type: application/json' -H 'Authorization: Bearer <token>' -d '{...}'` | 1 min |

## 项目结构

```
nekocafe/
├── README.md                    # 本文件
├── docker-compose.yml           # 本地一键起栈
├── Makefile                     # 常用命令快捷方式
├── .editorconfig                # 编辑器统一配置
├── .env.example                 # 环境变量模板
├── services/
│   ├── reservation/             # 预约服务
│   │   ├── Dockerfile           #   多阶段构建
│   │   ├── src/
│   │   │   ├── main.py          #   FastAPI 应用
│   │   │   ├── models.py        #   数据模型
│   │   │   ├── routes.py        #   路由
│   │   │   ├── config.py        #   配置
│   │   │   └── requirements.txt #   依赖
│   │   └── tests/
│   │       └── test_api.py      #   单元测试
│   └── member/                  # 会员服务
│       ├── Dockerfile
│       ├── src/
│       │   ├── main.py
│       │   ├── models.py
│       │   ├── routes.py
│       │   ├── auth.py          #   JWT 认证
│       │   ├── config.py
│       │   └── requirements.txt
│       └── tests/
│           └── test_api.py
├── infra/
│   ├── helm/nekocafe/           # Helm Chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   ├── values-dev.yaml
│   │   ├── values-staging.yaml
│   │   ├── values-prod.yaml
│   │   └── templates/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       ├── ingress.yaml
│   │       ├── hpa.yaml
│   │       ├── pdb.yaml
│   │       ├── configmap.yaml
│   │       ├── secret.yaml
│   │       └── servicemonitor.yaml
│   ├── k8s-manifests/           # 裸 K8s YAML (备选)
│   └── observability/           # 可观测性配置
│       ├── grafana/dashboards/
│       ├── grafana/datasources/
│       ├── prometheus/prometheus.yml
│       ├── prometheus/alerts.yml
│       ├── loki/loki-config.yaml
│       └── opentelemetry/otel-config.yaml
├── .github/workflows/
│   ├── ci.yml                   # CI 流水线
│   └── cd.yml                   # CD 流水线
└── docs/
    ├── runbook.md               # 运维手册
    └── rollback.sh              # 一键回滚脚本
```

## 环境地址

| 环境 | URL |
|------|-----|
| dev (本地) | http://localhost:8080 (Member) / http://localhost:8081 (Reservation) |
| staging | https://api-staging.nekocafe.com |
| prod | https://api.nekocafe.com |

## 监控与告警

- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- 告警通知: 飞书群 + PagerDuty

## 贡献指南

1. 从 `main` 分支创建 `feature/xxx` 分支
2. 本地通过 `docker compose up -d` 验证
3. 推送并创建 PR
4. CI 流水线必须全部通过
5. 至少 1 人 Code Review 通过后合并

## License

本项目为北京林业大学《软件工程》课程实验项目。
