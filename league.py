"""League-wide schedule constants and ranking rules, shared by the
simulation (main.py, tourney.py) and the web app (app.py, show_*.py)."""

# Head-to-head weeks, in order
H2H_WEEKS = [1, 1.5, 2, 2.5]

# Tournament format for each of weeks 3-16
TOURNEY_TYPES = ['Random', 'Random', 'Division', 'Division', 'Score', 'Random',
                 'Division', 'Division', 'Score', 'Random', 'Random', 'Score',
                 'Division', 'Division']

FIRST_TOURNEY_WEEK = 3


def record_key(scores):
    """Sort key for a list of score entries, best first: total score,
    tournament wins (21s), then H2H match wins (15s in the first 4 entries)."""
    return (-sum(scores), -scores.count(21), -scores[:4].count(15))
