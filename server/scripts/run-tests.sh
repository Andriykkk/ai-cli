#!/bin/bash
# Safe test runner script using Docker

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
}

# Function to build test image
build_test_image() {
    print_status "Building test Docker image..."
    cd "$SERVER_DIR"
    
    if docker build -f Dockerfile.test -t ai-cli-tests:latest .; then
        print_success "Test image built successfully"
    else
        print_error "Failed to build test image"
        exit 1
    fi
}

# Function to run tests
run_tests() {
    local test_type="${1:-all}"
    local verbose="${2:-false}"
    
    print_status "Running $test_type tests in Docker container..."
    
    cd "$SERVER_DIR"
    
    # Build Docker command
    local docker_cmd="docker run --rm"
    
    # Add security options
    docker_cmd="$docker_cmd --security-opt no-new-privileges:true"
    docker_cmd="$docker_cmd --cap-drop ALL --cap-add DAC_OVERRIDE"
    docker_cmd="$docker_cmd --network none"
    docker_cmd="$docker_cmd --read-only"
    docker_cmd="$docker_cmd --tmpfs /tmp:rw,noexec,nosuid,nodev,size=100m"
    docker_cmd="$docker_cmd --user 1000:1000"
    
    # Add resource limits
    docker_cmd="$docker_cmd --memory=512m --cpus=1.0"
    
    # Add name for easy identification
    docker_cmd="$docker_cmd --name ai-cli-test-runner-$$"
    
    # Mount current directory as read-only
    docker_cmd="$docker_cmd -v $SERVER_DIR:/app:ro"
    
    # Add image
    docker_cmd="$docker_cmd ai-cli-tests:latest"
    
    # Add pytest command based on test type
    case "$test_type" in
        "functional")
            docker_cmd="$docker_cmd python -m pytest tests/ -m functional"
            ;;
        "security")
            docker_cmd="$docker_cmd python -m pytest tests/ -m security"
            ;;
        "integration")
            docker_cmd="$docker_cmd python -m pytest tests/ -m integration"
            ;;
        "unit")
            docker_cmd="$docker_cmd python -m pytest tests/ -m unit"
            ;;
        "fast")
            docker_cmd="$docker_cmd python -m pytest tests/ -m 'not slow'"
            ;;
        "all"|*)
            docker_cmd="$docker_cmd python -m pytest tests/"
            ;;
    esac
    
    # Add verbose flag if requested
    if [ "$verbose" = "true" ]; then
        docker_cmd="$docker_cmd -v"
    fi
    
    # Add coverage reporting
    docker_cmd="$docker_cmd --cov=tools --cov-report=term-missing"
    
    print_status "Executing: $docker_cmd"
    
    # Run the tests
    if eval "$docker_cmd"; then
        print_success "Tests completed successfully"
        return 0
    else
        print_error "Tests failed"
        return 1
    fi
}

# Function to clean up Docker resources
cleanup() {
    print_status "Cleaning up Docker resources..."
    
    # Remove any leftover containers
    if docker ps -a --filter "name=ai-cli-test-runner-" --format "{{.Names}}" | grep -q "ai-cli-test-runner-"; then
        docker ps -a --filter "name=ai-cli-test-runner-" --format "{{.Names}}" | xargs docker rm -f
    fi
    
    # Optionally remove the test image (uncomment if desired)
    # docker rmi ai-cli-tests:latest 2>/dev/null || true
    
    print_success "Cleanup completed"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS] [TEST_TYPE]"
    echo ""
    echo "Run AI CLI tests in a secure Docker container"
    echo ""
    echo "TEST_TYPE:"
    echo "  all          Run all tests (default)"
    echo "  functional   Run functional tests only"
    echo "  security     Run security tests only"
    echo "  integration  Run integration tests only"
    echo "  unit         Run unit tests only" 
    echo "  fast         Run fast tests (exclude slow tests)"
    echo ""
    echo "OPTIONS:"
    echo "  -v, --verbose     Run tests in verbose mode"
    echo "  -b, --build       Force rebuild of test image"
    echo "  -c, --cleanup     Clean up Docker resources and exit"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 security -v        # Run security tests in verbose mode"
    echo "  $0 --build functional # Rebuild image and run functional tests"
    echo "  $0 --cleanup          # Clean up Docker resources"
}

# Main function
main() {
    local test_type="all"
    local verbose="false"
    local force_build="false"
    local cleanup_only="false"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                verbose="true"
                shift
                ;;
            -b|--build)
                force_build="true"
                shift
                ;;
            -c|--cleanup)
                cleanup_only="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            functional|security|integration|unit|fast|all)
                test_type="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    # Check Docker availability
    check_docker
    
    # If cleanup only, run cleanup and exit
    if [ "$cleanup_only" = "true" ]; then
        cleanup
        exit 0
    fi
    
    # Build or rebuild image if needed
    if [ "$force_build" = "true" ] || ! docker image inspect ai-cli-tests:latest &> /dev/null; then
        build_test_image
    fi
    
    # Run the tests
    if run_tests "$test_type" "$verbose"; then
        print_success "All tests passed!"
        exit 0
    else
        print_error "Some tests failed!"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"