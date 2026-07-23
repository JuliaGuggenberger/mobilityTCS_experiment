from otree.api import *
from _common.functions import *
from _common.pages import *

doc = """
    Phase II
"""

#*************************************************************************************************
# CONFIGURATION
class C(BaseConstants):
    NAME_IN_URL = 'app5_phaseII'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 15
    INITIAL_PRICE = 10.00
    PRICE_CHANGE_RATE = 0.05
    TRANSACTION_COSTS = 4
    AUTO_FEE = 50

    DAY_ABBREVIATIONS = {'Monday': 'Mo','Tuesday': 'Tu','Wednesday': 'We','Thursday': 'Th',
                         'Friday': 'Fr','Saturday': 'Sa','Sunday': 'Su'}

#*************************************************************************************************
# MODELS
class Subsession(BaseSubsession):
    def group_by_arrival_time_method(self, waiting_players):
        # Only group one eligible participant at a time
        for p in waiting_players:
            if p.participant.vars.get('advance_to_phase_III', False):
                return [p]
            
class Group(BaseGroup):
    token_price = models.FloatField(initial=C.INITIAL_PRICE)

class Player(BasePlayer):
    choice = models.StringField()
    budget = models.FloatField()
    token = models.IntegerField()
    token_old = models.IntegerField()
    token_purchased = models.IntegerField(initial=0,min=0)
    token_sold = models.IntegerField(initial=0,min=0)
    cost_change = models.StringField(
        choices=[('1', 'Because the distances of the trip are changed'), ('2', 'Because conditions such as weather, congestion, or events affect travel effort and time'), ('3', 'There is no reason for the cost changes'),],
        label="Why can the cost of a travel mode for the same trip change from one day to the next?",
        widget=widgets.RadioSelect,
        blank=False
    )
    timeout_occurred_choice = models.BooleanField(initial=False)
    timeout_occurred_market = models.BooleanField(initial=False)

#*******************************************************************************************************************
# PAGES
class SyncWaitPage(WaitPage):
    body_text = "Waiting for other participants to proceed..."

    @staticmethod
    def is_displayed(player):
        return player.participant.vars.get('advance_to_phase_III', False)
    
class ConditionalChoiceOrNoCommuteWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player):
        # Only show this wait page to players who have the *same* trip type
        trips = player.participant.vars['all_trips']
        index = (player.round_number - 1) % len(trips)
        current_mode = trips[index].get('mode')
        return current_mode != 'no_commute'  # only Choice players wait

    @staticmethod
    def after_all_players_arrive(group):
        pass  # optional synchronization logic

class MarketWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group):
        players = group.get_players()
        total_net = sum(p.token_purchased - p.token_sold for p in players)
        total_pending = sum(
            p.participant.vars.get('pending_token_purchases', 0) -
            p.participant.vars.get('pending_token_sales', 0)
            for p in players
        )
        new_price = group.token_price + (total_net + total_pending) * C.PRICE_CHANGE_RATE
        group.token_price = min(100.0, max(1.0, clean_zero(new_price)))
        for p in players:
            p.participant.vars['pending_token_purchases'] = 0
            p.participant.vars['pending_token_sales'] = 0
            p.participant.vars['token_price_next_round'] = group.token_price

# ======== Instruction ========
class Instruction(Page):
    form_model = 'player'
    form_fields = ['cost_change']

    @staticmethod
    def error_message(player, values):
        correct_answers = {'cost_change': '2'}
    
        errors = {}
        for field, correct in correct_answers.items():
            if values.get(field) != correct:
                errors[field] = "Incorrect. Please review this part."
        
        return errors or None


    @staticmethod
    def is_displayed(player):
        return player.round_number == 1 

    @staticmethod
    def vars_for_template(player):    
        # Load Trip Data for Preview
        trips = player.participant.vars['all_trips']
        trip_index = (player.round_number - 1) % len(trips)
        while trip_index < len(trips) and trips[trip_index]['mode'] == 'no_commute':
            trip_index += 1
        player.participant.vars['trip_choices'] = []
        trip = trips[trip_index]
        buffer = trip['early_buffer']
        preview_data, total_base, _ = preview_overview_data(trips, weekly_choices=False)

        # === Mode Information for Current Trip ===
        poss_modes = trip.get('possible_modes')
        poss_modes = ast.literal_eval(poss_modes)
        modes = choice_set(poss_modes, trip, vary = False, current_phase='I', week=0, day_in_week=0)

        # Return Template Variables
        return dict(
            budget=clean_zero(player.participant.vars['initial_budget']),
            token=int(player.participant.vars['initial_token']),
            token_price=clean_zero(player.group.token_price),
            default_mode=trip['mode'],
            preview_data=preview_data,
            total_base_token=total_base,
            page_name='weekpreview',
            buffer=buffer,
            modes=modes,
        ) 

# ======== WeekPreview ========
class WeekPreview(Page):
    timeout_seconds = timeout_sec('else')

    @staticmethod
    def is_displayed(player):
        return (
            player.round_number == 1 and
            player.participant.vars.get('advance_to_phase_III', False)
        )

    @staticmethod
    def vars_for_template(player):
        # Initialize Week and Budget
        current_week = (player.round_number - 1) // 5 + 1
        player.budget = player.participant.vars['initial_budget']
        player.token = player.participant.vars['initial_token_reduced']
        player.group.token_price = player.participant.vars.get('token_price_next_round', C.INITIAL_PRICE)

        #  Reset all market-related state
        player.participant.vars['pending_token_purchases'] = 0
        player.participant.vars['pending_token_sales'] = 0
        player.token_purchased = 0
        player.token_sold = 0

        # Load Trip Data for Preview 
        trips = player.participant.vars['all_trips']
        player.participant.vars['trip_choices'] = []
        preview_data, total_base, _ = preview_overview_data(trips, weekly_choices=False)

        # Return Template Variables
        return dict(
            budget=clean_zero(player.budget),
            token=int(player.token),
            token_price=clean_zero(player.group.token_price),
            preview_data=preview_data,
            current_week=current_week,
            total_base_token=total_base,
            current_phase='II',
            page_name='weekpreview'
        )
    
class Choice(Page):
    timeout_seconds = timeout_sec('choice')

    form_model = 'player'
    form_fields = ['choice']

    timeout_submission = {'choice': 'AUTO'}

    @staticmethod
    def is_displayed(player):
        trips = player.participant.vars['all_trips']
        index = (player.round_number - 1) % len(trips)
        trip = trips[index]
        return trip.get('mode') != 'no_commute'

    @staticmethod
    def vars_for_template(player):
        return choice_vars_for_template(player, C.NUM_ROUNDS, current_phase = 'II', AUTO_FEE=C.AUTO_FEE, vary=True)
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened:
            player.timeout_occurred_choice = True
        return choice_before_next_page(player, C.NUM_ROUNDS, timeout_happened, current_phase = 'II', reduced=True, AUTO_FEE=C.AUTO_FEE, vary=True)


class NoCommute(Page):
    timeout_seconds = timeout_sec('choice')

    @staticmethod
    def is_displayed(player):
        trips = player.participant.vars['all_trips']
        index = (player.round_number - 1) % len(trips)
        trip = trips[index]
        return trip.get('mode') == 'no_commute'

    @staticmethod
    def vars_for_template(player):
        return choice_vars_for_template(player, C.NUM_ROUNDS, current_phase = 'II')

    @staticmethod
    def before_next_page(player, timeout_happened):
        return choice_before_next_page(player, C.NUM_ROUNDS, timeout_happened, current_phase = 'II', reduced=True, choice='no_commute')


class Market(Page):
    timeout_seconds = timeout_sec('market')

    form_model = 'player'
    form_fields = ['token_purchased', 'token_sold']

    @staticmethod
    def vars_for_template(player):
        return market_vars_for_template(player, C.DAY_ABBREVIATIONS, C.NUM_ROUNDS, C.TRANSACTION_COSTS, C.PRICE_CHANGE_RATE, current_phase = 'II',vary=True)


    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened:
            player.timeout_occurred_market = True
        return market_before_next_page(player, C.NUM_ROUNDS, C.TRANSACTION_COSTS, C.PRICE_CHANGE_RATE, reduced = False)


class Results(Page):
    timeout_seconds = timeout_sec()

    @staticmethod
    def is_displayed(player):
        return player.round_number % 5 == 0

    @staticmethod
    def vars_for_template(player):
        return results_vars_for_template(player, C.NUM_ROUNDS, C.TRANSACTION_COSTS, C.INITIAL_PRICE, reduced=True, current_phase='II')

page_sequence = [SyncWaitPage, Instruction, SyncWaitPage, WeekPreview, SyncWaitPage, Market, MarketWaitPage, NoCommute, Choice, SyncWaitPage, Results]