#***********************************************************************************************
# pages.py 
# 
# This file contains the __init__ part of many pages
#***********************************************************************************************

# Imports
import json
import pandas as pd
from _common.functions import *
import ast

#***********************************************************************************************
# Choice
#***********************************************************************************************
# vars_for_template
def choice_vars_for_template(player, NUM_ROUNDS, current_phase = 'V', choice='commute', AUTO_FEE=10, vary=False):
    # === Basic Setup ===
    trips = player.participant.vars['all_trips']
    trip_choices = player.participant.vars.get('trip_choices', [])
    trip_index = (player.round_number - 1) % len(trips)
    trip = trips[trip_index]
    buffer = trip['early_buffer']
    car_distance = trip['tour_total_distance_km_driving']

    # === Get mode ===
    poss_modes = trip.get('possible_modes')
    poss_modes = ast.literal_eval(poss_modes)


    # === Week and Day Calculations ===
    week = (player.round_number - 1) // len(trips) + 1
    day_in_week = trip_index + 1
    num_weeks = NUM_ROUNDS // len(trips)
    week_start = (week - 1) * len(trips)
    week_end = week_start + len(trips)

    # === Weekly Token Summary ===
    weekly_choices = trip_choices[week_start:week_end]
    preview_data, total_base, total_token_used = preview_overview_data(trips, weekly_choices=weekly_choices)

    # === Mode Information for Current Trip ===
    modes = choice_set(poss_modes, trip, vary = vary, current_phase=current_phase, week=week, day_in_week=day_in_week)
    raw_reason = trip.get(f'variation_reason_{current_phase}_{week}_{day_in_week}') if vary else None
    if pd.isna(raw_reason):
        vary_reason = None
    else:
        vary_reason = raw_reason

    # === Map Resource Path ===
    map_src = f"/static/maps/map_{player.participant.vars['entered_code']}_{trip['day']}.png"

    if player.round_number == 1 and player.budget is None:
        player.budget = player.participant.vars['initial_budget']
        player.token = player.participant.vars['initial_token']

    # === Return Context for Template ===
    context = dict(
            modes=modes,
            modes_js=json.dumps({m['mode']: m for m in modes}),
            budget=clean_zero(player.budget),
            round_number=player.round_number,
            num_rounds=NUM_ROUNDS,
            map_src=map_src,
            week=week,
            day_in_week=day_in_week,
            travel_day=trip['day'],
            work_arrival=trip['arrival_time_work'],
            work_departure=trip['departure_time_work'],
            preview_data=preview_data,
            preview_data_today=preview_data[trip_index],
            default_mode = trip['mode'],
            current_phase=current_phase,
            page_name='choice',
            max_week=num_weeks,
            num_trips=len(trips),
            buffer=buffer,
            token=int(player.token),
            token_price=clean_zero(player.group.token_price),
            total_base_token=total_base,
            total_token_used=total_token_used,
            car_distance=car_distance,
            auto_fee = AUTO_FEE,
            vary_reason=vary_reason
        )

    return context
        

#************************************
# before_next_page
def choice_before_next_page(player, NUM_ROUNDS, timeout_happened, current_phase='V', reduced=False, choice='commute', distance=False, AUTO_FEE=10, vary=False):
    # === Basic Setup ===
    player.participant.vars['token_price_history'].append(player.group.token_price)
    trips = player.participant.vars['all_trips']
    trip_index = (player.round_number - 1) % len(trips)
    trip = trips[trip_index]
    week = (player.round_number - 1) // len(trips) + 1
    day_in_week = trip_index + 1

    if choice != 'no_commute':
    # === Determine Default Mode Choice ===
        if timeout_happened:
            # Use the mode that was preselected for the trip
            mode = trip.get('mode')
            player.choice = mode
        else:
            mode = player.choice
    else:
        mode = 'no_commute'

    # === Calculate Cost and Token Requirement ===
    if choice == 'no_commute':
        cost = 0.0
        token_needed = 0
    else:
        base_cost = float(trip[f'tour_total_cost_{mode}'])
        if vary:
            vary_cost = trip.get(f'tour_total_cost_{mode}_vary_{current_phase}_{week}_{day_in_week}')
            cost = float(vary_cost) if vary_cost is not None and not pd.isna(vary_cost) else base_cost
        else:
            cost = base_cost
        token_needed = int(trip[f'tour_total_token_{mode}'])

    # === Handle Token Purchase if Needed ===
    if token_needed > player.token:
        token_to_buy = token_needed - player.token
        token_price = player.group.token_price
        purchase_cost = token_to_buy * token_price + AUTO_FEE

        player.budget -= purchase_cost
        player.token += token_to_buy
        player.participant.vars['pending_token_purchases'] = player.participant.vars.get('pending_token_purchases', 0) + token_to_buy
        player.group.token_price = max(1.0, clean_zero(player.group.token_price))
    player.token -= token_needed

    # === Deduct Trip Cost and Tokens ===
    player.budget -= cost

    # else: 
    #     mode = choice

    # === Prepare Next Round's Budget and Tokens ===
   # if choice != 'no_commute':
    # === Record the Player's Choice ===
    player.participant.vars['trip_choices'].append({
        'round': player.round_number,
        'choice': mode,
        'cost': cost,
        'token': player.token,
        'remaining_budget': player.budget,
        'remaining_token': player.token,
        'token_price': player.group.token_price
    })

    if player.round_number < NUM_ROUNDS:
        next_p = player.in_round(player.round_number + 1)
        if (player.round_number + 1) % len(trips) == 1:
            if reduced == True: 
                next_p.budget = player.participant.vars['initial_budget']
                next_p.token = int(player.participant.vars['initial_token_reduced'])
            elif distance:
                next_p.budget = player.participant.vars['initial_budget']
                next_p.token = int(player.participant.vars['initial_token_distance'])
            else:
                next_p.budget = player.participant.vars['initial_budget']
                next_p.token = int(player.participant.vars['initial_token'])
        else:
            next_p.budget = player.budget
            next_p.token = player.token

        next_p.group.token_price = player.group.token_price

    else:
        # === Record the Player's Choice ===
        if choice != 'no_commute':
            player.participant.vars['trip_choices'].append({
                'round': player.round_number,
                'choice': mode,
                'cost': cost,
                'remaining_budget': player.budget
            })
        else:
            player.participant.vars['trip_choices'].append({
                'round': player.round_number,
                'choice': mode,
                'remaining_budget': player.budget
            })          
        
        if player.round_number < NUM_ROUNDS:
            next_p = player.in_round(player.round_number + 1)
            if (player.round_number + 1) % 5 == 1:
                next_p.budget = player.participant.vars['initial_budget']
            else:
                next_p.budget = player.budget

  

#***********************************************************************************************
# Market
#***********************************************************************************************
# vars_for_template
def market_vars_for_template(player, DAY_ABBREVIATIONS, NUM_ROUNDS, TRANSACTION_COSTS, PRICE_CHANGE_RATE, current_phase = 'V', vary=False):
    # === Basic Setup ===
    trips = player.participant.vars['all_trips']
    trip_choices = player.participant.vars.get('trip_choices', [])
    token_price_history = player.participant.vars.get('token_price_history', []).copy()
    trip_index = (player.round_number - 1) % len(trips)
    trip = trips[trip_index]
    buffer = trip['early_buffer']

    # === Get mode ===
    poss_modes = trip.get('possible_modes')
    poss_modes = ast.literal_eval(poss_modes)


    # === Day Labels for Graphs with Phase Headers ===
    day_labels = []
    rounds_per_phase = 2 * len(trips)
    PHASE_ORDER = ['I', 'II', 'III']
    num_phases = (len(token_price_history) + rounds_per_phase - 1) // rounds_per_phase
    current_phase_index = PHASE_ORDER.index(current_phase) if current_phase in PHASE_ORDER else -1

    for i in range(len(token_price_history)):
        phase_index = i // rounds_per_phase
        if phase_index < current_phase_index:
            # Previous phases: use phase label
            if i % rounds_per_phase == 0:
                day_labels.append(f"Phase {PHASE_ORDER[phase_index]}")
            else:
                day_labels.append("")
        else:
            # Current or future phase: use weekday and week number
            week = (i // len(trips)) + 1
            day = trips[i % len(trips)].get('day', f'Day {i + 1}')
            short_day = DAY_ABBREVIATIONS.get(day, f'D{i}')
            day_labels.append(f"{short_day}")


    # === Week & Day Tracking ===
    week = (player.round_number - 1) // len(trips) + 1
    max_week = NUM_ROUNDS // len(trips)
    day_in_week = trip_index + 1

    # === Token Requirements ===
    min_required_token = min(
        trip.get(f'tour_total_token_{mode}', float('inf'))
        for mode in poss_modes
        if isinstance(trip.get(f'tour_total_token_{mode}'), (int, float))
    )

    # === Remaining Max Token for This Week ===
    remaining_trips = trips[trip_index:]
    remaining_max_token = sum(
        t.get('tour_total_token_max', 0)
        for t in remaining_trips
        if isinstance(t.get('tour_total_token_max', 0), (int, float))
    )

    absolute_max_token = max(
        trip.get('tour_total_token_max', 0)
        for trip in player.participant.vars['all_trips']
        if isinstance(trip.get('tour_total_token_max'), (int, float))
    )

    # === Weekly Token Summary ===
    week_start = (week - 1) * len(trips)
    week_end = week_start + len(trips)
    weekly_choices = trip_choices[week_start:week_end]
    preview_data, total_base, total_token_used = preview_overview_data(trips, weekly_choices=weekly_choices)
    token_substract =  total_token_used if isinstance(total_token_used, (int, float)) else 0


    # === Mode Information for Current Trip ===
    modes = choice_set(poss_modes, trip, vary=vary, current_phase=current_phase, week=week, day_in_week=day_in_week)

    # === Final Context for Template Rendering ===
    return dict(
        absolute_max_token=absolute_max_token,
        budget=clean_zero(player.budget),
        day_in_week=day_in_week,
        default_mode=trip['mode'],
        max_token=int(remaining_max_token),
        max_week=max_week,
        min_required_token=0 if pd.isna(min_required_token) else int(min_required_token),
        modes=modes,
        modes_js=json.dumps({m['mode']: m for m in modes}),
        preview_data=preview_data,
        preview_data_today=preview_data[trip_index],
        token=int(player.token),
        token_day_labels_js=json.dumps(day_labels),
        token_price=clean_zero(player.group.token_price),
        token_price_history_js=json.dumps(token_price_history),
        total_base_token=total_base,
        total_token_used=total_token_used,
        transaction_costs=TRANSACTION_COSTS,
        week=week,
        current_phase=current_phase,
        page_name='market',
        num_trips=len(trips),
        buffer=buffer,
        price_change_rate=PRICE_CHANGE_RATE
    )

#************************************
# before_next_page
def market_before_next_page(player, NUM_ROUNDS, TRANSACTION_COSTS, PRICE_CHANGE_RATE, reduced=False, distance=False):
    # === Token Transactions ===
    pending_sales = player.participant.vars.get('pending_token_sales', 0)
    pending_purchases = player.participant.vars.get('pending_token_purchases', 0)
    token_price = player.group.token_price
    net_token = player.token_purchased - player.token_sold
    pending_token = pending_purchases - pending_sales
    transaction_costs = TRANSACTION_COSTS if (player.token_purchased > 0 or player.token_sold > 0) else 0

    # === Budget and Token Updates ===
    player.budget -= player.token_purchased * token_price
    player.budget += player.token_sold * token_price
    player.budget -= transaction_costs
    player.token += net_token

    # === Setup Next Round's Budget and Token ===
    if player.round_number < NUM_ROUNDS:
        next_p = player.in_round(player.round_number + 1)
        
        # Reset budget and token at the start of each week
        if (player.round_number + 1) % 5 == 1:
            if reduced == True: 
                next_p.budget = player.participant.vars['initial_budget']
                next_p.token = int(player.participant.vars['initial_token_reduced'])
            elif distance:
                next_p.budget = player.participant.vars['initial_budget']
                next_p.token = int(player.participant.vars['initial_token_distance'])
            else:
                next_p.budget = player.participant.vars['initial_budget']
                next_p.token = int(player.participant.vars['initial_token'])
        else:
            next_p.budget = player.budget
            next_p.token = player.token

    player.participant.vars['pending_token_purchases'] = 0
    player.participant.vars['pending_token_sales'] = 0


#***********************************************************************************************
# Results
#***********************************************************************************************
# vars_for_template
def results_vars_for_template(player, NUM_ROUNDS, TRANSACTION_COSTS, INITIAL_PRICE, reduced=False, current_phase = 'V', distance=False):
    # === Setup Week and Round Info ===
    trips = player.participant.vars['all_trips']
    trip_choices = player.participant.vars['trip_choices']
    num_weeks = NUM_ROUNDS // len(trips)
    current_week = (player.round_number - 1) // len(trips) + 1
    next_week = current_week + 1
    PHASE_ORDER = ['I','II','III']

    # === Retrieve Data ===
    sellback_key = f'sellback_{current_phase}_round_{player.round_number}'
    cached_sellback = player.participant.vars.get(sellback_key)

    token_price = player.group.token_price
    if token_price is None:
        token_price = INITIAL_PRICE

    if cached_sellback is not None:
        # Page already rendered once this round (e.g. a refresh) — reuse
        # those numbers instead of recomputing from player.token, which is
        # already 0 by now.
        remaining_token = cached_sellback['token_sold']
        sellback_earnings = cached_sellback['sellback_earnings']
        transaction_costs = cached_sellback['transaction_costs']
        token_price = cached_sellback['token_price']
    else:
        # === Sell Remaining Tokens (first render this round) ===
        remaining_token = player.token
        transaction_costs = TRANSACTION_COSTS if remaining_token > 0 else 0
        sellback_earnings = clean_zero(remaining_token * token_price - transaction_costs)
        if current_phase == 'testI':
            sellback_earnings = clean_zero(remaining_token * token_price)

        player.budget += sellback_earnings
        player.token = 0
        player.participant.vars['pending_token_sales'] = player.participant.vars.get('pending_token_sales', 0) + remaining_token
        player.participant.vars[sellback_key] = {
            'token_sold': remaining_token,
            'sellback_earnings': sellback_earnings,
            'transaction_costs': transaction_costs,
            'token_price': token_price,
        }

    # === Weekly Summary Calculation ===
    weekly_summary = []
    for week in range(num_weeks):
        start_round = week * len(trips)
        end_round = start_round + len(trips)
        week_choices = trip_choices[start_round:end_round]
        week_trips = trips[start_round % len(trips): (start_round % len(trips)) + len(trips)]

        # Get base budget and apply sellback earnings if this is the current week
        if week_choices:
            base_budget = week_choices[-1]['remaining_budget']
            week_budget = base_budget + sellback_earnings if (week + 1 == current_week) else base_budget
        else:
            week_budget = 0

        # Calculate emissions
        base_emissions = sum(t.get('tour_total_CO2_kg_base_mode') for t in week_trips)

        actual_emissions = 0
        for t, c in zip(week_trips, week_choices):
            mode = c.get('choice')
            if mode != 'no_commute':
                actual_emissions += t.get(f'tour_total_CO2_kg_{mode}', 0)
        diff_emissions = base_emissions - actual_emissions


        # Append weekly results
        weekly_summary.append({
            'week': week + 1,
            'budget': clean_zero(week_budget),
            'baseline_emissions': clean_zero(base_emissions),
            'actual_emissions': clean_zero(actual_emissions),
            'emissions_saved': clean_zero(diff_emissions),
            'emissions_excess': clean_zero(abs(diff_emissions)) if diff_emissions < 0 else None
        })

    # === Accumulate Totals ===
    if current_phase in ['I', 'II', 'III']:
        total_budget = sum(w['budget'] for w in weekly_summary)
    else: 
        total_budget = 0
    
    # Emissions from current phase
    current_phase_emissions = sum(w['emissions_saved'] for w in weekly_summary if w['week'] <= current_week)

    # Emissions from previous phases (Phase I, II, III, etc.)
    previous_emissions = sum(
        player.participant.vars.get(f'phase{phase}_emissions_saved', 0)
        for phase in PHASE_ORDER
        if phase != current_phase and player.participant.vars.get(f'phase{phase}_emissions_saved') is not None
    )

    # Total accumulated
    total_emissions_saved = current_phase_emissions + previous_emissions

    # === Payoff ===
    player.payoff = total_budget

    if current_phase not in ['testI', 'testII']:
        # === Handle Phase Progression ===
        current_phase_index = PHASE_ORDER.index(current_phase)
        previous_phases = PHASE_ORDER[:current_phase_index]
        try:
            next_phase = PHASE_ORDER[current_phase_index + 1]
        except IndexError:
            next_phase = None 

        # === Phase Results Summary ===
        phase_results = []
        for phase in previous_phases:
            budget = player.participant.vars.get(f'phase{phase}_total_budget')
            emissions = player.participant.vars.get(f'phase{phase}_emissions_saved')

            # Only include if both are present
            if budget is not None and emissions is not None:
                phase_results.append({
                    'name': f'Phase {phase}',
                    'budget': clean_zero(budget),
                    'emissions_saved': clean_zero(emissions)
                })

                # Only count Phase IV and above toward total payoff
                if phase in ['I', 'II', 'III']:
                    total_budget += budget
                    total_emissions_saved += emissions

        # === Save Current Phase Results ===
        player.participant.vars[f'phase{current_phase}_total_budget'] = total_budget
        player.participant.vars[f'phase{current_phase}_emissions_saved'] = current_phase_emissions
        player.participant.vars[f'phase{current_phase}_choices'] = player.participant.vars.get('trip_choices', []).copy()

    else:
        # === For Test Phases, Set Next Phase to None ===
        next_phase = None
        phase_results = []

    # === Weekly Preview Overview ===
    week_start = (week - 1) * len(trips)
    week_end = week_start + len(trips)
    weekly_choices = trip_choices[week_start:week_end]
    preview_data, total_base, _ = preview_overview_data(trips, weekly_choices=weekly_choices)

    # === Return Template Data ===
    context = dict(
        weekly_summary=weekly_summary,
        current_week=current_week,
        preview_data=preview_data,
        next_week=next_week,
        budget_init = clean_zero(player.participant.vars['initial_budget']),
        current_phase=current_phase,
        next_phase=next_phase,
        total_budget=clean_zero(total_budget),
        total_emissions_saved=clean_zero(total_emissions_saved),
        max_week = num_weeks,
        page_name='results',
        emissions_equivalent_sentence=get_emissions_equivalent(total_emissions_saved),
        token_price=clean_zero(token_price),
        total_base_token=total_base,
        sellback_earnings=sellback_earnings,
        token_sold=remaining_token,
        budget=clean_zero(player.budget),
        token=player.token,
        token_init = (
            player.participant.vars['initial_token_reduced'] if reduced
            else player.participant.vars['initial_token_distance'] if distance
            else player.participant.vars['initial_token']
        ),        
        transaction_costs = transaction_costs,
        phase_results=phase_results
    )

    return context