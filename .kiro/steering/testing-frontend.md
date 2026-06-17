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

## ESLint

The CI build runs ESLint as part of `react-scripts build` — it fails the build on any error. Always check for lint issues before committing frontend changes:

```bash
# From frontend/ directory — lint a specific file
npx eslint src/modules/products/components/VariantEditModal.tsx

# Lint all changed files (uses git diff)
npx eslint $(git diff --name-only --diff-filter=d HEAD -- 'src/**/*.ts' 'src/**/*.tsx')
```

### Common lint errors to avoid

- **no-unused-vars**: Remove unused imports and variables. CI treats these as errors.
- **react-hooks/exhaustive-deps**: Add missing dependencies or suppress with `// eslint-disable-next-line`.
- When removing code (imports, functions), check that nothing else referenced the removed symbol.

### Quick lint check before commit

After editing a file, run ESLint on it before staging. The build will fail otherwise and require a fix commit.
