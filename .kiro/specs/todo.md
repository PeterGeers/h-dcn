aws logs filter-log-events --region eu-west-1 --log-group-name "/aws/lambda/webshop-backend-UpdateProductFunction-fzZ38QlFJd8x" --start-time 1735672800000 --query "events[].message" --output text
put text                                                                                                        INIT_START Runtime Version: python:3.11.v93     Runtime Version ARN: arn:aws:lambda:eu-west-1::runtime:0517e723f
a8dfc41b11b2324c8c497c137d4a3442c2e280cd9deb3ccfd45d0bd                                                                 START RequestId: c7e0d32c-1d36-4806-a646-5636f6fbe533 Version: $LATEST
        END RequestId: c7e0d32c-1d36-4806-a646-5636f6fbe533
        REPORT RequestId: c7e0d32c-1d36-4806-a646-5636f6fbe533  Duration: 382.98 ms     Billed Duration: 950 msM
emory Size: 128 MB      Max Memory Used: 88 MB  Init Duration: 566.27 ms                                        XRAY TraceId: 1-68dab0f5-6eeb2bb60e8a3ce93d952709       SegmentId: 19e793bcd2f11f50     Sampled: true
        INIT

Stop here the following is not intended for now

Selecting productsubgroep werk niet
- Laat alleen productgroepen zien en niet de geneste structuur
-Het selectie nmechanisme is veel te groot ten opzichte van het hele scherm





Should We Implement This?
Yes! This would:

Fix your current member update issue
Secure the product endpoints properly
Create a solid foundation for all future handlers
Ensure frontend and backend always use the same credential data
Would you like me to:

Create the shared auth module first?
    Does the frontend send the right credentials at all locations to the backend already
    Are all backend handlers that are not used removed
This is definitely the right architectural direction for your system.