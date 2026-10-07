# scoring_config.py
"""
Centralized Configuration for Agent Decision Making
Modify these weights to change how the system plans the trip.
"""

SCORING_WEIGHTS = {
    "hotel": {
        "rating_weight": 10.0,
        "budget_penalty_per_dollar": 0.5, # Penalty applied for every dollar over budget
    },
    "weather": {
        "rain_penalty": -30.0,            # Penalty for outdoor activities if raining
        "extreme_heat_penalty": -15.0     # Penalty for extreme temperatures (>35C)
    },
    "news_sentiment": {
        "negative_political_news_penalty": -50.0, # Avoid areas with unrest
        "positive_economic_news_bonus": 10.0
    }
}

SEARCH_CONSTRAINTS = {
    "country_limit": "Sri Lanka",
    "max_activities_per_day": 3
}
