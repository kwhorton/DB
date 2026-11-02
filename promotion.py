"""Promotion and relegation between tiers at the end of the season.

Tiers 1-3: the bottom 4 teams by record are relegated to the next tier down.
Tiers 2-4: the top 2 teams by record are promoted automatically, and the two
best playoff finishers among the other teams are promoted too.

Standings use the same record_key order as everywhere else, over the
regular season only (playoff results never add to team.score).
"""
from league import record_key, FIRST_TOURNEY_WEEK, TOURNEY_TYPES, PLAYOFF_WEEKS
from playoffs import playoff_seeds

AUTO_PROMOTE = 2
PLAYOFF_PROMOTE = 2
RELEGATE = 4
LAST_REGULAR_WEEK = FIRST_TOURNEY_WEEK + len(TOURNEY_TYPES) - 1


def promotion_picture(tier, tiers, teams, n, rounds, current_week):
    """Who is promoted or relegated as of current_week, given the first n
    regular-season score entries and the tier's playoff rounds.

    Returns a dict:
      can_promote / can_relegate - whether this tier has each zone
      started  - any results in yet (no zones before Week 1)
      final    - the regular season is over, so the record-based zones are set
      auto     - [team] top 2 by record (promoted)
      relegated- [team] bottom 4 by record
      playoff  - [team] the 2 playoff promotions, once the Final Four is played
      contenders - [team] teams still able to earn a playoff promotion
      status   - {team_name: 'auto' | 'playoff' | 'relegated'}
      chasers / survivors - the first teams outside each zone, with point gaps
    """
    pos = tiers.index(tier)
    can_promote = pos > 0
    can_relegate = pos < len(tiers) - 1
    ranked = sorted(teams, key=lambda t: record_key(t.score[:n], t.games[:n]))
    pts = {t: sum(t.score[:n]) for t in ranked}

    auto = ranked[:AUTO_PROMOTE] if can_promote and n else []
    relegated = ranked[-RELEGATE:] if can_relegate and n else []
    final = current_week >= LAST_REGULAR_WEEK

    # Playoff path: field narrows round by round; decided after the Final Four
    playoff, contenders = [], []
    if can_promote and final:
        played = [r for r, week in zip(rounds, PLAYOFF_WEEKS) if week <= current_week]
        if len(played) == len(PLAYOFF_WEEKS):
            playoff = [t for t in played[-1].finish_order if t not in auto][:PLAYOFF_PROMOTE]
        else:
            # Before Round 1 the whole field (bye teams too); then the next round's field
            alive = rounds[len(played)].team_list if 0 < len(played) < len(rounds) else playoff_seeds(teams, n)
            contenders = [t for t in alive if t not in auto]

    def gaps(teams_out, edge):
        return [{'team': t, 'gap': abs(pts[edge] - pts[t]), 'score': pts[t]} for t in teams_out]

    chasers = gaps(ranked[AUTO_PROMOTE:AUTO_PROMOTE + 2], auto[-1]) if auto else []
    survivors = gaps(ranked[-RELEGATE - 2:-RELEGATE][::-1], relegated[0]) if relegated else []

    status = {}
    for t in relegated:
        status[t.team_name] = 'relegated'
    for t in playoff:
        status[t.team_name] = 'playoff'
    for t in auto:
        status[t.team_name] = 'auto'

    return {
        'can_promote': can_promote,
        'can_relegate': can_relegate,
        'started': n > 0,
        'final': final,
        'playoffs_decided': bool(playoff),
        'auto': [{'team': t, 'score': pts[t]} for t in auto],
        'relegated': [{'team': t, 'score': pts[t]} for t in relegated],
        'playoff': playoff,
        'contenders': contenders,
        'status': status,
        'chasers': chasers,
        'survivors': survivors,
        'up_tier': tiers[pos - 1] if can_promote else None,
        'down_tier': tiers[pos + 1] if can_relegate else None,
        'last_week': LAST_REGULAR_WEEK,
    }
