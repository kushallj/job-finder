#!/usr/bin/env bash
set -e

# docker_manage.sh — Unified CLI for Managing Multi-Service Docker Architecture

COLOR_CYAN='\033[0;36m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_NC='\033[0m'

function print_header() {
    echo -e "${COLOR_CYAN}================================================================${COLOR_NC}"
    echo -e "${COLOR_CYAN} 🐳 Job Finder & Ghost Copilot — Microservices Docker CLI${COLOR_NC}"
    echo -e "${COLOR_CYAN}================================================================${COLOR_NC}"
}

function usage() {
    print_header
    echo "Usage: ./scripts/docker_manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build              Build all microservice Docker images"
    echo "  up                 Start all services in detached production mode"
    echo "  dev                Start all services with development hot-reload"
    echo "  down               Stop and remove all running containers"
    echo "  logs [service]     Follow logs for all or a specific service"
    echo "  ps                 Show running container status and health"
    echo "  clean              Prune dangling images and build caches"
    echo ""
}

CMD=${1:-"help"}

case "$CMD" in
    build)
        print_header
        echo -e "${COLOR_GREEN}🔨 Building all microservice images...${COLOR_NC}"
        docker compose build
        ;;
    up)
        print_header
        echo -e "${COLOR_GREEN}🚀 Starting microservices fleet in production mode...${COLOR_NC}"
        docker compose up -d
        echo -e "${COLOR_GREEN}✅ Fleet launched! Checking container health...${COLOR_NC}"
        docker compose ps
        ;;
    dev)
        print_header
        echo -e "${COLOR_YELLOW}⚡ Starting in Development Hot-Reload mode...${COLOR_NC}"
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up
        ;;
    down)
        print_header
        echo -e "${COLOR_YELLOW}🛑 Stopping microservices...${COLOR_NC}"
        docker compose down
        ;;
    logs)
        SERVICE=${2:-""}
        docker compose logs -f $SERVICE
        ;;
    ps)
        docker compose ps
        ;;
    clean)
        echo -e "${COLOR_YELLOW}🧹 Cleaning unused docker objects...${COLOR_NC}"
        docker system prune -f
        ;;
    *)
        usage
        ;;
esac
