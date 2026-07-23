# Test Cases — mobilityTCS_experiment (oTree)

Scope: `app1_intro` → `app2_testI` → `app3_testII` → `app4_phaseI` → `app5_phaseII` → `app6_phaseIII` → `app7_postsurvey` → `app8_thankyou`

---

## 1. Session / Room Setup
| # | Test | Expected Result |
|---|------|------------------|
| 1.1 | Start session `mobilityTCS_experiment` in room `LEE` with a label from `Participants.txt` | Session starts, app_sequence runs in order, no errors |
| 1.2 | Open link with a label **not** in `Participants.txt` | oTree rejects / access denied |
| 1.3 | Two participants join `group_by_arrival_time=True` room roughly at once | Each is grouped independently (`PLAYERS_PER_GROUP = None` in early apps) |
| 1.4 | `participation_fee = 0.00`, `real_world_currency_per_point = 1.00` | Final payoff shown equals accumulated DKK budget, no extra base fee |

---

## 2. App1 — Intro (`CodeEntry` + `Introduction`)
| # | Test | Expected Result |
|---|------|------------------|
| 2.1 | Enter a valid `id_code` from `choice_set.csv` (any case, e.g. lowercase) | Accepted — code is upper-cased before lookup; proceeds to Introduction |
| 2.2 | Enter an invalid/unknown code | Error: "Invalid code. Please check and re-enter your personal code." |
| 2.3 | Submit empty code field | Error: "Please enter your personal code." |
| 2.4 | Enter code with leading/trailing whitespace | Still accepted (stripped before lookup) |
| 2.5 | Valid code entered → check participant vars | `all_trips`, `initial_budget`, `initial_token`, `initial_token_reduced`, `initial_token_distance`, `token_price_history=[10.00]` all set correctly from CSV row |
| 2.6 | Introduction quiz — answer all 6 questions correctly (2,3,2,1,1,3) | Page advances, no error |
| 2.7 | Introduction quiz — answer one question incorrectly | Only that field shows "Incorrect. Please review this part."; others unaffected |
| 2.8 | Introduction quiz — leave a radio button unselected | Blocked (all fields `blank=False`) |
| 2.9 | Trip preview on Introduction page shows first *commuting* trip (skips `no_commute` days) | Preview data / default mode matches the first trip where `mode != 'no_commute'` |
| 2.10 | Reload/refresh CodeEntry page after invalid attempt | Form resets, previous invalid state doesn't persist incorrectly |

---

## 3. App2 — Test Phase I (5 rounds)
| # | Test | Expected Result |
|---|------|------------------|
| 3.1 | Round 1 `WeekPreview` | Displays `initial_budget`, `initial_token`, token price = 10.00, correct weekly overview table |
| 3.2 | Day where `trip.mode == 'no_commute'` | `NoCommute` page shown, `Choice` page skipped |
| 3.3 | Day where `trip.mode != 'no_commute'` | `Choice` page shown, `NoCommute` skipped |
| 3.4 | Select a mode requiring more tokens than currently owned | Extra tokens auto-purchased at current token price + `AUTO_FEE (50)`; budget reduced accordingly |
| 3.5 | Select a mode requiring fewer/equal tokens than owned | No auto-purchase; tokens simply deducted, no `AUTO_FEE` charged |
| 3.6 | Timeout on `Choice` page (no `timeout_seconds` set here → default page timeout) | Default preselected trip mode (`trip['mode']`) is used automatically |
| 3.7 | Complete round 5 | `Results` page displayed (`round_number % 5 == 0`) |
| 3.8 | Rounds 1–4 | `Results` page NOT displayed |
| 3.9 | Results page shows weekly summary | Correct `baseline_emissions`, `actual_emissions`, `emissions_saved`/`emissions_excess`, `budget`, CO₂-equivalent sentence |
| 3.10 | Emissions saved negative (participant polluted more than baseline) | "You produced X kg CO₂eq more..." message shown, not a benchmark equivalence |
| 3.11 | Emissions saved = 0 | "No emissions saved in total yet..." message shown |
| 3.12 | Budget carries between rounds within the same 5-round week | Round *n+1* budget/token = round *n* ending values (no reset mid-week) |
| 3.13 | Player choice for `no_commute` day | Cost = 0, tokens = 0, `trip_choices` entry has `choice='no_commute'` |

---

## 4. App3 — Test Phase II (Market introduced)
| # | Test | Expected Result |
|---|------|------------------|
| 4.1 | `Instruction` quiz — correct answers (`price_change='3'`, `token_buy='3'`) | Advances without error |
| 4.2 | `Instruction` quiz — incorrect answer | Field-specific error shown |
| 4.3 | `SyncWaitPage` — only players with `advance_to_phase_III=True` proceed | Others do not see wait page / are filtered by `group_by_arrival_time_method` |
| 4.4 | `Market` page — buy tokens (`token_purchased > 0`) | `budget -= token_purchased * token_price`; if any trade occurs, `transaction_costs (4)` deducted once |
| 4.5 | `Market` page — sell tokens (`token_sold > 0`) | `budget += token_sold * token_price`; transaction cost deducted once |
| 4.6 | `Market` page — buy and sell 0 tokens | No transaction cost charged |
| 4.7 | `MarketWaitPage.after_all_players_arrive` | New `token_price = old_price + (net_traded + pending_net) * 0.05`, clamped to [1.0, 100.0] |
| 4.8 | Aggregate trades push price below 1.0 or above 100.0 | Price clamped at bounds, never negative or >100 |
| 4.9 | Timeout on `Market` page (60s) | `timeout_occurred_market = True`; no purchase/sale applied (fields blank ⇒ treated as 0) |
| 4.10 | Timeout on `Choice` page (60s) | `timeout_occurred_choice = True`; default trip mode auto-selected |
| 4.11 | `NoCommute` day | `Choice`/`Market` interplay: `ConditionalChoiceOrNoCommuteWaitPage` only waits for players with a commute trip |
| 4.12 | Round 5 `Results` | Sellback of remaining tokens at current price minus `TRANSACTION_COSTS`; for `current_phase == 'testI'` no transaction cost (N/A here, applies to app2) |
| 4.13 | Refresh `Results` page after first render (round already scored) | `sellback_{phase}_round_{n}` cache reused — values remain the same, not recomputed/doubled |
| 4.14 | Token price graph (`token_price_history_js`) across phase | Correct day labels (weekday abbreviations for current phase, "Phase X" label for prior phases) |

---

## 5. App4/5/6 — Phase I / II / III (15 rounds = 3 weeks × 5 days)
| # | Test | Expected Result |
|---|------|------------------|
| 5.1 | Phase I: start of each 5-round week (`round % 5 == 1`) | Budget resets to `initial_budget`; tokens reset to `initial_token_reduced` (Phase I passes `reduced=True`) |
| 5.2 | Phase II: week reset | Tokens reset to `initial_token` (Phase II/III do not pass `reduced`, only Phase III passes `distance=True`) |
| 5.3 | Phase III: week reset | Tokens reset to `initial_token_distance` |
| 5.4 | Phase II & III: `Choice`/`Market` pass `vary=True` | Mode cost drawn from `tour_total_cost_{mode}_vary_{phase}_{week}_{day}` column when present, else falls back to base cost |
| 5.5 | Phase II & III: `vary_reason` present (`variation_reason_...` not NaN) | Reason text shown to participant explaining cost variation |
| 5.6 | Phase II & III: `variation_reason` is NaN | `vary_reason = None`, no explanation text rendered |
| 5.7 | Phase progression: complete Phase I → Phase II | `phaseI_total_budget`, `phaseI_emissions_saved`, `phaseI_choices` saved to participant vars |
| 5.8 | Phase II results page | Shows cumulative `phase_results` list including Phase I row; `total_budget`/`total_emissions_saved` include Phase I contributions |
| 5.9 | Phase III results page (final phase) | `next_phase = None`; phase_results includes Phase I & II; totals include all three phases |
| 5.10 | `SyncWaitPage` before `Instruction`/`WeekPreview`/`Results` in each phase | Displayed only for `advance_to_phase_III == True` participants |
| 5.11 | Timeout during Choice in Phase I/II/III (60s) | Default trip mode used, `timeout_occurred_choice=True`, round still progresses |
| 5.12 | Round 15 (`NUM_ROUNDS`) reached | Final `Results` page computes phase totals and (in Phase III) overall totals; app8 reachable next |
| 5.13 | `max_week` / `current_week` calculation across 15 rounds | `max_week = 15 // 5 = 3`; `current_week` increments correctly each 5 rounds |
| 5.14 | Token price persists correctly across Instruction → WeekPreview → Market at start of new phase | Uses `token_price_next_round` from previous phase, not hardcoded `INITIAL_PRICE`, unless it's the very first round |

---

## 6. App7 — Post-survey
| # | Test | Expected Result |
|---|------|------------------|
| 6.1 | `Literacy` page — 3 fields required | Cannot submit blank required field |
| 6.2 | `Survey1` — `familiar_currency = 'Other'` triggers `familiar_currency_other` free text | Conditional field behaves as expected (verify template logic even if not enforced server-side) |
| 6.3 | `Survey2` — rating fields (`fun_rating`, `difficulty_rating`, etc.) accept only choices 1–5 | Values outside {1..5} not selectable via radio UI |
| 6.4 | `Survey3` — multiple opinion/multi-select-style fields | All required fields validated; submission stores expected string codes |
| 6.5 | Complete all 4 survey pages in sequence | `page_sequence = [Literacy, Survey1, Survey2, Survey3]` order respected, no skipped pages |

---

## 7. App8 — Thank You
| # | Test | Expected Result |
|---|------|------------------|
| 7.1 | Reach final page | Displays final payoff / thank-you message, no further form fields |
| 7.2 | Attempt to navigate back and resubmit earlier apps | oTree prevents re-submission / back-button reuse of completed pages |

---

## 8. Cross-Cutting / Non-Functional
| # | Test | Expected Result |
|---|------|------------------|
| 8.1 | `clean_zero()` helper | `-0.00` normalized to `0.00`; values rounded to 2 decimals everywhere displayed |
| 8.2 | Missing/NaN CSV values (e.g. no stops for a trip) | `extract_stops` skips NaN/empty stop entries gracefully |
| 8.3 | Map image path `/static/maps/map_{code}_{day}.png` | Correct file resolves for every participant code / day combination in `choice_set.csv`; broken image if file missing |
| 8.4 | Emissions benchmark sentence for a very large saved value (> largest benchmark) | Falls back to largest bucket description, no crash |
| 8.5 | Emissions benchmark sentence for a tiny saved value (< smallest benchmark) | "You're approaching the CO₂eq emissions impact of..." fallback shown |
| 8.6 | Concurrent participants completing Phase III at different speeds | `group_by_arrival_time_method` correctly pairs/singles out only eligible participants without blocking others indefinitely |
| 8.7 | Admin export (oTree admin/data page) after a full run | All custom fields (`choice`, `budget`, `token`, `token_purchased`, `token_sold`, survey answers) present and correctly typed in export |
| 8.8 | Browser refresh mid-`Choice`/`Market` page (before submit) | No duplicate token purchase/sale or double budget deduction |
| 8.9 | Direct URL manipulation to skip ahead to a later round/app | oTree's page-sequence enforcement blocks out-of-order access |
| 8.10 | Full end-to-end run (App1 → App8) with a valid code | No exceptions in server log; final payoff = sum of Phase I–III weekly budgets; emissions total = sum of all phases |

---

### Notes for Testers
- Currency: DKK, 2 decimal places, no participation fee.
- Token price bounds: **1.00 – 100.00**, `PRICE_CHANGE_RATE = 0.05`.
- Transaction cost: **4 DKK** per non-zero market/auto trade; auto-purchase fee: **50 DKK**.
- Timeouts: Choice = 60s, Market = 60s (Phase II/III only — Test Phase I has no explicit timeout).
- Use multiple valid codes from `choice_set.csv` covering: all-commute weeks, weeks with `no_commute` days, and edge trips with missing stop data, to get full coverage.
