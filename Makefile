.PHONY: help up down build test lint clean logs ps

help: ## 显示帮助信息
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## 启动全部服务
	docker compose up -d
	@echo "所有服务已启动"
	@echo "  Member Service:     http://localhost:8080"
	@echo "  Reservation Service: http://localhost:8081"
	@echo "  Grafana:            http://localhost:3000"

down: ## 停止全部服务
	docker compose down

build: ## 构建所有镜像
	docker compose build

restart: ## 重启所有服务
	docker compose restart

logs: ## 查看所有服务日志
	docker compose logs -f

ps: ## 查看服务运行状态
	docker compose ps

test: ## 运行单元测试
	docker compose exec member pytest tests/ -v
	docker compose exec reservation pytest tests/ -v

test-cov: ## 运行测试并生成覆盖率报告
	docker compose exec member pytest tests/ --cov=src --cov-report=term-missing
	docker compose exec reservation pytest tests/ --cov=src --cov-report=term-missing

lint: ## 运行代码检查
	@echo "Running yamllint..."
	yamllint . || true
	@echo "Running hadolint..."
	hadolint services/member/Dockerfile services/reservation/Dockerfile || true

clean: ## 清理所有容器、镜像和卷
	docker compose down -v --rmi all

scan: ## 安全扫描镜像
	trivy image nekocafe-member:latest
	trivy image nekocafe-reservation:latest

health: ## 健康检查
	@echo "=== Member Service ==="
	@curl -s http://localhost:8080/health | python -m json.tool || echo "DOWN"
	@echo "=== Reservation Service ==="
	@curl -s http://localhost:8081/health | python -m json.tool || echo "DOWN"

seed: ## 初始化测试数据
	docker compose exec member python /app/seed.py
	docker compose exec reservation python /app/seed.py

shell-member: ## 进入 Member 容器
	docker compose exec member bash

shell-reservation: ## 进入 Reservation 容器
	docker compose exec reservation bash
