# Frontend Testing Conventions

## Critical Rules

### Never run react-scripts test without --watchAll=false

`react-scripts test` defaults to Jest watch mode, which **never terminates**. Always pass `--watchAll=false`:

```bash
# From frontend/ directory
npx react-scripts test --watchAll=false
```

### Always use --testPathPattern for single files

The full frontend test suite has pre-existing Babel/TypeScript transform issues that cause mass failures. Always target specific test files:

```bash
# Run a specific test file
npx react-scripts test --watchAll=false --testPathPattern="sizeSorter"

# Run property tests only
npx react-scripts test --watchAll=false --testPathPattern="property"

# Run tests in a specific module
npx react-scripts test --watchAll=false --testPathPattern="webshop-management"
```

### Never run the full frontend test suite in automation

Running all ~110 test suites at once will fail due to Babel config issues with some older files. This is a known pre-existing issue. When verifying frontend code:

1. Use `npx tsc --noEmit` for type checking (fast, reliable)
2. Use `--testPathPattern` to run only the relevant test file(s)
3. Do **not** run the entire suite unless explicitly asked

## Property-Based Tests (fast-check)

Frontend property tests use `fast-check`. Place them in `__tests__/<utility>.property.test.ts` alongside the regular unit tests:

```bash
npx react-scripts test --watchAll=false --testPathPattern="sizeSorter.property"
```
