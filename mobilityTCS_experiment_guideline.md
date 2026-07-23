# mobilityTCS_experiment — Detailed Guideline

Purpose of this document: a map of the codebase so that when something needs to change (a rule, a price, a payoff cap, a survey question...), you know **exactly which file/constant/function to touch** and **what else depends on it**.

---

## 1. Big picture

```
settings.py  → defines SESSION_CONFIGS (app order), currency, rooms
app1_intro   → participant enters their personal code, code is matched against
               app1_intro/choice_set.csv, comprehension quiz on the rules
app2_testI   → practice round: choose travel mode only (no market)
app3_testII  → practice round: choose travel mode + trade tokens (fixed-ish price)
app4_phaseI  → paid week 1 (choice + market, price moves)
app5_phaseII → paid week 2 (identical structure to app4)
app6_phaseIII→ paid week 3 (identical structure, only for participants
               flagged advance_to_phase_III during app1)
app7_postsurvey → financial literacy + attitude survey, computes final payoff
app8_thankyou   → displays final payoff (recomputed as fallback)
```

`app4_phaseI`, `app5_phaseII`, `app6_phaseIII` are **near-duplicates of each other**. If you change game logic (market math, choice logic), you almost always need to change it in **all three**, or better: change it once in `_common/pages.py` and `_common/functions.py`, since all three call the same shared functions. Only `current_phase` label (`'I'`, `'II'`, `'III'`) differs between them.

`app2_testI` and `app3_testII` are the "training" versions — same shared functions, but simpler (`app2` has no market, `app3` has a market but is a rehearsal, not paid).

---

## 2. Where the actual logic lives

- **`_common/functions.py`** — pure helper functions used everywhere:
  - `timeout_sec(page)` — timeout in seconds per page type (`'market'`, `'choice'`, default `60`). **Change this to adjust how long participants have per page.**
  - `clean_zero(x)` — rounds to 2 decimals, turns `-0.00` into `0.00`.
  - `format_minutes_to_hm(total_minutes)` — formats duration for display.
  - `preview_overview_data(trips, weekly_choices)` — builds the weekly trip-preview table (used on WeekPreview/Choice/Market/Results pages).
  - `choice_set(poss_modes, trip, vary, current_phase, week, day_in_week)` — builds the list of mode options (time/cost/tokens/rating) shown on the Choice/Market page. **If you add a new travel mode or a new displayed attribute, edit here.**
  - `EMISSIONS_BENCHMARKS` — list of `(description, kg CO2)` tuples used for the "you saved as much CO2 as..." message. **Add/edit entries here to change the comparison scale.**
  - `get_emissions_equivalent(saved_emissions)` — picks the right benchmark sentence.

- **`_common/pages.py`** — shared page behaviour, imported and called by app2–app6's `__init__.py`:
  - `choice_vars_for_template(...)` / `choice_before_next_page(...)` — everything about picking a mode: computes cost, deducts budget/tokens, auto-buys missing tokens (charging `AUTO_FEE`), carries budget/tokens into the next round, resets them at the start of each week.
  - `market_vars_for_template(...)` / `market_before_next_page(...)` — builds the trading UI data (price history chart, min/max tokens) and applies buy/sell transactions, `TRANSACTION_COSTS`, and updates `group.token_price` via `PRICE_CHANGE_RATE`.
  - `results_vars_for_template(...)` — weekly summary page: sells back leftover tokens automatically, computes emissions saved vs. baseline, accumulates payoff across phases (`phase{X}_total_budget`, `phase{X}_emissions_saved` in `participant.vars`), decides `next_phase`.
  - `PHASE_ORDER = ['I','II','III']` (defined **twice**, once in each of these two functions — see §5 gotchas).

- **Each `appN.../__init__.py`** — just wires the shared functions together with that app's own `C` constants and its own `page_sequence`. Very little unique logic (mostly in app1, app7, app8).

---

## 3. Full constant reference (`class C(BaseConstants)`)

### Present in every app
| Constant | Meaning | Safe to change? |
|---|---|---|
| `NAME_IN_URL` | URL slug for the app | Yes, but must stay unique and match any hardcoded references (none found) |
| `PLAYERS_PER_GROUP` | oTree group size; `None` = everyone in one group per session config | Changing this changes how `Group`-level state (e.g. `token_price`) is shared — currently every player effectively has their own "market" since grouping is by arrival time with group size 1 (see `group_by_arrival_time_method`) |
| `NUM_ROUNDS` | number of rounds (= trips) in this app | Must stay a multiple of the number of trips per week (5) for the weekly reset logic (`% 5`, `% len(trips)`) to line up. Changing it changes how many weeks the app covers |

### Market / pricing (app2–app6, `app1` has `INITIAL_PRICE` only)
| Constant | Meaning | Effect if changed |
|---|---|---|
| `INITIAL_PRICE` | starting token price (DKK/token) | Changes the price shown at the very first Instruction/WeekPreview page and used before any trading happens |
| `PRICE_CHANGE_RATE` | price sensitivity to net tokens traded | `new_price = old_price + net_tokens_traded * PRICE_CHANGE_RATE`, clamped to `[1.0, 100.0]` (hardcoded, not a constant — see §5). Increase for more volatile prices |
| `TRANSACTION_COSTS` | flat fee charged when a player buys/sells any token in the Market page | Only charged if `token_purchased > 0` or `token_sold > 0` for that round |
| `AUTO_FEE` | fee charged when a player doesn't have enough tokens for their chosen mode and the system auto-buys the shortfall | Applies in `choice_before_next_page`; also applied on timeout auto-submit |
| `DAY_ABBREVIATIONS` | dict `{'Monday':'Mo', ...}` for the price-history chart x-axis labels | Purely cosmetic |

### Payoff (app7, app8 — **must be kept identical in both files**, see §5)
| Constant | Meaning |
|---|---|
| `MIN_PAYOFF` | payoff floor for non-candidates (participants whose raw total ≤ `CAP_PAYOFF`) |
| `CAP_PAYOFF` | threshold above which a participant becomes a "high-pay candidate"; non-winners among candidates are capped here |
| `MAX_WINNER_PAYOFF` | ceiling for the one randomly-drawn "winner" among high-pay candidates |

### app1 only
| Constant | Meaning |
|---|---|
| `APP_DIR` | auto-computed (`os.path.dirname(__file__)`) — don't hand-edit |
| `TRAVEL_DIARY_PATH` | path to `choice_set.csv`, the per-participant trip-data source |

---

## 4. Payoff logic in detail (app7 → app8)

1. `app7_postsurvey`, page `Survey3.before_next_page`:
   - Draws **one** session-wide "winner" (`session.vars['highpay_winner_code']`) at random from all participants whose `payoff_plus_participation_fee() > CAP_PAYOFF`. This runs only once per session (guarded by `if 'highpay_winner_code' not in session.vars`).
   - For the *current* participant: if not a candidate → payoff clamped to `[MIN_PAYOFF, CAP_PAYOFF]`. If a candidate but not the winner → payoff = `CAP_PAYOFF`. If the winner → payoff = `min(base_total, MAX_WINNER_PAYOFF)`.
   - Result is rounded up to the nearest 5 (`-(-x // 5) * 5`).
   - Stored in `participant.vars['final_total']`, `['base_total']`, `['is_candidate']`, `['is_winner']`; official oTree `player.payoff` / `participant.payoff` is set to `final_total - participation_fee`.
2. `app8_thankyou`, `Subsession.creating_session()` **also** tries to draw a winner the same way — this is redundant with app7 and only kicks in if app7's step didn't already set `session.vars['highpay_winner_code']`. Keep this consistent if you change the winner-selection rule.
3. `ThankYou.vars_for_template` mostly re-displays `participant.vars['final_total']` / `['base_total']` with a fallback recomputation.

**If you change the payoff scheme:** edit the constants in both `app7_postsurvey/__init__.py` and `app8_thankyou/__init__.py` (currently duplicated by hand — no shared constants file for these), and update the logic in `Survey3.before_next_page` (source of truth) and, if needed, `Subsession.creating_session` / `ThankYou.vars_for_template` (fallback) in app8.

---

## 5. Gotchas / duplicated logic (things easy to break)

- **`PHASE_ORDER = ['I','II','III']`** is hardcoded in *two places* inside `_common/pages.py` (`market_vars_for_template` and `results_vars_for_template`). If you add a 4th phase, update both.
- **Price clamp `[1.0, 100.0]`** is hardcoded (not a constant) in several places: the `MarketWaitPage.after_all_players_arrive` of app3/app4/app5/app6 `__init__.py`, and again in `results_vars_for_template`. Search for `min(100.0, max(1.0,` if you need to change the price floor/ceiling.
- **`AUTO_FEE`, `TRANSACTION_COSTS`, `PRICE_CHANGE_RATE`, `DAY_ABBREVIATIONS`** are each defined separately per app (`app2`...`app6`) rather than imported from one place — a change needs to be repeated in each app's `__init__.py` that should use the new value.
- **`app4_phaseI`, `app5_phaseII`, `app6_phaseIII` are nearly line-for-line identical** — the only differences are `current_phase` strings passed to shared functions and (for app6) whatever extra gating exists for `advance_to_phase_III`. When fixing a bug in the market/choice flow, fix it in all three (or better, move the fix into `_common/pages.py` if the logic is truly identical).
- **Weekly length is hardcoded as `5`** in several places (`% 5 == 1`, `% 5 == 0` for Results page and budget/token reset), separately from `len(trips)` used elsewhere. If the CSV's number of trips per week ever isn't 5, these two need to be reconciled.
- **`group_by_arrival_time_method`** in app3–app6 only ever returns a group of size 1 (single eligible participant), effectively meaning each participant has their own private "market"/group — despite the market code being written as if multiple players could share a group and trade against each other. Relevant if you ever want genuinely shared/multiplayer markets.
- **Sellback/session state caching**: `results_vars_for_template` caches its computed sellback numbers in `participant.vars[f'sellback_{phase}_round_{round}']` to survive page refreshes. If you change what happens on Results, make sure this cache key logic still matches (otherwise a page refresh will show stale numbers or double-charge).

---

## 6. Common change scenarios → where to edit

| I want to... | Edit |
|---|---|
| Change how long participants get per page | `_common/functions.py` → `timeout_sec()` |
| Change token price sensitivity | `PRICE_CHANGE_RATE` in each app's `C` class (app3–app6) |
| Change the flat trading fee | `TRANSACTION_COSTS` in each app's `C` class (app2–app6) |
| Change the "not enough tokens" penalty | `AUTO_FEE` in each app's `C` class (app2–app6) |
| Add/remove a week (round of 5 trips) | `NUM_ROUNDS` in app2–app6's `C` class, **and** make sure `choice_set.csv` has enough trip rows per participant |
| Change payoff floor/cap/winner-bonus | `MIN_PAYOFF` / `CAP_PAYOFF` / `MAX_WINNER_PAYOFF` in **both** `app7_postsurvey/__init__.py` and `app8_thankyou/__init__.py` |
| Add a new travel mode (e.g. e-scooter) | `_common/functions.py` → `choice_set()` (reads `tour_total_*_{mode}` and `rating_{mode}` columns); add matching columns to `choice_set.csv`; update HTML templates that hardcode mode icons/labels |
| Change/add a comprehension-quiz question | The relevant app's `Player` fields + `Instruction`/`Introduction` page's `form_fields` and `error_message` correct-answers dict (app1, app3, app4/5/6) |
| Add/remove a post-survey question | `app7_postsurvey/__init__.py` → add a `Player` field, add it to the right `SurveyN.form_fields` list, and update the matching `.html` template |
| Change the CO₂ comparison sentence scale | `_common/functions.py` → `EMISSIONS_BENCHMARKS` |
| Change the app order / session name / currency | `settings.py` → `SESSION_CONFIGS`, `REAL_WORLD_CURRENCY_CODE`, etc. |
| Change who can reach app6 (Phase III) | `participant.vars['advance_to_phase_III']`, set in `app1_intro/__init__.py` `CodeEntry.before_next_page` (currently always `True` — no actual filtering condition is applied there yet) |

---

## 7. Data dependency: `app1_intro/choice_set.csv`

One row per participant (`id_code`) per day (`day_number`). Required columns (non-exhaustive, as referenced in code):
- Identity/day: `id_code`, `day_number`, `day`, `mode`, `possible_modes` (stringified Python list), `early_buffer`
- Budgets: `total_monetary_budget_per_id`, `total_token_budget_per_id`, `total_token_budget_reduced_per_id`, `total_token_budget_distance_per_id`
- Trip geography/timing: `morning_origin`, `morning_destination`, `morning_loc_stop{1-4}`, `morning_stop{1-4}_reason`, `evening_...` equivalents, `arrival_time_work`, `departure_time_work`
- Per-mode figures (repeated for each mode in `possible_modes`, e.g. `car`, `bike`, `pt`): `tour_total_duration_min_{mode}`, `tour_total_cost_{mode}`, `tour_total_token_{mode}`, `rating_{mode}`, `tour_total_CO2_kg_{mode}`
- Base/reference: `tour_total_token_base_mode`, `tour_total_CO2_kg_base_mode`, `tour_total_distance_km_driving`, `tour_total_token_max`
- Variation (only used if `vary=True` is passed — currently unused by any app's `__init__.py`, but supported by the shared functions): `tour_total_cost_{mode}_vary_{phase}_{week}_{day}`, `variation_reason_{phase}_{week}_{day}`

If you add a participant, they need a full set of day rows in this CSV under a unique `id_code` — that code is what's typed into `CodeEntry`.

---

## 8. Runtime state (not config, but worth knowing when debugging)

Stored in `participant.vars` across the whole session (survives app changes):
`all_trips`, `trip_choices`, `initial_budget`, `initial_token`, `initial_token_reduced`, `initial_token_distance`, `token_price_history`, `advance_to_phase_III`, `pending_token_purchases`, `pending_token_sales`, `token_price_next_round`, `code_invalid`, `phase{I,II,III}_total_budget`, `phase{I,II,III}_emissions_saved`, `phase{I,II,III}_choices`, `sellback_{phase}_round_{n}`, `base_total`, `final_total`, `is_candidate`, `is_winner`.

Stored in `session.vars`: `highpay_winner_code` (set once per session).
