#!/bin/bash
# ============================================================================
# OpenViking Server Startup Script
# ============================================================================
# Manages the OpenViking server process for Hermes Agent integration.
#
# Usage:
#   ./scripts/start-openviking.sh [start|stop|restart|status]
#
# ============================================================================

set -e

# Configuration
OPENVIKING_CONFIG_DIR="${OPENVIKING_CONFIG_DIR:-$HOME/.openviking}"
OPENVIKING_PORT="${OPENVIKING_PORT:-1933}"
OPENVIKING_HOST="${OPENVIKING_HOST:-127.0.0.1}"
PID_FILE="$OPENVIKING_CONFIG_DIR/server.pid"
LOG_FILE="$OPENVIKING_CONFIG_DIR/server.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# ============================================================================
# Helper Functions
# ============================================================================

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

check_server_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is dead
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

check_port_available() {
    if command -v lsof >/dev/null 2>&1; then
        if lsof -Pi :$OPENVIKING_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            return 1
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -an | grep -q ":$OPENVIKING_PORT.*LISTEN"; then
            return 1
        fi
    fi
    return 0
}

# ============================================================================
# Commands
# ============================================================================

cmd_start() {
    echo "Starting OpenViking server..."

    # Create config directory
    mkdir -p "$OPENVIKING_CONFIG_DIR"

    # Check if already running
    if check_server_running; then
        local pid=$(cat "$PID_FILE")
        print_warning "Server already running (PID: $pid)"
        return 0
    fi

    # Check if port is in use
    if ! check_port_available; then
        print_error "Port $OPENVIKING_PORT is already in use"
        echo "Stop the conflicting process or change OPENVIKING_PORT"
        return 1
    fi

    # Check if openviking-server is installed
    if ! command -v openviking-server >/dev/null 2>&1; then
        print_error "openviking-server not found in PATH"
        echo "Install OpenViking: pip install openviking"
        return 1
    fi

    # Start server in background
    nohup openviking-server \
        --host "$OPENVIKING_HOST" \
        --port "$OPENVIKING_PORT" \
        > "$LOG_FILE" 2>&1 &

    local pid=$!
    echo $pid > "$PID_FILE"

    # Wait for server to start
    echo -n "Waiting for server to start"
    for i in {1..30}; do
        if curl -s "http://$OPENVIKING_HOST:$OPENVIKING_PORT/health" >/dev/null 2>&1; then
            echo ""
            print_success "Server started successfully (PID: $pid)"
            echo "Endpoint: http://$OPENVIKING_HOST:$OPENVIKING_PORT"
            echo "Logs: $LOG_FILE"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    echo ""
    print_error "Server failed to start within 30 seconds"
    echo "Check logs: tail -f $LOG_FILE"

    # Clean up PID file if server didn't start
    if [ -f "$PID_FILE" ]; then
        local check_pid=$(cat "$PID_FILE")
        if ! ps -p "$check_pid" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
        fi
    fi

    return 1
}

cmd_stop() {
    echo "Stopping OpenViking server..."

    if ! check_server_running; then
        print_warning "Server is not running"
        return 0
    fi

    local pid=$(cat "$PID_FILE")
    echo "Stopping process $pid..."

    # Send SIGTERM
    kill -TERM "$pid" 2>/dev/null || true

    # Wait for graceful shutdown
    for i in {1..10}; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
            print_success "Server stopped"
            return 0
        fi
        sleep 1
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        print_warning "Forcing shutdown..."
        kill -KILL "$pid" 2>/dev/null || true
        rm -f "$PID_FILE"
        print_success "Server stopped (forced)"
    fi
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

cmd_status() {
    if check_server_running; then
        local pid=$(cat "$PID_FILE")
        print_success "Server is running (PID: $pid)"

        # Try to get version and stats
        local endpoint="http://$OPENVIKING_HOST:$OPENVIKING_PORT"
        echo "Endpoint: $endpoint"

        if command -v curl >/dev/null 2>&1; then
            local health=$(curl -s "$endpoint/health" 2>/dev/null)
            if [ -n "$health" ]; then
                echo "Health: OK"
            fi

            local version=$(curl -s "$endpoint/api/v1/version" 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
            if [ -n "$version" ]; then
                echo "Version: $version"
            fi
        fi

        echo "Logs: $LOG_FILE"
    else
        print_warning "Server is not running"
        if [ -f "$LOG_FILE" ]; then
            echo "Last 5 log lines:"
            tail -5 "$LOG_FILE"
        fi
    fi
}

cmd_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        print_error "Log file not found: $LOG_FILE"
    fi
}

# ============================================================================
# Main
# ============================================================================

main() {
    local command="${1:-status}"

    case "$command" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        restart)
            cmd_restart
            ;;
        status)
            cmd_status
            ;;
        logs)
            cmd_logs
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|logs}"
            echo ""
            echo "Commands:"
            echo "  start    - Start OpenViking server"
            echo "  stop     - Stop OpenViking server"
            echo "  restart  - Restart OpenViking server"
            echo "  status   - Show server status"
            echo "  logs     - Tail server logs"
            exit 1
            ;;
    esac
}

main "$@"
