#!/bin/bash
# Test script for DataProcessingService (Linux/Mac version)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Default values
WATCH=false
COVERAGE=false
VERBOSE=false
PATTERN=""
UPDATE_SNAPSHOTS=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --watch)
            WATCH=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --pattern)
            PATTERN="$2"
            shift 2
            ;;
        --update-snapshots)
            UPDATE_SNAPSHOTS=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --watch              Run tests in watch mode"
            echo "  --coverage           Generate coverage report"
            echo "  --verbose            Run tests with verbose output"
            echo "  --pattern PATTERN    Run only tests matching pattern"
            echo "  --update-snapshots   Update snapshots"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}🧪 H-DCN DataProcessingService Test Runner${NC}"
echo -e "${CYAN}===========================================${NC}"

# Change to frontend directory
cd "$(dirname "$0")/.."

# Build test command
TEST_COMMAND="npm test -- --testPathPattern=DataProcessingService"

if [ "$WATCH" = true ]; then
    echo -e "${YELLOW}📺 Running tests in watch mode...${NC}"
    TEST_COMMAND="$TEST_COMMAND --watch"
else
    TEST_COMMAND="$TEST_COMMAND --watchAll=false"
fi

if [ "$COVERAGE" = true ]; then
    echo -e "${YELLOW}📊 Generating coverage report...${NC}"
    TEST_COMMAND="$TEST_COMMAND --coverage --coverageDirectory=coverage/data-processing"
fi

if [ "$VERBOSE" = true ]; then
    echo -e "${YELLOW}🔍 Running with verbose output...${NC}"
    TEST_COMMAND="$TEST_COMMAND --verbose"
fi

if [ -n "$PATTERN" ]; then
    echo -e "${YELLOW}🎯 Running tests matching pattern: $PATTERN${NC}"
    TEST_COMMAND="$TEST_COMMAND --testNamePattern='$PATTERN'"
fi

if [ "$UPDATE_SNAPSHOTS" = true ]; then
    echo -e "${YELLOW}📸 Updating snapshots...${NC}"
    TEST_COMMAND="$TEST_COMMAND --updateSnapshot"
fi

echo ""
echo -e "${GRAY}Executing: $TEST_COMMAND${NC}"
echo ""

# Run the tests
eval $TEST_COMMAND

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All DataProcessingService tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo -e "${CYAN}📊 Coverage report generated in: coverage/data-processing/${NC}"
        echo -e "${GRAY}   Open coverage/data-processing/lcov-report/index.html to view detailed report${NC}"
    fi
else
    echo ""
    echo -e "${RED}❌ Some tests failed. Exit code: $EXIT_CODE${NC}"
fi

exit $EXIT_CODE