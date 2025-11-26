#!/bin/bash
# run_tests.sh
# Script untuk menjalankan tests dengan berbagai opsi
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh unit         # Run unit tests only
#   ./run_tests.sh coverage     # Run with coverage
#   ./run_tests.sh quick        # Run fast tests only
#   ./run_tests.sh help         # Show help

set -e  # Exit on error

# Colors untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

show_help() {
    cat << EOF
${GREEN}Testing Script - Sistem Arsip Digital${NC}

${YELLOW}Usage:${NC}
  ./run_tests.sh [command]

${YELLOW}Commands:${NC}
  all           Run all tests (default)
  unit          Run unit tests only
  integration   Run integration tests only
  service       Run service layer tests
  utils         Run utils tests
  forms         Run forms tests
  
  coverage      Run with coverage report
  quick         Run fast tests only (exclude slow)
  failed        Run failed tests only
  watch         Watch mode (auto-run on changes)
  
  parallel      Run tests in parallel
  verbose       Run with verbose output
  
  clean         Clean test artifacts
  help          Show this help message

${YELLOW}Examples:${NC}
  ./run_tests.sh                    # Run all tests
  ./run_tests.sh unit               # Unit tests only
  ./run_tests.sh coverage           # With coverage
  ./run_tests.sh service verbose    # Service tests verbose
  ./run_tests.sh unit parallel      # Unit tests parallel

${YELLOW}Coverage Reports:${NC}
  After running coverage, open: ${BLUE}htmlcov/index.html${NC}

EOF
}

run_all_tests() {
    print_header "Running All Tests"
    pytest -v
    print_success "All tests completed"
}

run_unit_tests() {
    print_header "Running Unit Tests"
    pytest apps/archive/tests/unit/ -v -m unit
    print_success "Unit tests completed"
}

run_integration_tests() {
    print_header "Running Integration Tests"
    pytest apps/archive/tests/integration/ -v -m integration
    print_success "Integration tests completed"
}

run_service_tests() {
    print_header "Running Service Layer Tests"
    pytest apps/archive/tests/unit/services/ -v
    print_success "Service tests completed"
}

run_utils_tests() {
    print_header "Running Utils Tests"
    pytest apps/archive/tests/unit/utils/ -v
    print_success "Utils tests completed"
}

run_forms_tests() {
    print_header "Running Forms Tests"
    pytest apps/archive/tests/unit/forms/ -v
    print_success "Forms tests completed"
}

run_coverage() {
    print_header "Running Tests with Coverage"
    pytest --cov=apps.archive \
           --cov-report=html \
           --cov-report=term-missing \
           -v
    
    print_success "Coverage report generated"
    print_warning "Open htmlcov/index.html to view detailed report"
}

run_quick() {
    print_header "Running Quick Tests (Fast Only)"
    pytest -m "not slow" -v
    print_success "Quick tests completed"
}

run_failed() {
    print_header "Running Failed Tests Only"
    pytest --lf -v
    print_success "Failed tests rerun completed"
}

run_watch() {
    print_header "Watch Mode - Auto-run on changes"
    print_warning "Press Ctrl+C to stop"
    
    if command -v ptw &> /dev/null; then
        ptw -- -v
    else
        print_error "pytest-watch not installed"
        print_warning "Install: pip install pytest-watch"
        exit 1
    fi
}

run_parallel() {
    print_header "Running Tests in Parallel"
    pytest -n auto -v
    print_success "Parallel tests completed"
}

run_verbose() {
    print_header "Running Tests (Verbose)"
    pytest -vv --tb=long
}

clean_artifacts() {
    print_header "Cleaning Test Artifacts"
    
    # Remove cache directories
    find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove coverage files
    rm -rf htmlcov/ 2>/dev/null || true
    rm -f .coverage 2>/dev/null || true
    rm -f coverage.xml 2>/dev/null || true
    
    print_success "Test artifacts cleaned"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_error "pytest is not installed"
    print_warning "Install: pip install -r requirements-dev.txt"
    exit 1
fi

# Main execution
case "${1:-all}" in
    all)
        run_all_tests
        ;;
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    service)
        run_service_tests
        ;;
    utils)
        run_utils_tests
        ;;
    forms)
        run_forms_tests
        ;;
    coverage)
        run_coverage
        ;;
    quick)
        run_quick
        ;;
    failed)
        run_failed
        ;;
    watch)
        run_watch
        ;;
    parallel)
        run_parallel
        ;;
    verbose)
        run_verbose
        ;;
    clean)
        clean_artifacts
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

# Handle additional flags
if [[ "$2" == "verbose" ]]; then
    print_warning "Running with verbose output..."
fi

if [[ "$2" == "parallel" ]]; then
    print_warning "Running in parallel mode..."
fi

exit 0