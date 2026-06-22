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
