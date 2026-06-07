# Implementation Plan

## Overview

Fix the SAM circular dependency caused by `CreateOrderFunction`'s `MOLLIE_WEBHOOK_URL` environment variable referencing `${MyApi}` via `!Sub`. The fix removes the template-level API reference and constructs the webhook URL at runtime from the Lambda event's `requestContext`.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - SAM Template Circular Dependency via MyApi Reference in Environment
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the circular dependency exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case: `CreateOrderFunction` environment variable `MOLLIE_WEBHOOK_URL` containing `!Sub` with `${MyApi}` reference
  - Create test file `backend/tests/unit/test_circular_dependency_bug.py`
  - Use `hypothesis` to generate SAM template structures with varying environment variables
  - The property under test: For any SAM template where a Lambda function has BOTH an `Environment.Variables` entry referencing `MyApi` via `!Sub` AND an `Events` entry with `RestApiId: !Ref MyApi`, the template validation SHALL detect a circular dependency
  - Parse `backend/template.yaml` and assert that `CreateOrderFunction`'s `MOLLIE_WEBHOOK_URL` does NOT contain `${MyApi}` reference (from Bug Condition: `isBugCondition(template)` in design)
  - Expected Behavior assertion: the env var value should construct the webhook URL without referencing the API resource directly
  - Run test on UNFIXED code - expect FAILURE (the template currently contains `${MyApi}` in `MOLLIE_WEBHOOK_URL`)
  - Document counterexample: `MOLLIE_WEBHOOK_URL: !Sub "https://${MyApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/mollie-webhook"` creates circular dependency
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Webhook URL Construction Produces Valid Reachable URLs
  - **IMPORTANT**: Follow observation-first methodology
  - **IMPORTANT**: Write these tests BEFORE implementing the fix
  - Create test file `backend/tests/unit/test_webhook_url_preservation.py`
  - Observe: On unfixed code, `MOLLIE_WEBHOOK_URL` env var produces URLs matching `https://<api-id>.execute-api.eu-west-1.amazonaws.com/<stage>/mollie-webhook`
  - Observe: The `create_order` handler passes this URL to `create_payment()` as the `webhook_url` parameter
  - Observe: The handler falls back to empty string when env var is not set
  - Write property-based test with `hypothesis`: for all valid API Gateway request contexts (random `apiId` strings matching `[a-z0-9]{10}`, random stage names from `[a-zA-Z0-9_-]+`), the runtime webhook URL construction function SHALL produce a URL matching `https://{apiId}.execute-api.eu-west-1.amazonaws.com/{stage}/mollie-webhook`
  - Write property: for all valid request contexts, the constructed URL always ends with `/mollie-webhook`
  - Write property: for all valid request contexts, the constructed URL is a valid HTTPS URL
  - Write unit test: when `MOLLIE_WEBHOOK_URL` env var is set, it takes precedence (fallback/override for testing)
  - Verify tests pass on UNFIXED code (the URL construction function will be a pure helper that works independently of the template fix)
  - _Requirements: 3.1, 3.3_

- [x] 3. Fix for SAM circular dependency in CreateOrderFunction MOLLIE_WEBHOOK_URL
  - [x] 3.1 Remove `${MyApi}` reference from `MOLLIE_WEBHOOK_URL` in `backend/template.yaml`
    - Remove or replace the line `MOLLIE_WEBHOOK_URL: !Sub "https://${MyApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}/mollie-webhook"` from `CreateOrderFunction`'s Environment block
    - The environment variable can be removed entirely (runtime construction replaces it) or kept as an empty/commented placeholder for local testing override
    - No other functions or environment variables should be modified
    - _Bug_Condition: isBugCondition(template) — CreateOrderFunction Environment.Variables contains !Sub referencing MyApi AND Events contains RestApiId: !Ref MyApi_
    - _Expected_Behavior: Template deploys without circular dependency; webhook URL still valid_
    - _Preservation: All other Lambda functions, API routes, permissions unchanged_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.2, 3.4_

  - [x] 3.2 Add runtime webhook URL construction in `backend/handler/create_order/app.py`
    - Create a helper function `_build_webhook_url(event)` that constructs the Mollie webhook URL from the Lambda event's request context:
      ```python
      def _build_webhook_url(event):
          request_context = event.get('requestContext', {})
          api_id = request_context.get('apiId', '')
          stage = request_context.get('stage', '')
          region = os.environ.get('AWS_REGION', 'eu-west-1')
          return f"https://{api_id}.execute-api.{region}.amazonaws.com/{stage}/mollie-webhook"
      ```
    - Update `_handle_mollie_payment` to accept the `event` parameter and use `_build_webhook_url(event)` instead of relying solely on the `MOLLIE_WEBHOOK_URL` env var
    - Keep `MOLLIE_WEBHOOK_URL` env var as fallback/override: `webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event)`
    - Update `_update_persistent_order` similarly to pass event and use the new webhook URL construction
    - Thread the `event` parameter through `_create_new_order` → `_handle_mollie_payment`
    - _Bug_Condition: Removes need for template-level MyApi reference_
    - _Expected_Behavior: Webhook URL matches https://{apiId}.execute-api.{region}.amazonaws.com/{stage}/mollie-webhook_
    - _Preservation: Fallback to env var preserves local testing and override capability_
    - _Requirements: 2.1, 3.1, 3.3_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - SAM Template Circular Dependency Resolved
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 asserts that `CreateOrderFunction`'s `MOLLIE_WEBHOOK_URL` does NOT contain `${MyApi}`
    - After removing the reference in 3.1, this test should now PASS
    - Run: `pytest backend/tests/unit/test_circular_dependency_bug.py -v`
    - **EXPECTED OUTCOME**: Test PASSES (confirms circular dependency is resolved)
    - _Requirements: 2.1, 2.2_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Webhook URL Construction Still Valid
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run: `pytest backend/tests/unit/test_webhook_url_preservation.py -v`
    - **EXPECTED OUTCOME**: Tests PASS (confirms webhook URL construction produces valid URLs and no regressions)
    - Confirm all property-based tests still pass after the fix
    - _Requirements: 3.1, 3.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run full test suite: `pytest backend/tests/ -v`
  - Verify no circular dependency errors: `sam validate` in `backend/`
  - Confirm `sam build` succeeds without errors
  - Ensure all tests pass, ask the user if questions arise

## Task Dependency Graph

```json
{
  "waves": [["1", "2"], ["3.1"], ["3.2"], ["3.3", "3.4"], ["4"]]
}
```

## Notes

- Tests use `pytest` and `hypothesis` for property-based testing
- The `_build_webhook_url(event)` helper is a pure function testable in isolation
- `MOLLIE_WEBHOOK_URL` env var kept as fallback for local testing (`sam local invoke`)
- No changes needed to `MollieWebhookFunction` — only the URL _construction_ in `CreateOrderFunction` changes
- The `backend/template.yaml` change is the only infrastructure modification; all other resources remain untouched
