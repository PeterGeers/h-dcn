# Autoresearch: DataProcessingService Runtime Optimization

## Objective
Optimize the runtime performance of `DataProcessingService.ts` for filtering, sorting, search, and aggregation operations on member datasets up to 5K records.

## Current Metrics (Baseline)
- **avg_performance_ms**: 20 (average across all tests)
- **fuzzy_search_ms**: 141 (5K records - close to 150ms limit)
- **sort_large_ms**: 40 (5K records)
- **filter_large_ms**: 2 (5K records)

## Test Command
`npm run test:data-processing:performance`

## Files in Scope
- `src/services/DataProcessingService.ts` - Main service to optimize

## Off Limits
- Test files (these define the targets)
- Type definitions (keep interfaces stable)
- WebWorkerManager.ts (separate concern)

## Constraints
- All performance tests must pass (< thresholds)
- Functional correctness must be maintained

## Optimization Targets (in priority order)

### 1. Fuzzy Match (Highest Priority)
**Problem**: Levenshtein distance algorithm is O(n×m) quadratic complexity.
**Current**: ~141ms for 5K records
**Target**: <100ms

**Ideas**:
- Add early termination when impossible to reach threshold
- Use optimized iterative approach instead of full matrix
- Add length-based quick reject
- Cache results for repeated patterns

### 2. Sorting
**Problem**: `[...data].sort()` creates unnecessary copy
**Current**: ~40ms for 5K records
**Target**: <30ms

**Ideas**:
- Avoid array spread if input can be modified
- Use native sort with optimized comparator

### 3. String Operations
**Problem**: Repeated `toLowerCase()` calls in filtering/search
**Ideas**:
- Normalize once and reuse
- Consider case-insensitive comparison without creating new strings

### 4. Filtering
**Current**: ~2ms for 5K records (already good, but can improve)
**Ideas**:
- short-circuit evaluation for OR logic
- Pre-compute field values

## What's Been Tried

### Baseline
- Recorded initial metrics
- Identified fuzzy search as #1 bottleneck
