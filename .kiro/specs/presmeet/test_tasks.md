# PresMeet Feature Test Plan

## Strategy

Deploy a separate CloudFormation stack (`h-dcn-presmeet-feature`) to the nonprofit AWS account. This creates its own API Gateway URL with all 12 PresMeet Lambda functions, while sharing the existing DynamoDB tables. After testing, delete the stack — no trace left in infrastructure.

## Important: Test Data Conventions

- **Club ID for testing**: Always use `club_test_presmeet` as your Cognito group when testing
- **Order identification**: All test orders will have `source: "presmeet"` and `club_id: "test_presmeet"`
- **Config records**: Seeded with prefix `config_presmeet_*` — these are needed for production too, so keep them
- **Cleanup**: After testing, delete orders/payments with `club_id: "test_presmeet"` from DynamoDB

## API URL

After deploy, your staging API base URL will be:

```
https://<api-id>.execute-api.eu-west-1.amazonaws.com/Prod
```

Find it in the deploy output under `Outputs > ApiBaseUrl`, or:

```bash
aws cloudformation describe-stacks --stack-name h-dcn-presmeet-feature --profile nonprofit-deploy --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text
```

All PresMeet endpoints are prefixed with `/presmeet/`:

- `GET  {base}/presmeet/config`
- `PUT  {base}/presmeet/booking`
- `GET  {base}/presmeet/booking`
- `POST {base}/presmeet/booking/submit`
- `POST {base}/presmeet/booking/validate`
- `POST {base}/presmeet/payment`
- `POST {base}/presmeet/webhook/mollie`
- `POST {base}/presmeet/admin/payment`
- `POST {base}/presmeet/admin/lock`
- `POST {base}/presmeet/admin/unlock/{order_id}`
- `POST {base}/presmeet/admin/report/generate`
- `GET  {base}/presmeet/admin/report`

## Authentication

All endpoints (except mollie webhook) require a valid Cognito JWT access token:

```
Authorization: Bearer <access_token>
```

Get a token by signing in through the existing portal (portal.h-dcn.nl) and grabbing it from browser DevTools > Application > Session Storage, or use the AWS CLI:

```bash
aws cognito-idp initiate-auth \
  --client-id 6jhvk853b0lfg9q1m861qs0cug \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=<email>,PASSWORD=<password> \
  --region eu-west-1 --profile nonprofit-deploy \
  --query "AuthenticationResult.AccessToken" --output text
```

## Tasks

- [ ] 1. Deploy feature stack
  - [ ] 1.1 Push feature branch to GitHub
    - ```bash
      git checkout -b feature/presmeet
      git add -A
      git commit --no-verify -m "feat: PresMeet booking module"
      git push -u origin feature/presmeet
      ```
  - [ ] 1.2 Deploy from GitHub Actions (recommended)
    - Go to repo → Actions → "Deploy Backend" workflow
    - Click "Run workflow" → select `feature/presmeet` branch
    - If your workflow doesn't support manual dispatch, add this to `.github/workflows/deploy-backend.yml`:
      ```yaml
      on:
        workflow_dispatch:
        push:
          branches: [main]
          paths: ["backend/**"]
      ```
    - The workflow runs `sam build --use-container` (Docker available in CI) and deploys
    - **Change the stack name** in the workflow to `h-dcn-presmeet-feature` for this run, OR deploy manually from CI output artifacts
  - [ ] 1.3 Alternative: Deploy from local with Python 3.11 workaround
    - Install Python 3.11: `winget install Python.Python.3.11`
    - Then: `cd backend && sam build && sam deploy --stack-name h-dcn-presmeet-feature --region eu-west-1 --profile nonprofit-deploy --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --resolve-s3 --no-confirm-changeset --parameter-overrides MollieApiKey="" S3ReportsBucket=h-dcn-reports`
  - [ ] 1.4 Alternative: Fix Docker and use container build
    - Run `Set-Item Env:DOCKER_HOST "npipe:////./pipe/docker_engine"` then `sam build --use-container`
    - Or restart Docker Desktop and retry
    - Then deploy as above
  - [ ] 1.5 Note the API URL from deploy output
    - ```bash
      aws cloudformation describe-stacks --stack-name h-dcn-presmeet-feature --profile nonprofit-deploy --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" --output text
      ```
    - Save as `$BASE` for subsequent curl commands

- [ ] 2. Seed configuration data
  - [ ] 2.1 Seed Product_Type_Config records
    - `python backend/scripts/seed_presmeet_config.py --profile nonprofit-deploy`
    - Expect: 4 records inserted (meeting_ticket, party_ticket, tshirt, airport_transfer)
  - [ ] 2.2 Verify config endpoint works
    - ```bash
      curl -H "Authorization: Bearer $TOKEN" $BASE/presmeet/config
      ```
    - Expect: JSON with `product_types` array (4 items) and `event` (null until event is seeded)
  - [ ] 2.3 Seed a test event (manual DynamoDB insert)
    - ```bash
      aws dynamodb put-item --table-name Events --profile nonprofit-deploy --item '{
        "event_id": {"S": "presmeet_2025_test"},
        "title": {"S": "Presidents Meeting 2025 TEST"},
        "start_date": {"S": "2025-09-15"},
        "end_date": {"S": "2025-09-18"},
        "source": {"S": "presmeet"}
      }'
      ```

- [ ] 3. Test booking lifecycle
  - [ ] 3.1 Save a booking (creates draft)
    - ```bash
      curl -X PUT -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
          "delegates": [{"name": "Test Delegate", "role": "President", "party": true, "tshirt": {"gender": "male", "size": "L"}}],
          "guests": [{"name": "Test Guest"}],
          "transfers": [{"direction": "pickup", "airport": "AMS", "flight": "KL1234", "date": "2025-09-15", "time": "14:00", "persons": 2}]
        }' \
        $BASE/presmeet/booking
      ```
    - Expect: 200, status "draft", total_amount = 50 + 99.50 + 25 + 99.50 + 10 = €284.00
  - [ ] 3.2 Get booking
    - `curl -H "Authorization: Bearer $TOKEN" $BASE/presmeet/booking`
    - Expect: same order returned with all items
  - [ ] 3.3 Submit booking
    - `curl -X POST -H "Authorization: Bearer $TOKEN" $BASE/presmeet/booking/submit`
    - Expect: 200, status transitions to "submitted", submitted_at set
  - [ ] 3.4 Modify after submit (reverts to draft)
    - Repeat 3.1 with slightly different data
    - Expect: 200, status back to "draft"
  - [ ] 3.5 Resubmit
    - Repeat 3.3
    - Expect: 200, "submitted" again

- [ ] 4. Test validation
  - [ ] 4.1 Exceed max delegates (4 delegates, max is 3)
    - ```bash
      curl -X PUT -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"delegates": [{"name":"A","role":"P"},{"name":"B","role":"S"},{"name":"C","role":"T"},{"name":"D","role":"M"}], "guests":[], "transfers":[]}' \
        $BASE/presmeet/booking
      ```
    - Expect: 400 with error mentioning meeting_ticket limit
  - [ ] 4.2 Validate cart with invalid attributes
    - ```bash
      curl -X POST -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"items": [{"item_id":"x","product_type":"tshirt","attributes":{"name":"Test","gender":"invalid","size":"XXS"}}]}' \
        $BASE/presmeet/booking/validate
      ```
    - Expect: 200, valid=false, errors for gender and size enum violations

- [ ] 5. Test admin operations
  - [ ] 5.1 Lock order (requires webmaster role)
    - `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" $BASE/presmeet/admin/lock`
    - Expect: 200 with locked_count
  - [ ] 5.2 Verify locked order rejects modifications
    - Repeat 3.1 → Expect: 409 "Order is locked"
  - [ ] 5.3 Unlock order
    - `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" $BASE/presmeet/admin/unlock/<order_id>`
    - Expect: 200, status back to "submitted"
  - [ ] 5.4 Generate report
    - `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" $BASE/presmeet/admin/report/generate`
    - Expect: 200 with generated_at, total_orders, generation_duration_ms
  - [ ] 5.5 Get report
    - `curl -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/presmeet/admin/report?type=overview"`
    - Expect: 200 with summary counts and payment aggregates
  - [ ] 5.6 Get CSV export
    - `curl -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/presmeet/admin/report?type=export_all"`
    - Expect: CSV content with header row + data rows
  - [ ] 5.7 Record manual payment
    - ```bash
      curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"order_id":"<order_id>","amount":100,"date":"2025-09-01","description":"Test bank transfer"}' \
        $BASE/presmeet/admin/payment
      ```
    - Expect: 200, payment record with status "paid", order payment_status "partial"

- [ ] 6. Test payment guard
  - [ ] 6.1 Save new draft and attempt payment
    - Save booking (draft) → POST to create payment
    - Expect: 400 "Order must be submitted before payment"
  - [ ] 6.2 Submit order and attempt payment
    - Submit → POST to create payment
    - Expect: 200 with checkout_url (or 502 if MollieApiKey is empty, which is fine)

- [ ] 7. Frontend integration (optional)
  - [ ] 7.1 Update frontend .env to point at feature stack API
    - Set `REACT_APP_API_URL` to your staging API URL
  - [ ] 7.2 Start frontend locally
    - `cd frontend && npm start`
  - [ ] 7.3 Navigate to /presmeet and walk through the UI
    - Add delegates, guests, transfers
    - Save draft, submit, check overview tab
    - If webmaster: check admin tab, generate report, lock/unlock

- [ ] 8. Cleanup
  - [ ] 8.1 Delete test orders from DynamoDB
    - ```bash
      aws dynamodb scan --table-name Orders --profile nonprofit-deploy \
        --filter-expression "source = :s AND club_id = :c" \
        --expression-attribute-values '{":s":{"S":"presmeet"},":c":{"S":"test_presmeet"}}' \
        --query "Items[].order_id.S" --output text
      ```
    - Delete each returned order_id
  - [ ] 8.2 Delete test payments from DynamoDB
    - Same scan pattern on Payments table with `source = "presmeet"`
  - [ ] 8.3 Delete test event
    - `aws dynamodb delete-item --table-name Events --key '{"event_id":{"S":"presmeet_2025_test"}}' --profile nonprofit-deploy`
  - [ ] 8.4 Delete the feature stack
    - `aws cloudformation delete-stack --stack-name h-dcn-presmeet-feature --profile nonprofit-deploy`
    - Wait for deletion: `aws cloudformation wait stack-delete-complete --stack-name h-dcn-presmeet-feature --profile nonprofit-deploy`
  - [ ] 8.5 Keep config records (needed for production)
    - The 4 `config_presmeet_*` records in Producten stay — they're production config

## Notes

- The feature stack shares DynamoDB tables with production. Only test with identifiable test data.
- MollieApiKey is empty in this deployment — payment initiation will return 502. That's expected. Test payment logic via manual payments (admin endpoint) instead.
- The Cognito user pool is shared. Your existing portal login works against the feature stack API.
- Frontend is NOT deployed with the feature stack. Test frontend locally pointing at the staging API, or skip and rely on curl tests.
- After successful testing, merge to main → CI deploys to production `h-dcn` stack automatically.
