#!/bin/bash
set -uo pipefail

cd "$(dirname "$0")"

# Run performance tests
output=$(npm run test:data-processing:performance 2>&1)

echo "$output"

# Check for test failures
if echo "$output" | grep -qE "FAIL.*test"; then
  echo "METRIC avg_performance_ms=99999"
  echo "METRIC tests_passed=0"
  exit 0
fi

# Parse timing data from test output  
test_times=$(echo "$output" | grep -oE '\([0-9]+ ms\)' | grep -oE '[0-9]+')

if [ -z "$test_times" ]; then
  avg_time=100
else
  total=0
  count=0
  for t in $test_times; do
    total=$((total + t))
    count=$((count + 1))
  done
  avg_time=$((total / count))
fi

# Extract specific times
fuzzy_time=$(echo "$output" | grep -i "fuzzy" | grep -oE '\([0-9]+ ms\)' | grep -oE '[0-9]+')
sort_large_time=$(echo "$output" | grep -i "sort large" | grep -oE '\([0-9]+ ms\)' | grep -oE '[0-9]+')

echo "METRIC avg_performance_ms=${avg_time:-100}"
echo "METRIC fuzzy_search_ms=${fuzzy_time:-150}"
echo "METRIC sort_large_ms=${sort_large_time:-40}"
