import os
from pathlib import Path
from os import environ

# ==============================================================================
# oTree Session Configuration
# ==============================================================================

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

SESSION_CONFIGS = [
    dict(
        name='mobilityTCS_experiment',
        app_sequence=[
            'app1_intro',
            'app2_testI', 'app3_testII',
            'app4_phaseI', 'app5_phaseII', 'app6_phaseIII', 
            'app7_postsurvey', 'app8_thankyou'
            ],
        num_demo_participants=2,
        group_by_arrival_time=True,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00, 
    doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

ROOMS = [
    dict(
        name='LEE',
        display_name='LEE',
        participant_label_file='Participants.txt',
    ),
]


# ==============================================================================
# Templates
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / '_templates'],  # <-- this enables global templates like 'global/token_overview.html'
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ==============================================================================
# Misc oTree / Django Settings
# ==============================================================================
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'DKK'
REAL_WORLD_CURRENCY_DECIMAL_PLACES = 2
USE_POINTS = False

ADMIN_USERNAME = 'admin'
# ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '4066956229700'