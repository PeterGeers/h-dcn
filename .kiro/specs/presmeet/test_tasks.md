# PresMeet Feature Test Plan

## Status

- **Branch**: `feature/presmeet` (pushed)
- **Stack**: `h-dcn-presmeet-feature` (deployed via GitHub Actions #21)
- **API Base URL**: `https://7sze61wi7j.execute-api.eu-west-1.amazonaws.com/prod`

## Test Data Conventions

- **Config records**: Prefix `config_presmeet_*` in Producten table — keep these (needed for production)
- **Test event**: `event_id: "presmeet_2025_test"` in Events table — delete after testing
- **Test orders**: Will be created by your Cognito user's club_id — delete after testing
- **Cleanup**: Delete test orders/payments/event from DynamoDB when done; keep config records

## Authentication

All endpoints (except mollie webhook) require a valid Cognito access token:

```
Authorization: Bearer <access_token>
```

Get a token from browser DevTools (portal.h-dcn.nl → Application → Session Storage → accessToken), or:

```bash
aws cognito-idp initiate-auth \
  --client-id 6jhvk853b0lfg9q1m861qs0cug \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=<email>,PASSWORD=<password> \
  --region eu-west-1 --profile nonprofit-deploy \
  --query "AuthenticationResult.AccessToken" --output text
```

Set variables for convenience:

```bash
$BASE = "https://7sze61wi7j.execute-api.eu-west-1.amazonaws.com/prod"
$TOKEN = "<your_access_token>"
$ADMIN_TOKEN = "<webmaster_user_access_token>"
```

## Tasks

- [ ] 1. Seed configuration data
  - [ ] 1.1 Seed Product_Type_Config records
    - `python backend/scripts/seed_presmeet_config.py --profile nonprofit-deploy`
    - Expect: 4 records inserted (meeting_ticket, party_ticket, tshirt, airport_transfer)
  - [ ] 1.2 Seed a test event
    - ```bash
      aws dynamodb put-item --table-name Events --profile nonprofit-deploy --region eu-west-1 --item '{
        "event_id": {"S": "presmeet_2025_test"},
        "title": {"S": "Presidents Meeting 2025 TEST"},
        "start_date": {"S": "2025-09-15"},
        "end_date": {"S": "2025-09-18"},
        "source": {"S": "presmeet"}
      }'
      ```
  - [ ] 1.3 Verify config endpoint
    - `curl -H "Authorization: Bearer $TOKEN" $BASE/presmeet/config`
    - Expect: JSON with `product_types` (4 items) and `event` (start_date, end_date)

- [x 2. Test booking lifecycle
  - [x] 2.1 Save a booking (creates draft)
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
    - Expect: 200, status "draft", total_amount = €284.00
  - [x] 2.2 Get booking
    - `curl -H "Authorization: Bearer $TOKEN" $BASE/presmeet/booking`
    - Expect: same order with all items
  - [x] 2.3 Submit booking
    - `curl -X POST -H "Authorization: Bearer $TOKEN" $BASE/presmeet/booking/submit`
    - Expect: 200, status "submitted", submitted_at set
  - [x] 2.4 Modify after submit (reverts to draft)
    - Repeat 2.1 with different data → Expect: status back to "draft"
  - [x] 2.5 Resubmit
    - Repeat 2.3 → Expect: "submitted" again

- [x] 3. Test validation
  - [x] 3.1 Exceed max delegates (4, max is 3)
    - ```bash
      curl -X PUT -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"delegates":[{"name":"A","role":"P"},{"name":"B","role":"S"},{"name":"C","role":"T"},{"name":"D","role":"M"}],"guests":[],"transfers":[]}' \
        $BASE/presmeet/booking
      ```
    - Expect: 400 with error mentioning meeting_ticket limit
  - [x] 3.2 Validate cart with invalid attributes
    - ```bash
      curl -X POST -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"items":[{"item_id":"x","product_type":"tshirt","attributes":{"name":"Test","gender":"invalid","size":"XXS"}}]}' \
        $BASE/presmeet/booking/validate
      ```
    - Expect: 200, valid=false, errors for gender and size enum violations

- [ ] 4. Test admin operations (requires webmaster role token)
  - [ ] 4.1 Lock order
    - `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" $BASE/presmeet/admin/lock`
    - Expect: 200 with locked_count ≥ 1
  - [ ] 4.2 Verify locked order rejects modifications
    - Repeat 2.1 → Expect: 409 "Order is locked"
  - [ ] 4.3 Unlock order
    - `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" $BASE/presmeet/admin/unlock/<order_id>`
    - Expect: 200, status "submitted"
  - [ ] 4.4 Generate report
    - `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" $BASE/presmeet/admin/report/generate`
    - Expect: 200 with generated_at, total_orders, generation_duration_ms
  - [ ] 4.5 Get report
    - `curl -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/presmeet/admin/report?type=overview"`
    - Expect: 200 with summary counts and payment aggregates
  - [ ] 4.6 Download CSV export
    - `curl -H "Authorization: Bearer $ADMIN_TOKEN" "$BASE/presmeet/admin/report?type=export_all"`
    - Expect: CSV content with header + data rows
  - [ ] 4.7 Record manual payment
    - ```bash
      curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"order_id":"<order_id>","amount":100,"date":"2025-09-01","description":"Test bank transfer"}' \
        $BASE/presmeet/admin/payment
      ```
    - Expect: 200, payment_status "partial"

- [ ] 5. Test payment guard
  - [ ] 5.1 Payment on draft order
    - Save new booking (draft) → `curl -X POST ... $BASE/presmeet/payment`
    - Expect: 400 "Order must be submitted before payment"
  - [ ] 5.2 Payment on submitted order
    - Submit → `curl -X POST ... $BASE/presmeet/payment`
    - Expect: 502 (MollieApiKey is empty — confirms handler runs correctly up to the Mollie call)

- [ ] 6. Frontend integration (optional)
  - [ ] 6.1 Set `REACT_APP_API_URL=https://7sze61wi7j.execute-api.eu-west-1.amazonaws.com/prod` in frontend .env
  - [ ] 6.2 Run `cd frontend && npm start`
  - [ ] 6.3 Navigate to /presmeet, walk through booking form, overview tab, admin tab

- [ ] 7. Cleanup
  - [ ] 7.1 Delete test orders from Orders table
    - Scan for `source = "presmeet"` with your club_id, delete each
  - [ ] 7.2 Delete test payments from Payments table
    - Scan for `source = "presmeet"`, delete each
  - [ ] 7.3 Delete test event
    - `aws dynamodb delete-item --table-name Events --key '{"event_id":{"S":"presmeet_2025_test"}}' --profile nonprofit-deploy --region eu-west-1`
  - [ ] 7.4 Delete the feature stack
    - `aws cloudformation delete-stack --stack-name h-dcn-presmeet-feature --profile nonprofit-deploy --region eu-west-1`
  - [ ] 7.5 Keep config records
    - The 4 `config_presmeet_*` records in Producten stay (needed for production)

## Notes

- MollieApiKey is empty → payment initiation returns 502. Test payment logic via manual payments (task 4.7) instead.
- Cognito user pool is shared. Your existing portal login works against the feature stack API.
- After successful testing: merge `feature/presmeet` to `main` → CI auto-deploys to production `h-dcn` stack.
