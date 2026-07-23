from otree.api import *
from _common.functions import *
from _common.pages import *

doc = """
    Test Phase I
"""

#*************************************************************************************************
# CONFIGURATION
class C(BaseConstants):
    NAME_IN_URL = 'app2_testI'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 5
    INITIAL_PRICE = 10.00
    TRANSACTION_COSTS = 4
    AUTO_FEE = 50

#*************************************************************************************************
# MODELS
class Subsession(BaseSubsession):
    pass
            
class Group(BaseGroup):
    token_price = models.FloatField(initial=C.INITIAL_PRICE)
    token_price_after_market = models.FloatField()

class Player(BasePlayer):
    choice = models.StringField()
    budget = models.FloatField()
    token = models.IntegerField()

#*******************************************************************************************************************
# PAGES
# ======== WeekPreview ========
class WeekPreview(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        # Initialize Week and Budget
        current_week = (player.round_number - 1) // 5 + 1
        player.budget = player.participant.vars['initial_budget']
        player.token = player.participant.vars['initial_token']
        player.group.token_price = C.INITIAL_PRICE

        # Load Trip Data for Preview
        trips = player.participant.vars['all_trips']
        player.participant.vars['trip_choices'] = []
        preview_data, total_base, _ = preview_overview_data(trips, weekly_choices=False)

        # Return Template Variables
        return dict(
            budget=clean_zero(player.budget),
            token=int(player.token),
            token_price=round(player.group.token_price, 2),
            preview_data=preview_data,
            current_week=current_week,
            total_base_token=total_base,
            current_phase='testI',
            page_name='weekpreview'
        )
    
# ======== Choice ========
class Choice(Page):
    form_model = 'player'
    form_fields = ['choice']

    @staticmethod
    def is_displayed(player):
        trips = player.participant.vars['all_trips']
        index = (player.round_number - 1) % len(trips)
        trip = trips[index]
        return trip.get('mode') != 'no_commute'

    @staticmethod
    def vars_for_template(player):
        return choice_vars_for_template(player, C.NUM_ROUNDS, current_phase = 'testI', AUTO_FEE=C.AUTO_FEE)

    
    @staticmethod
    def before_next_page(player, timeout_happened):
        return choice_before_next_page(player, C.NUM_ROUNDS, timeout_happened, current_phase = 'testI', AUTO_FEE=C.AUTO_FEE)

# ======== NoCommute ========
class NoCommute(Page):
    @staticmethod
    def is_displayed(player):
        trips = player.participant.vars['all_trips']
        index = (player.round_number - 1) % len(trips)
        trip = trips[index]
        return trip.get('mode') == 'no_commute'

    @staticmethod
    def vars_for_template(player):
        return choice_vars_for_template(player, C.NUM_ROUNDS, current_phase = 'testI')
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        return choice_before_next_page(player, C.NUM_ROUNDS, timeout_happened, current_phase = 'testI', choice='no_commute')

# ======== Results ========
class Results(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number % 5 == 0

    @staticmethod
    def vars_for_template(player):
        return results_vars_for_template(player, C.NUM_ROUNDS, C.TRANSACTION_COSTS, C.INITIAL_PRICE, current_phase='testI')


page_sequence = [WeekPreview, NoCommute, Choice, Results]