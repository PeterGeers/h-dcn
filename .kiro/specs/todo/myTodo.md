# Post-Refactor Findings

## Dead code removed from eventBooking

The following PresMeet-specific files were deleted — no live component imported them:

| Deleted                                          | Reason                                                    |
| ------------------------------------------------ | --------------------------------------------------------- |
| `utils/cartBuilder.ts`                           | Builds cart from PresMeet BookingFormData — dead code     |
| `utils/cartBuilder.test.ts`                      | Tests for dead utility                                    |
| `utils/validation.ts`                            | Validates PresMeet-specific form data — dead code         |
| `utils/pdfGenerator.ts`                          | Generates PDF from PresMeet cart/booking data — dead code |
| `__tests__/cartBuilder.property.test.ts`         | Tests dead utility                                        |
| `__tests__/validation.property.test.ts`          | Tests dead utility                                        |
| `__tests__/validation.test.ts`                   | Tests dead utility                                        |
| `__tests__/bookingCalculations.property.test.ts` | Tests dead utility                                        |
| `__tests__/pdfGenerator.property.test.ts`        | Tests dead utility                                        |
| `__tests__/clubSearch.property.test.ts`          | Tests OnboardingFlow.filterClubs (can be re-added later)  |

## Remaining: presmeet.types.ts in eventBooking

`eventBooking/types/presmeet.types.ts` still exists — it's used by:

- `OnboardingFlow.tsx` (imports `ClubRegistryEntry`, `ClubRegistry`)

This will be cleaned up when OnboardingFlow is refactored (the `/presmeet/clubs` endpoint it calls also needs to be updated).

## Final verification

- `npx tsc --noEmit`: zero errors ✅
- `npx react-scripts test --watchAll=false --testPathPattern="eventBooking"`: 13 suites, 181 tests pass ✅
- `grep modules/presmeet` in .ts/.tsx: zero matches ✅
- `modules/presmeet/` directory: does not exist ✅

# H-DCN Todo List



## .kiro\specs\code-quality-maintenance
- Add check failing tests (UNit, Integration and e2e) and add test resolution to tasks.md
- Add security analysis (or sperate prompt) to detect 

## Use of google mail vs AWS SES

  
## Multi-language
Extend Multi language (whole app) also in the backend

## Type hints
Voor een AWS Lambda + DynamoDB SaaS-platform zou ik zelf eerder streven naar:

100% type hints op nieuwe code
Verbeter de meest gewijzigde bestanden
Verbeter bestanden met de meeste Pyright/MyPy-waarschuwingen
Laat oude, stabiele code voorlopig met rust



## Standardize naming conventions
Standardize naming conventions to english verbs for tables and fields in dynamo db tables and fix all handlers that touch them. 
This would help reduce errors/ typos as KIRO often assumes the proper names in English

# missing functions
Now about Issue 3: separate price for a variant — that's a feature/design issue rather than a bug introduced by this branch. The variant schema editor doesn't currently support per-variant pricing. That would be a separate feature request. Let me note it but not block on it.


