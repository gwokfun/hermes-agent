#!/bin/bash
# ============================================================================
# OpenViking Setup Script for Hermes Agent
# ============================================================================
# This script helps users set up OpenViking memory plugin integration with
# Hermes Agent. It guides through installation, configuration, and testing.
#
# Usage:
#   ./scripts/setup-openviking.sh
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
OPENVIKING_CONFIG_DIR="$HOME/.openviking"
OPENVIKING_DEFAULT_PORT=1933

# ============================================================================
# Helper Functions
# ============================================================================

print_banner() {
    echo ""
    echo -e "${MAGENTA}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}${BOLD}║                                                          ║${NC}"
    echo -e "${MAGENTA}${BOLD}║          OpenViking Memory Plugin Setup                 ║${NC}"
    echo -e "${MAGENTA}${BOLD}║          for Hermes Agent                               ║${NC}"
    echo -e "${MAGENTA}${BOLD}║                                                          ║${NC}"
    echo -e "${MAGENTA}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}${BOLD}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

prompt_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local response

    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi

    read -p "$prompt" response
    response=${response:-$default}

    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# Installation Steps
# ============================================================================

check_prerequisites() {
    print_step "Checking prerequisites..."

    local missing_deps=()

    # Check Python
    if ! check_command python3; then
        missing_deps+=("python3")
    fi

    # Check pip
    if ! check_command pip3; then
        missing_deps+=("pip3")
    fi

    # Check git
    if ! check_command git; then
        missing_deps+=("git")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo "Please install them first."
        exit 1
    fi

    print_success "All prerequisites satisfied"
}

install_openviking() {
    print_step "Installing OpenViking..."

    if python3 -c "import openviking" 2>/dev/null; then
        print_warning "OpenViking already installed"
        if prompt_yes_no "Reinstall OpenViking?"; then
            pip3 install --upgrade openviking
            print_success "OpenViking updated"
        else
            print_success "Using existing OpenViking installation"
        fi
    else
        echo "Installing OpenViking from PyPI..."
        pip3 install openviking
        print_success "OpenViking installed successfully"
    fi
}

configure_openviking() {
    print_step "Configuring OpenViking..."

    # Create config directory
    mkdir -p "$OPENVIKING_CONFIG_DIR"

    # Prompt for configuration
    echo ""
    echo "OpenViking Configuration:"
    echo "------------------------"

    # Endpoint
    read -p "OpenViking server endpoint [http://127.0.0.1:$OPENVIKING_DEFAULT_PORT]: " endpoint
    endpoint=${endpoint:-"http://127.0.0.1:$OPENVIKING_DEFAULT_PORT"}

    # API Key (optional)
    read -p "API key (leave blank for local dev mode): " api_key

    # Account
    read -p "Account/tenant ID [default]: " account
    account=${account:-"default"}

    # User
    read -p "User ID [default]: " user
    user=${user:-"default"}

    # Agent
    read -p "Agent ID [hermes]: " agent
    agent=${agent:-"hermes"}

    # Write to Hermes .env
    local env_file="$HERMES_HOME/.env"

    if [ ! -f "$env_file" ]; then
        touch "$env_file"
    fi

    # Remove old OpenViking config if exists
    sed -i.bak '/^OPENVIKING_/d' "$env_file" 2>/dev/null || true

    # Add new config
    {
        echo ""
        echo "# OpenViking Memory Plugin Configuration"
        echo "OPENVIKING_ENDPOINT=$endpoint"
        [ -n "$api_key" ] && echo "OPENVIKING_API_KEY=$api_key"
        echo "OPENVIKING_ACCOUNT=$account"
        echo "OPENVIKING_USER=$user"
        echo "OPENVIKING_AGENT=$agent"
    } >> "$env_file"

    print_success "Configuration saved to $env_file"
}

configure_embedding_models() {
    print_step "Configuring embedding and VLM models..."

    echo ""
    echo "Model Configuration:"
    echo "-------------------"

    # Embedding model
    echo ""
    echo "Embedding models:"
    echo "  1) BAAI/bge-small-zh-v1.5 (Chinese, 24M params, recommended)"
    echo "  2) BAAI/bge-base-zh-v1.5 (Chinese, 102M params)"
    echo "  3) BAAI/bge-large-zh-v1.5 (Chinese, 326M params)"
    echo "  4) sentence-transformers/all-MiniLM-L6-v2 (English, 22M params)"
    echo "  5) Custom model"
    read -p "Select embedding model [1]: " emb_choice
    emb_choice=${emb_choice:-1}

    case "$emb_choice" in
        1) embedding_model="BAAI/bge-small-zh-v1.5" ;;
        2) embedding_model="BAAI/bge-base-zh-v1.5" ;;
        3) embedding_model="BAAI/bge-large-zh-v1.5" ;;
        4) embedding_model="sentence-transformers/all-MiniLM-L6-v2" ;;
        5)
            read -p "Enter custom embedding model: " embedding_model
            ;;
        *) embedding_model="BAAI/bge-small-zh-v1.5" ;;
    esac

    # Device for embedding
    read -p "Device for embedding [cpu/cuda/mps]: " emb_device
    emb_device=${emb_device:-cpu}

    # VLM model
    echo ""
    echo "Vision Language Models:"
    echo "  1) Qwen/Qwen2-VL-2B-Instruct (2B params, recommended)"
    echo "  2) Qwen/Qwen2-VL-7B-Instruct (7B params)"
    echo "  3) Custom model"
    read -p "Select VLM model [1]: " vlm_choice
    vlm_choice=${vlm_choice:-1}

    case "$vlm_choice" in
        1) vlm_model="Qwen/Qwen2-VL-2B-Instruct" ;;
        2) vlm_model="Qwen/Qwen2-VL-7B-Instruct" ;;
        3)
            read -p "Enter custom VLM model: " vlm_model
            ;;
        *) vlm_model="Qwen/Qwen2-VL-2B-Instruct" ;;
    esac

    # Device for VLM
    read -p "Device for VLM [cpu/cuda/mps]: " vlm_device
    vlm_device=${vlm_device:-cpu}

    # Write to .env
    local env_file="$HERMES_HOME/.env"

    {
        echo "OPENVIKING_EMBEDDING_MODEL=$embedding_model"
        echo "OPENVIKING_EMBEDDING_DEVICE=$emb_device"
        echo "OPENVIKING_VLM_MODEL=$vlm_model"
        echo "OPENVIKING_VLM_DEVICE=$vlm_device"
    } >> "$env_file"

    print_success "Model configuration saved"
}

start_openviking_server() {
    print_step "Starting OpenViking server..."

    # Check if already running
    if curl -s "http://127.0.0.1:$OPENVIKING_DEFAULT_PORT/health" >/dev/null 2>&1; then
        print_success "OpenViking server already running"
        return 0
    fi

    if prompt_yes_no "Start OpenViking server now?" "y"; then
        echo "Starting server in background..."
        nohup openviking-server > "$OPENVIKING_CONFIG_DIR/server.log" 2>&1 &
        local server_pid=$!
        echo $server_pid > "$OPENVIKING_CONFIG_DIR/server.pid"

        # Wait for server to start
        echo -n "Waiting for server to start"
        for i in {1..30}; do
            if curl -s "http://127.0.0.1:$OPENVIKING_DEFAULT_PORT/health" >/dev/null 2>&1; then
                echo ""
                print_success "OpenViking server started (PID: $server_pid)"
                return 0
            fi
            echo -n "."
            sleep 1
        done

        echo ""
        print_warning "Server startup timeout. Check logs at $OPENVIKING_CONFIG_DIR/server.log"
    else
        print_warning "Server not started. Start manually with: openviking-server"
    fi
}

activate_hermes_plugin() {
    print_step "Activating OpenViking plugin in Hermes..."

    # Check if hermes command exists
    if ! check_command hermes; then
        print_warning "Hermes command not found in PATH"
        echo "Please run this after Hermes Agent installation is complete."
        return 1
    fi

    # Run hermes memory setup
    if prompt_yes_no "Configure Hermes to use OpenViking memory?" "y"; then
        echo "Running: hermes memory setup"
        echo "Please select 'openviking' from the menu..."
        sleep 2
        hermes memory setup || true
    fi
}

test_connection() {
    print_step "Testing connection..."

    local endpoint=$(grep OPENVIKING_ENDPOINT "$HERMES_HOME/.env" 2>/dev/null | cut -d'=' -f2)
    endpoint=${endpoint:-"http://127.0.0.1:$OPENVIKING_DEFAULT_PORT"}

    echo "Testing endpoint: $endpoint"

    if curl -s -f "$endpoint/health" >/dev/null 2>&1; then
        print_success "Connection successful!"

        # Try to get version info
        local version=$(curl -s "$endpoint/api/v1/version" 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$version" ]; then
            echo "  Server version: $version"
        fi
    else
        print_error "Cannot connect to OpenViking server"
        echo "  Make sure the server is running: openviking-server"
        echo "  Check logs at: $OPENVIKING_CONFIG_DIR/server.log"
    fi
}

print_summary() {
    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║                                                          ║${NC}"
    echo -e "${GREEN}${BOLD}║          Setup Complete!                                 ║${NC}"
    echo -e "${GREEN}${BOLD}║                                                          ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start Hermes Agent:"
    echo "   $ hermes"
    echo ""
    echo "2. Verify OpenViking is active:"
    echo "   $ hermes memory status"
    echo ""
    echo "3. Test memory features:"
    echo "   - Use 'viking_search' to search knowledge base"
    echo "   - Use 'viking_remember' to store facts"
    echo "   - Use 'viking_add_resource' to ingest documents"
    echo ""
    echo "Documentation:"
    echo "  - Setup guide: docs/openviking-setup.md"
    echo "  - Plugin README: plugins/memory/openviking/README.md"
    echo ""
    echo "Server management:"
    echo "  - Start: openviking-server"
    echo "  - Stop: kill \$(cat ~/.openviking/server.pid)"
    echo "  - Logs: tail -f ~/.openviking/server.log"
    echo ""
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    print_banner

    check_prerequisites
    echo ""

    install_openviking
    echo ""

    configure_openviking
    echo ""

    if prompt_yes_no "Configure embedding and VLM models?" "y"; then
        configure_embedding_models
        echo ""
    fi

    start_openviking_server
    echo ""

    test_connection
    echo ""

    activate_hermes_plugin
    echo ""

    print_summary
}

# Run main function
main "$@"
