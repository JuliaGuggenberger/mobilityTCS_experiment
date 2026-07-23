from otree.api import *
from _common.functions import *
from _common.pages import *

doc = """
    Phase I
"""

#*************************************************************************************************
# CONFIGURATION
class C(BaseConstants):
    NAME_IN_URL = 'app4_phaseI'
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
    token_price_after_market = models.FloatField()

class Player(BasePlayer):
    choice = models.StringField()
    budget = models.FloatField()
    token = models.IntegerField()
    token_old = models.IntegerField()
    token_purchased = models.IntegerField(initial=0,min=0)
    token_sold = models.IntegerField(initial=0,min=0)
    payoff_deter = models.StringField(
        choices=[('1', 'Your performance in the upcoming phases'), ('2', 'Your performance of in the upcoming and previous phases'), ('3', 'Your final payoff is independent of you performance'),],
        label="What determines your final payoff?",
        widget=widgets.RadioSelect,
        blank=False
    )
    token_price = models.StringField(
        choices=[('1', 'No, only to the next week'), ('2', 'Yes, it will be taken over'), ('3', 'No, the token price resets for the next phase'),],
        label="Will the token price be taken over to the next phase?",
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
        group.token_price_after_market = group.token_price 
        for p in players:
            p.participant.vars['pending_token_purchases'] = 0
            p.participant.vars['pending_token_sales'] = 0
            p.participant.vars['token_price_next_round'] = group.token_price

# ======== Instruction ========
class Instruction(Page):
    form_model = 'player'
    form_fields = ['payoff_deter', 'token_price']

    @staticmethod
    def error_message(player, values):
        correct_answers = {'payoff_deter': '1', 'token_price': '2'}
    
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
        # Initialize Week and Budget
        player.budget = player.participant.vars['initial_budget']
        player.token_old = player.participant.vars['initial_token']
        player.token = player.participant.vars['initial_token_reduced']
        player.group.token_price = player.participant.vars.get('token_price_next_round', C.INITIAL_PRICE)

        # Return Template Variables
        return dict(
            budget=clean_zero(player.budget),
            token=int(player.token_old),
            token_reduced=int(player.token),
            token_price=clean_zero(player.group.token_price),
            page_name='intro',
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
        player.group.token_price = C.INITIAL_PRICE

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
            current_phase='I',
            page_name='weekpreview'
        )
    
    def before_next_page(player, timeout_happened):
        player.participant.vars['token_price_history'] = [C.INITIAL_PRICE]

        
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
        return choice_vars_for_template(player, C.NUM_ROUNDS, current_phase = 'I', AUTO_FEE=C.AUTO_FEE)
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        if timeout_happened:
            player.timeout_occurred_choice = True
        return choice_before_next_page(player, C.NUM_ROUNDS, timeout_happened, current_phase = 'I', reduced=True, AUTO_FEE=C.AUTO_FEE)


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
        return choice_vars_for_template(player, C.NUM_ROUNDS, current_phase = 'I')

    @staticmethod
    def before_next_page(player, timeout_happened):
        return choice_before_next_page(player, C.NUM_ROUNDS, timeout_happened, current_phase = 'I', reduced=True, choice='no_commute')


class Market(Page):
    timeout_seconds = timeout_sec('market')

    form_model = 'player'
    form_fields = ['token_purchased', 'token_sold']

    @staticmethod
    def vars_for_template(player):
        return market_vars_for_template(player, C.DAY_ABBREVIATIONS, C.NUM_ROUNDS, C.TRANSACTION_COSTS, C.PRICE_CHANGE_RATE, current_phase = 'I')


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
        return results_vars_for_template(player, C.NUM_ROUNDS, C.TRANSACTION_COSTS, C.INITIAL_PRICE, reduced=True, current_phase='I', PRICE_CHANGE_RATE=C.PRICE_CHANGE_RATE)

page_sequence = [SyncWaitPage, Instruction, SyncWaitPage, WeekPreview, SyncWaitPage, Market, MarketWaitPage, NoCommute, Choice, SyncWaitPage, Results]