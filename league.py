"""League-wide schedule constants and ranking rules, shared by the
simulation (main.py, tourney.py) and the web app (app.py, show_*.py)."""

# Head-to-head weeks, in order
H2H_WEEKS = [1, 1.5, 2, 2.5]

# Tournament format for each of weeks 3-16
TOURNEY_TYPES = ['Random', 'Random', 'Division', 'Division', 'Score', 'Random',
                 'Division', 'Division', 'Score', 'Random', 'Random', 'Score',
                 'Division', 'Division']

FIRST_TOURNEY_WEEK = 3

# Playoff rounds 1-3, the weeks after the last tournament week
PLAYOFF_WEEKS = [17, 18, 19]


def game_pct(games):
    """Share of games won from a list of (won, played) pairs; 0 if none played."""
    won = sum(w for w, _ in games)
    played = sum(p for _, p in games)
    return won / played if played else 0


def record_key(scores, games):
    """Sort key for a team's score entries and the matching (won, played) game
    records, best first: total score, tournament wins (21s), H2H match wins
    (15s in the first 4 entries), then game win percentage. Rating is never
    a tiebreaker."""
    return (-sum(scores), -scores.count(21), -scores[:4].count(15), -game_pct(games))
