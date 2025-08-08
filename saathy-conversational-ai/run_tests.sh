#!/bin/bash

# Saathy Conversational AI - Test Runner Script

set -e  # Exit on error

echo "=== Saathy Conversational AI Test Suite ==="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
RUN_BACKEND=true
RUN_FRONTEND=true
RUN_INTEGRATION=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only)
            RUN_FRONTEND=false
            shift
            ;;
        --frontend-only)
            RUN_BACKEND=false
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --help)
            echo "Usage: ./run_tests.sh [OPTIONS]"
            echo "Options:"
            echo "  --backend-only    Run only backend tests"
            echo "  --frontend-only   Run only frontend tests"
            echo "  --integration     Include integration tests"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Backend Tests
if [ "$RUN_BACKEND" = true ]; then
    echo -e "${BLUE}Running Backend Tests...${NC}"
    cd backend
    
    # Run unit tests
    echo -e "${BLUE}Running unit tests...${NC}"
    if [ "$RUN_INTEGRATION" = true ]; then
        pytest -v
    else
        pytest -v -m "not integration"
    fi
    
    BACKEND_EXIT=$?
    
    if [ $BACKEND_EXIT -eq 0 ]; then
        echo -e "${GREEN}✓ Backend tests passed${NC}"
    else
        echo -e "${RED}✗ Backend tests failed${NC}"
    fi
    
    # Show coverage report location
    echo -e "${BLUE}Coverage report generated at: backend/htmlcov/index.html${NC}"
    
    cd ..
    echo
fi

# Frontend Tests
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${BLUE}Running Frontend Tests...${NC}"
    cd frontend
    
    # Run Jest tests
    npm test -- --watchAll=false --coverage
    
    FRONTEND_EXIT=$?
    
    if [ $FRONTEND_EXIT -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend tests passed${NC}"
    else
        echo -e "${RED}✗ Frontend tests failed${NC}"
    fi
    
    cd ..
    echo
fi

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"

if [ "$RUN_BACKEND" = true ]; then
    if [ ${BACKEND_EXIT:-1} -eq 0 ]; then
        echo -e "${GREEN}✓ Backend: PASS${NC}"
    else
        echo -e "${RED}✗ Backend: FAIL${NC}"
    fi
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ ${FRONTEND_EXIT:-1} -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend: PASS${NC}"
    else
        echo -e "${RED}✗ Frontend: FAIL${NC}"
    fi
fi

# Exit with failure if any tests failed
if [ ${BACKEND_EXIT:-0} -ne 0 ] || [ ${FRONTEND_EXIT:-0} -ne 0 ]; then
    exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"