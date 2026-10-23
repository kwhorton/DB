"""League news for the home page: short articles about the week just played
and the one coming up.

Each storyline detector reads the season as of a week and returns Storylines:
a kind, a priority (how newsworthy it is), a subject (the team or player it is
about) and the facts behind it. Renderers turn those facts into a headline and
a few paragraphs of template prose. Nothing here knows about Flask; app.py
picks the articles for the current tier and week."""

import random
import zlib
from dataclasses import dataclass, field

from awards import match_mvp, event_leaders
from league import (H2H_WEEKS, TOURNEY_TYPES, FIRST_TOURNEY_WEEK, PLAYOFF_WEEKS,
                    PLAYOFF_ROUND_NAMES, record_key)
from playoffs import playoff_seeds
from show_standings import (WEEKS, results_before, results_through, snapshot, ranked,
                            team_rating, rating_week_for, division_place, ordinal)
from tourney import subtype_of

# Seed pairs in each 8-team bracket's opening round, as Tournament.run_tourney
# and PlayoffRound.run_qualifier play them (0 is the top seed)
FIRST_ROUND = [(0, 7), (3, 4), (2, 5), (1, 6)]

# A win over a team rated at least this much higher counts as an upset
UPSET_GAP = 30

# A single-match line needs this many hits per five games (a full tournament
# match) to be a story of its own; head-to-head matches run much longer
STAR_HITS = 7

# Articles shown, the lead story included
ARTICLES = 4


@dataclass
class Storyline:
    kind: str
    priority: float
    subject: str            # the team or player the story is about, for dedup
    facts: dict = field(default_factory=dict)


# ---------------------------------------------------------------- helpers

def name(player):
    return player.name.title()


NUMBER_WORDS = ['zero', 'one', 'two', 'three', 'four', 'five',
                'six', 'seven', 'eight', 'nine', 'ten']


def number(n):
    """Small counts as words ('three'), larger ones as digits."""
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)


def plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def counted(n, one, many=None):
    """plural() with small counts as words: 'three matches'."""
    return f"{number(n)} {one if n == 1 else (many or one + 's')}"



def join(items):
    """'A', 'A and B', 'A, B and C'"""
    items = list(items)
    if len(items) <= 1:
        return ''.join(items)
    return ', '.join(items[:-1]) + ' and ' + items[-1]


def score(match):
    """The match score from the winner's side, e.g. '3–1'."""
    return f"{max(match.match_score)}–{min(match.match_score)}"


def week_label(week):
    return f"Week {week:g}"


def standing(teams, n):
    """Teams best first by record through n score entries."""
    return sorted(teams, key=lambda t: record_key(t.score[:n], t.games[:n]))


def tourney_name(tourney, all_tourneys):
    sub = subtype_of(tourney, all_tourneys)
    if tourney.type == 'Division':
        return f"the {sub} Division tournament"
    if tourney.type == 'Score':
        return f"the {sub} Score bracket"
    return "a Random-draw bracket"


def h2h_record(team, n):
    """(wins, losses) in head-to-head matches through n score entries."""
    played = team.score[:min(n, len(H2H_WEEKS))]
    wins = played.count(15)
    return wins, len(played) - wins


def trailing(scores, value):
    """How many of the last entries in scores equal value."""
    count = 0
    for s in reversed(scores):
        if s != value:
            break
        count += 1
    return count


class Season:
    """One tier's season as of a selected week, with the lookups every
    detector needs."""

    def __init__(self, tier, tier_data, awards, current_week):
        self.tier = tier
        self.teams = tier_data['teams']
        self.schedule = tier_data['schedule']
        self.all_tourneys = tier_data['all_tourneys']
        self.playoff_rounds = tier_data.get('playoff_rounds', [])
        self.awards = awards
        self.current_week = current_week

        # The regular-season week to recap, and the week to preview
        played = [w for w in WEEKS if w <= current_week]
        self.week = played[-1] if played else None
        self.next_week = next((w for w in WEEKS + PLAYOFF_WEEKS if w > current_week), None)

        self.n = results_through(current_week)
        self.n_before = results_before(self.week) if self.week else 0
        self.now = standing(self.teams, self.n)
        self.before = standing(self.teams, self.n_before)
        self.rank = {t.team_name: i for i, t in enumerate(self.now, start=1)}
        self.rank_before = {t.team_name: i for i, t in enumerate(self.before, start=1)}

        rw = rating_week_for(self.week or 0)
        self.rating = {t.team_name: team_rating(t, rw) for t in self.teams}
        by_rating = sorted(self.teams, key=lambda t: -self.rating[t.team_name])
        self.rating_rank = {t.team_name: i for i, t in enumerate(by_rating, start=1)}

    def points(self, team, n=None):
        return sum(team.score[:self.n if n is None else n])

    def week_matches(self, week):
        return [m for m in self.schedule if m.week == week]

    def week_tourneys(self, week):
        return [t for t in self.all_tourneys if t.week == week]

    def team_tourney(self, team, week):
        return next((t for t in self.week_tourneys(week) if team in t.team_list), None)

    def rng(self, *key):
        """A random source fixed by tier, week and story, so an article reads
        the same every time it's shown."""
        seed = '|'.join(str(k) for k in (self.tier, self.current_week) + key)
        return random.Random(zlib.crc32(seed.encode()))


# ------------------------------------------------- detectors: week recaps

def tournament_recaps(s):
    """Each tournament's winner, scored up for low seeds, long matches,
    unbeaten runs and title streaks."""
    stories = []
    for t in s.week_tourneys(s.week):
        champ = t.finish_order[0]
        seed = t.team_list.index(champ) + 1
        field_by_rating = sorted(t.team_list, key=lambda team: -s.rating[team.team_name])
        rating_rank = field_by_rating.index(champ) + 1
        played = [m for m in t.matches if champ in (m.team1, m.team2)]
        path = [(m, m.get_wl_teams()[0] is champ) for m in played]
        losses = sum(1 for _, won in path if not won)
        five_games = sum(1 for m in played if min(m.match_score) == 2)
        titles = champ.score[:s.n].count(21)
        streak = trailing(champ.score[:s.n], 21)
        name_ = champ.team_name
        jump = s.rank_before[name_] - s.rank[name_] if s.n_before else 0

        if streak >= 2:
            variant = 'streak'
        elif seed >= 5 or (seed >= 3 and rating_rank >= 6):
            variant = 'underdog'
        elif losses == 0:
            variant = 'unbeaten'
        else:
            variant = 'default'

        priority = (34 + 4 * (seed - 1) + 2 * (rating_rank - 1) + 3 * five_games
                    + (6 if losses == 0 else 0) + 6 * (streak - 1)
                    + (4 if titles == 1 else 0) + max(jump, 0))
        stories.append(Storyline('tournament', priority, name_, dict(
            variant=variant, tourney=t, champ=champ, seed=seed, field_size=len(t.team_list),
            rating_rank=rating_rank, path=path, losses=losses, five_games=five_games,
            titles=titles, streak=streak, jump=jump, final=played[-1],
            # A 17th match is the second final, played when the losers-bracket team wins the first
            reset=len(t.matches) == 17)))
    return stories


def snapped_streaks(s):
    """Teams whose run of tournament titles ended this week."""
    stories = []
    for team in s.teams:
        streak = trailing(team.score[:s.n_before], 21)
        if streak < 2 or team.score[s.n - 1] == 21:
            continue
        t = s.team_tourney(team, s.week)
        if t is None:
            continue
        beaten_by = [(m.get_wl_teams()[0], m) for m in t.matches
                     if team in (m.team1, m.team2) and m.get_wl_teams()[1] is team]
        stories.append(Storyline('snapped', 38 + 8 * streak, team.team_name, dict(
            team=team, streak=streak, tourney=t, place=t.finish_order.index(team) + 1,
            beaten_by=beaten_by)))
    return stories


def upsets(s):
    """The week's biggest win by a lower-rated team (and the runner-up, for
    a mention)."""
    found = []
    for m in s.week_matches(s.week):
        winner, loser = m.get_wl_teams()
        gap = s.rating[loser.team_name] - s.rating[winner.team_name]
        if gap >= UPSET_GAP:
            found.append((gap, m, winner, loser))
    if not found:
        return []
    found.sort(key=lambda f: -f[0])
    gap, m, winner, loser = found[0]
    return [Storyline('upset', 25 + gap / 3, winner.team_name, dict(
        match=m, winner=winner, loser=loser,
        tourney=s.team_tourney(winner, s.week) if m.match_type == 'T' else None,
        also=[(f[2], f[3], f[1]) for f in found[1:2]]))]


def sweeps(s):
    """Head-to-head weeks: the most one-sided 3–0 sweep."""
    best = None
    for m in s.week_matches(s.week):
        if m.match_type != 'H' or min(m.match_score) != 0:
            continue
        conceded = sum(games[2 - m.winner] for games in m.set_results)
        if best is None or conceded < best[0]:
            best = (conceded, m)
    if best is None or best[0] > 4:
        return []
    conceded, m = best
    winner, loser = m.get_wl_teams()
    return [Storyline('sweep', 18 + 2 * (6 - conceded), winner.team_name, dict(
        match=m, winner=winner, loser=loser, conceded=conceded, sets=len(m.set_results)))]


def unbeaten(s):
    """Head-to-head weeks: the teams still perfect."""
    if s.week not in H2H_WEEKS or s.n < 2:
        return []
    perfect = [t for t in s.now if h2h_record(t, s.n)[1] == 0]
    if not 1 <= len(perfect) <= 6:
        return []
    return [Storyline('unbeaten', 26 + 3 * (6 - len(perfect)), perfect[0].team_name, dict(
        teams=perfect, wins=h2h_record(perfect[0], s.n)[0]))]


def standings_shakeup(s):
    """Changes at the top, in the division races and at the playoff line,
    plus where the bubble teams play next."""
    if not s.n_before:
        return []
    leader, leader_before = s.now[0], s.before[0]
    second = s.now[1]
    margin = s.points(leader) - s.points(second)
    margin_before = s.points(leader_before, s.n_before) - s.points(s.before[1], s.n_before)

    def division_leaders(order):
        seen = {}
        for team in order:
            seen.setdefault(team.division, team)
        return seen

    leaders_now, leaders_then = division_leaders(s.now), division_leaders(s.before)
    new_div_leaders = [team for div, team in sorted(leaders_now.items())
                       if leaders_then[div] is not team and team is not leader]

    seeds = playoff_seeds(s.teams, s.n)
    seeds_before = playoff_seeds(s.teams, s.n_before)
    # Biggest moves first
    def move(t):
        return s.rank_before[t.team_name] - s.rank[t.team_name]
    entered = sorted((t for t in s.now if t in seeds and t not in seeds_before), key=move, reverse=True)
    dropped = sorted((t for t in s.now if t in seeds_before and t not in seeds), key=move)
    first_out = next(t for t in s.now if t not in seeds)
    last_in = [t for t in s.now if t in seeds and t not in leaders_now.values()][-1]
    gap = s.points(last_in) - s.points(first_out)

    new_leader = leader is not leader_before
    priority = (25 + (15 if new_leader else 0) + 6 * len(new_div_leaders)
                + 5 * len(entered + dropped) + (8 if gap <= 3 else 0))
    if not (new_leader or new_div_leaders or entered or dropped or gap <= 6):
        return []
    subject = (dropped or entered or [leader])[0].team_name
    return [Storyline('standings', priority, subject, dict(
        leader=leader, leader_before=leader_before, second=second, new_leader=new_leader,
        margin=margin, margin_before=margin_before, new_div_leaders=new_div_leaders,
        entered=entered, dropped=dropped, last_in=last_in, first_out=first_out, gap=gap,
        seed_count=len(seeds)))]


def player_of_week(s):
    rows = s.awards.player_of_week(s.week)
    if not rows:
        return []
    top = rows[0]
    return [Storyline('potw', 30, top['pid'], dict(
        row=top, line=s.awards.by_week[s.week][top['pid']],
        runner_up=rows[1] if len(rows) > 1 else None))]


def star_performance(s):
    """The week's best single-match line, by hits per five games, then catches."""
    best = None
    for m in s.week_matches(s.week):
        mvp = match_mvp(m)
        if mvp is None:
            continue
        key = (5 * mvp['impact'].hits / len(m.games), mvp['impact'].catches)
        if best is None or key > best[0]:
            best = (key, m, mvp)
    if best is None or best[0][0] < STAR_HITS:
        return []
    (rate, _), m, mvp = best
    winner, loser = m.get_wl_teams()
    return [Storyline('star', 20 + 2 * rate, mvp['pid'], dict(
        match=m, mvp=mvp, won=mvp['team'] is winner,
        opponent=loser if mvp['team'] is winner else winner))]


def mvp_race(s):
    rows = s.awards.season_race(s.week)
    if len(rows) < 2:
        return []
    leader, second = rows[0], rows[1]
    climber = next((r for r in rows[1:5] if r['move'] >= 3), None)
    new_leader = leader['prev_rank'] not in (None, 1)
    priority = 18 + (15 if new_leader else 0) + (3 * climber['move'] if climber else 0)
    return [Storyline('race', priority, leader['pid'], dict(
        leader=leader, second=second, new_leader=new_leader, climber=climber,
        margin=leader['above_avg'] - second['above_avg']))]


# --------------------------------------------------- detectors: previews

def h2h_preview(s):
    """The next head-to-head week's best matchup, by standing (or by rating
    before any games)."""
    matches = s.week_matches(s.next_week)
    order = s.rank if s.n else s.rating_rank
    matches.sort(key=lambda m: order[m.team1.team_name] + order[m.team2.team_name])
    n, rw = snapshot(s.next_week, s.current_week)

    def side(team):
        return dict(team=team, rank=order[team.team_name], points=s.points(team),
                    place=division_place(team, s.teams, n, rw), record=h2h_record(team, n))

    pairs = [(side(m.team1), side(m.team2)) for m in matches]
    return [Storyline('h2h_preview', 42, 'preview:h2h', dict(
        pairs=pairs, by_rating=not s.n))]


def tournament_preview(s):
    """The bracket with the tier leader in it, with its projected first round,
    plus any team chasing a title streak."""
    n, rw = snapshot(s.next_week, s.current_week)
    groups = []
    for t in s.week_tourneys(s.next_week):
        seeded = [team for team, _ in ranked(t.team_list, n, rw)]
        groups.append((t, seeded))
    if not groups:
        return []
    leader = s.now[0]
    t, seeded = next(((t, sd) for t, sd in groups if leader in sd), groups[0])
    pairs = [(seeded[a], seeded[b]) for a, b in FIRST_ROUND]
    # The opening-round pairing between the two best-placed teams, other than
    # 1 v 8, if both are in playoff position
    pick = min(pairs[1:], key=lambda p: s.rank[p[0].team_name] + s.rank[p[1].team_name])
    seeds = playoff_seeds(s.teams, s.n)
    if not (pick[0] in seeds and pick[1] in seeds):
        pick = None
    streaks = [(team, trailing(team.score[:s.n], 21)) for team in s.now
               if trailing(team.score[:s.n], 21) >= 2]
    return [Storyline('tourney_preview', 42, f"preview:{t.id}", dict(
        tourney=t, seeded=seeded, pairs=pairs, pick=pick, streaks=streaks,
        type=TOURNEY_TYPES[int(s.next_week) - FIRST_TOURNEY_WEEK], groups=groups))]


def preseason(s):
    """Before Week 1: the tier's highest-rated teams."""
    favorites = sorted(s.teams, key=lambda t: -s.rating[t.team_name])[:3]
    return [Storyline('preseason', 45, favorites[0].team_name, dict(favorites=favorites))]


def field_set(s):
    """After Week 16: the playoff field and its byes."""
    seeds = playoff_seeds(s.teams, s.n)
    qualifier = seeds[4:]
    pairs = [(qualifier[a], qualifier[b]) for a, b in FIRST_ROUND]
    first_out = next(t for t in s.now if t not in seeds)
    return [Storyline('field_set', 55, seeds[0].team_name, dict(
        seeds=seeds, pairs=pairs, first_out=first_out,
        gap=s.points(seeds[-1]) - s.points(first_out)))]


def playoff_recap(s):
    """Rounds 1 and 2: who advanced, and the best seed knocked out."""
    index = PLAYOFF_WEEKS.index(s.current_week) if s.current_week in PLAYOFF_WEEKS else None
    if index is None or index >= len(s.playoff_rounds):
        return []
    rnd = s.playoff_rounds[index]
    seeds = playoff_seeds(s.teams)
    seed_of = {t: i for i, t in enumerate(seeds, start=1)}
    if rnd.finish_order:
        return champion(s, rnd, seed_of)
    out = [t for t in rnd.team_list if t not in rnd.advancers]
    mvp = event_leaders(rnd.matches)[0]
    best_out = min(out, key=seed_of.get)
    return [Storyline('playoff_round', 60, f"round:{index}", dict(
        name=PLAYOFF_ROUND_NAMES[index], advancers=sorted(rnd.advancers, key=seed_of.get),
        out=out, best_out=best_out, seed_of=seed_of, mvp=mvp,
        # A team from the top half of this round's field went out
        upset=rnd.team_list.index(best_out) < len(rnd.team_list) // 2))]


def champion(s, rnd, seed_of):
    champ, runner_up = rnd.finish_order[:2]
    final = rnd.matches[-1]
    awards = s.awards.playoff_awards
    return [Storyline('champion', 70, champ.team_name, dict(
        champ=champ, runner_up=runner_up, third=rnd.finish_order[2], final=final,
        reset=rnd.labels[-1] != 'Championship', seed_of=seed_of,
        playoff_mvp=awards.get('Playoff MVP'), final_four_mvp=awards.get('Final Four MVP')))]


def playoff_preview(s):
    """The next playoff round's field, once the round before it is played."""
    index = PLAYOFF_WEEKS.index(s.next_week)
    if index == 0 or index >= len(s.playoff_rounds):
        return []
    rnd = s.playoff_rounds[index]
    seed_of = {t: i for i, t in enumerate(playoff_seeds(s.teams), start=1)}
    order = rnd.team_list
    pairs = ([(order[a], order[b]) for a, b in FIRST_ROUND] if len(order) == 8
             else [(order[0], order[3]), (order[1], order[2])])
    return [Storyline('playoff_preview', 55, f"preview:{index}", dict(
        name=PLAYOFF_ROUND_NAMES[index], pairs=pairs, seed_of=seed_of,
        byes=order[:4] if index == 1 else []))]


def storylines(s):
    """Every storyline for the season as of the selected week."""
    found = []
    if s.current_week <= WEEKS[-1] and s.week is not None:
        is_tourney = s.week not in H2H_WEEKS
        detectors = [upsets, standings_shakeup, player_of_week, star_performance, mvp_race]
        detectors += [tournament_recaps, snapped_streaks] if is_tourney else [sweeps, unbeaten]
        for detect in detectors:
            found += detect(s)
    elif s.current_week > WEEKS[-1]:
        found += playoff_recap(s)

    if s.next_week is None:
        pass
    elif s.next_week in H2H_WEEKS:
        found += h2h_preview(s)
        if s.week is None:
            found += preseason(s)
    elif s.next_week in PLAYOFF_WEEKS:
        found += field_set(s) if s.next_week == PLAYOFF_WEEKS[0] else playoff_preview(s)
    else:
        found += tournament_preview(s)
    return found


# -------------------------------------------------------------- renderers
# Each takes (season, facts, rng) and returns (headline, [paragraphs]).

def render_tournament(s, f, rng):
    champ, t = f['champ'].team_name, f['tourney']
    where = tourney_name(t, s.all_tourneys)
    seed = f"No. {f['seed']} seed"

    if f['variant'] == 'underdog':
        headline = rng.choice([f"{champ} pulls off a {seed} title run",
                               f"Underdog {champ} wins {where.replace('the ', '', 1)}",
                               f"{champ} crashes the party as a {seed}"])
        size = f['field_size']
        if f['rating_rank'] == size:
            rated = "the lowest-rated team in the field"
        elif f['rating_rank'] == size - 1:
            rated = "one of its two lowest-rated teams"
        else:
            rated = "one of its lower-rated teams"
        lead = f"{champ} came into {where} as the {seed} and {rated}, and left with the title."
    elif f['variant'] == 'streak':
        headline = rng.choice([f"{champ} makes it {number(f['streak'])} straight",
                               f"{champ}'s winning streak reaches {counted(f['streak'], 'title')}",
                               f"Nobody can stop {champ}"])
        lead = f"{champ} won {where} for its {ordinal(f['streak'])} straight tournament title"
        lead += (", every title it has won this season." if f['titles'] == f['streak']
                 else f" and its {ordinal(f['titles'])} of the season.")
    elif f['variant'] == 'unbeaten':
        headline = rng.choice([f"{champ} runs the table",
                               f"Perfect week for {champ}",
                               f"{champ} goes unbeaten to win {where.replace('the ', '', 1)}"])
        lead = f"{champ} didn't lose a match on its way to winning {where}."
    else:
        headline = rng.choice([f"{champ} wins {where.replace('the ', '', 1)}",
                               f"{champ} takes the title"])
        lead = f"{champ} won {where} as the {seed}."

    if f['five_games'] == len(f['path']) and f['five_games'] >= 3:
        lead += f" Every one of its {number(len(f['path']))} matches went the full five games."
    elif f['five_games'] >= 2:
        lead += f" {number(f['five_games']).capitalize()} of its matches went the distance."

    # The path to the final, with back-to-back wins (or losses) under one verb
    final = f['final']
    before_final = [(m, won) for m, won in f['path'] if m is not final]
    if f['reset']:
        before_final = before_final[:-1]
    runs = []
    for m, won in before_final:
        opp = (m.team2 if m.team1 is f['champ'] else m.team1).team_name
        if runs and runs[-1][0] == won:
            runs[-1][1].append(f"{opp} {score(m)}")
        else:
            runs.append((won, [f"{opp} {score(m)}"]))
    steps = [("beat " if won else "lost to ") + join(games) for won, games in runs]
    path = f"Along the way it {', '.join(steps)}" if steps else "It went straight to the final"
    final_opp = (final.team2 if final.team1 is f['champ'] else final.team1).team_name
    if f['reset']:
        first = f['path'][-2]
        if first[1]:
            path += f", then had to beat {final_opp} twice in the final, {score(first[0])} and {score(final)}."
        else:
            path += (f", then dropped the first final to {final_opp} {score(first[0])} "
                     f"before winning the deciding rematch {score(final)}.")
    else:
        path += f", then beat {final_opp} {score(final)} in the final."
    mvp = match_mvp(final)
    if mvp and mvp['team'] is f['champ']:
        path += (f" {name(mvp['player'])} was MVP of the final with "
                 f"{plural(mvp['impact'].hits, 'hit')}.")

    if f['jump'] >= 2:
        move = f"The 21 points lifted {champ} from {ordinal(s.rank_before[champ])} to {ordinal(s.rank[champ])}."
    elif s.rank[champ] == 1:
        move = f"{champ} stays first in {s.tier}."
    else:
        move = f"{champ} sits {ordinal(s.rank[champ])} in {s.tier} with {s.points(f['champ'])} points."
    if f['titles'] == 1 and f['variant'] != 'streak':
        move += " It was the team's first title of the season."
    return headline, [lead, path, move]


def render_snapped(s, f, rng):
    team = f['team'].team_name
    headline = rng.choice([f"{team}'s streak ends at {number(f['streak'])}",
                           f"{team} finally falls",
                           f"The run is over for {team}"])
    lead = (f"{team} had won {number(f['streak'])} straight tournaments, but finished "
            f"{ordinal(f['place'])} in {tourney_name(f['tourney'], s.all_tourneys)}.")
    losses = [f"{w.team_name} ({score(m)})" for w, m in f['beaten_by']]
    body = [lead, f"It lost to {join(losses)}."] if losses else [lead]
    if s.rank[team] == 1:
        body.append(f"{team} still leads {s.tier}, but its lead over {s.now[1].team_name} "
                    f"is down to {plural(s.points(f['team']) - s.points(s.now[1]), 'point')}.")
    else:
        body.append(f"It is now {ordinal(s.rank[team])}, down from {ordinal(s.rank_before[team])}.")
    return headline, body


def render_upset(s, f, rng):
    w, l, m = f['winner'].team_name, f['loser'].team_name, f['match']
    headline = rng.choice([f"{w} stuns {l}", f"Upset: {w} topples {l}",
                           f"{w} knocks off {l}"])
    where = (f" in {tourney_name(f['tourney'], s.all_tourneys)}" if f['tourney']
             else f" in {week_label(s.week)} head-to-head play")
    body = [f"{w} beat {l} {score(m)}{where}. On paper it wasn't close: {l} came in "
            f"{ordinal(s.rating_rank[l])} in {s.tier} by rating, {w} {ordinal(s.rating_rank[w])}."]
    mvp = match_mvp(m)
    if mvp and mvp['team'] is f['winner']:
        body.append(f"{name(mvp['player'])} led the way with {plural(mvp['impact'].hits, 'hit')}"
                    + (f" and {plural(mvp['impact'].catches, 'catch', 'catches')}" if mvp['impact'].catches else "")
                    + ".")
    for aw, al, am in f['also']:
        body.append(f"It wasn't the week's only surprise: {aw.team_name} also beat {al.team_name} {score(am)}.")
    return headline, body


def render_sweep(s, f, rng):
    w, l = f['winner'].team_name, f['loser'].team_name
    headline = rng.choice([f"{w} rolls past {l}", f"{w} makes it look easy",
                           f"No contest: {w} sweeps {l}"])
    body = [f"{w} swept {l} 3–0, giving up just {plural(f['conceded'], 'game')} "
            f"across {f['sets']} sets."]
    wins, losses = h2h_record(f['winner'], s.n)
    body.append(f"{w} is {wins}–{losses} in head-to-head play and {ordinal(s.rank[w])} in {s.tier}.")
    return headline, body


def render_unbeaten(s, f, rng):
    teams = [t.team_name for t in f['teams']]
    if len(teams) == 1:
        headline = f"{teams[0]} is the last unbeaten team"
        lead = f"{teams[0]} is the only team in {s.tier} still perfect in head-to-head play, at {f['wins']}–0."
    else:
        headline = rng.choice([f"{number(len(teams)).capitalize()} teams still perfect",
                               f"Unbeaten club down to {number(len(teams))}"])
        lead = f"{join(teams)} are all {f['wins']}–0 in head-to-head play."
    first = f['teams'][0]
    return headline, [lead, f"{first.team_name} is {ordinal(s.rank[first.team_name])} in {s.tier} "
                            f"with {s.points(first)} points."]


def render_standings(s, f, rng):
    leader = f['leader'].team_name
    if f['new_leader']:
        headline = rng.choice([f"{leader} takes over first place", f"New No. 1: {leader}"])
    elif f['dropped']:
        headline = rng.choice([f"{f['dropped'][0].team_name} falls out of the playoff picture",
                               "Shake-up at the playoff line"])
    elif f['entered']:
        headline = f"{f['entered'][0].team_name} climbs into a playoff spot"
    elif f['new_div_leaders']:
        headline = f"{f['new_div_leaders'][0].team_name} takes over the {f['new_div_leaders'][0].division}"
    else:
        headline = ("Bubble watch: a tie at the playoff line" if f['gap'] == 0
                    else f"Bubble watch: {plural(f['gap'], 'point')} at the playoff line")

    body = []
    second = f['second'].team_name
    if f['margin'] == 0:
        body.append(f"{leader} and {second} are level on {s.points(f['leader'])} points at the top "
                    f"of {s.tier}, with {leader} ahead on tiebreakers.")
    elif f['new_leader']:
        body.append(f"{leader} moved into first place in {s.tier} with {s.points(f['leader'])} points, "
                    f"{plural(f['margin'], 'point')} ahead of {second}. "
                    f"{f['leader_before'].team_name} had led a week ago.")
    else:
        change = ""
        if f['margin'] < f['margin_before']:
            change = f", down from {f['margin_before']} a week ago"
        elif f['margin'] > f['margin_before']:
            change = f", up from {f['margin_before']} a week ago"
        body.append(f"{leader} still leads {s.tier}, {plural(f['margin'], 'point')} clear of "
                    f"{second}{change}.")
    for team in f['new_div_leaders']:
        body.append(f"{team.team_name} now leads the {team.division}.")

    # The biggest moves across the playoff line, two each way at most
    moves = [f"{t.team_name} rose from {ordinal(s.rank_before[t.team_name])} to {ordinal(s.rank[t.team_name])}"
             for t in f['entered'][:2]]
    moves += [f"{t.team_name} fell from {ordinal(s.rank_before[t.team_name])} to {ordinal(s.rank[t.team_name])}"
              for t in f['dropped'][:2]]
    if moves:
        body.append(f"At the playoff line, {join(moves)}.")

    last_in, first_out = f['last_in'].team_name, f['first_out'].team_name
    out = (f"{first_out} is first out on tiebreakers" if f['gap'] == 0
           else f"{first_out} is first out, {plural(f['gap'], 'point')} back")
    bubble = f"{last_in} holds the last wild-card spot with {s.points(f['last_in'])} points; {out}."
    upcoming = next_assignment(s, [f['last_in'], f['first_out']])
    body.append(bubble + (" " + upcoming if upcoming else ""))
    return headline, body


def next_assignment(s, teams):
    """Where each team plays next week, as a sentence, or '' if not known."""
    if s.next_week is None or s.next_week in PLAYOFF_WEEKS:
        return ""
    parts = []
    for team in teams:
        if s.next_week in H2H_WEEKS:
            m = next(m for m in s.week_matches(s.next_week) if team in (m.team1, m.team2))
            opp = m.team2 if m.team1 is team else m.team1
            parts.append(f"{team.team_name} plays {opp.team_name}")
        else:
            t = s.team_tourney(team, s.next_week)
            sub = subtype_of(t, s.all_tourneys)
            parts.append(f"{team.team_name} plays in the {sub} bracket" if t.type == 'Score'
                         else f"{team.team_name} plays in the {sub} Division tournament" if t.type == 'Division'
                         else None)
    parts = [p for p in parts if p]
    return f"Next week, {join(parts)}." if parts else ""


def render_potw(s, f, rng):
    row, line = f['row'], f['line']
    player, team = name(row['player']), row['team'].team_name
    headline = rng.choice([f"{player} is Player of the Week",
                           f"{player} earns Player of the Week honors",
                           f"Player of the Week: {player}"])
    stats = [plural(line.hits, 'hit')]
    if line.catches:
        stats.append(plural(line.catches, 'catch', 'catches'))
    lead = (f"{player} of {team} is the {week_label(s.week)} Player of the Week, with "
            f"{join(stats)} over {plural(row['games'], 'game')}, "
            f"{row['above_avg']:+.1f} points above the tier average.")
    t = s.team_tourney(row['team'], s.week)
    if t:
        place = t.finish_order.index(row['team']) + 1
        context = (f"{team} won {tourney_name(t, s.all_tourneys)}." if place == 1
                   else f"{team} finished {ordinal(place)} in {tourney_name(t, s.all_tourneys)}.")
    else:
        m = next(m for m in s.week_matches(s.week) if row['team'] in (m.team1, m.team2))
        w, l = m.get_wl_teams()
        context = (f"{team} beat {l.team_name} {score(m)}." if w is row['team']
                   else f"{team} lost to {w.team_name} {score(m)}.")
    body = [lead, context]
    if f['runner_up']:
        r = f['runner_up']
        body.append(f"{name(r['player'])} of {r['team'].team_name} was next, at {r['above_avg']:+.1f}.")
    return headline, body


def render_star(s, f, rng):
    mvp, m = f['mvp'], f['match']
    player, team = name(mvp['player']), mvp['team'].team_name
    hits = mvp['impact'].hits
    headline = rng.choice([f"{plural(hits, 'hit')} for {player}", f"{player} goes off for {hits}",
                           f"{player}'s big day"])
    result = (f"in {team}'s {score(m)} win over {f['opponent'].team_name}" if f['won']
              else f"even as {team} lost {score(m)} to {f['opponent'].team_name}")
    catches = mvp['impact'].catches
    body = [f"{player} had {plural(hits, 'hit')}"
            + (f" and {plural(catches, 'catch', 'catches')}" if catches else "")
            + f" {result}, the best single-match line of {week_label(s.week)}."]
    return headline, body


def render_race(s, f, rng):
    leader, second = f['leader'], f['second']
    lname, sname = name(leader['player']), name(second['player'])
    if f['new_leader']:
        headline = f"{lname} takes the lead in the MVP race"
    else:
        headline = rng.choice([f"{lname} still leads the MVP race", f"MVP race: {lname} out front"])
    body = [f"{lname} of {leader['team'].team_name} leads the season-long MVP race at "
            f"{leader['above_avg']:+.1f} points above average, {f['margin']:.1f} ahead of "
            f"{sname} of {second['team'].team_name}."]
    if f['climber']:
        c = f['climber']
        body.append(f"{name(c['player'])} of {c['team'].team_name} moved up "
                    f"{plural(c['move'], 'place')} to {ordinal(c['rank'])}.")
    return headline, body


def render_h2h_preview(s, f, rng):
    (a, b), rest = f['pairs'][0], f['pairs'][1:]
    an, bn = a['team'].team_name, b['team'].team_name
    headline = rng.choice([f"Game of the week: {an} at {bn}", f"{an} and {bn} meet in {week_label(s.next_week)}",
                           f"Circle it: {an} at {bn}"])

    def desc(side):
        if f['by_rating']:
            return f"the {ordinal(side['rank'])}-rated team in {s.tier}"
        wins, losses = side['record']
        return f"{ordinal(side['place'])} in the {side['team'].division} at {wins}–{losses}"

    lead = f"{an} ({desc(a)}) visits {bn} ({desc(b)}) in {week_label(s.next_week)}."
    if a['team'].division == b['team'].division:
        lead += " The two are division rivals."
    body = [lead]
    if not f['by_rating'] and a['record'][1] == 0 and b['record'][1] == 0 and a['record'][0]:
        body.append("Both teams are unbeaten, so one perfect record ends.")
    if rest:
        c, d = rest[0]
        body.append(f"Also worth watching: {c['team'].team_name} at {d['team'].team_name}.")
    return headline, body


def render_tourney_preview(s, f, rng):
    t, kind = f['tourney'], f['type']
    week = week_label(s.next_week)
    top = f['seeded'][0].team_name
    where = f"{top}'s bracket" if kind == 'Random' else tourney_name(t, s.all_tourneys)
    headline = rng.choice([f"{week} preview: {top} heads the field" if kind == 'Random'
                           else f"{week} preview: {top} leads {where.replace('the ', '', 1)}",
                           f"What to watch in {week}"])
    intro = {
        'Score': (f"{week} is a Score week: teams are grouped by record, two from each division "
                  f"per bracket, and every bracket pays its winner the same 21 points."),
        'Division': f"{week} sends every team back to its division for a Division tournament.",
        'Random': f"{week} is a Random draw, with two teams from each division in every bracket.",
    }[kind]
    pairs = '; '.join(f"{a.team_name} vs. {b.team_name}" for a, b in f['pairs'])
    body = [intro, f"In {where}, the projected first round is {pairs}."]
    if f['pick']:
        a, b = f['pick']
        body.append(f"The pick of the opening matches is {a.team_name} ({ordinal(s.rank[a.team_name])} "
                    f"in {s.tier}) against {b.team_name} ({ordinal(s.rank[b.team_name])}).")
    for team, streak in f['streaks']:
        body.append(f"{team.team_name} goes for its {ordinal(streak + 1)} straight title.")
    return headline, body


def render_preseason(s, f, rng):
    favs = f['favorites']
    headline = rng.choice([f"{favs[0].team_name} starts as the team to beat",
                           f"Season preview: {favs[0].team_name} leads the way"])
    body = [f"{favs[0].team_name} opens the season as the highest-rated team in {s.tier}, "
            f"ahead of {join([t.team_name for t in favs[1:]])}.",
            f"The first four weeks are head-to-head; tournaments start in {week_label(FIRST_TOURNEY_WEEK)}."]
    return headline, body


def render_field_set(s, f, rng):
    seeds = f['seeds']
    headline = rng.choice([f"The field is set: {seeds[0].team_name} is the No. 1 seed",
                           f"{seeds[0].team_name} tops the playoff field"])
    byes = join([f"{t.team_name} ({i})" for i, t in enumerate(seeds[:4], start=1)])
    pairs = '; '.join(f"{a.team_name} vs. {b.team_name}" for a, b in f['pairs'])
    body = [f"The regular season is over, and {len(seeds)} teams are in. {byes} earned first-round byes.",
            f"Seeds 5 through {len(seeds)} open the playoffs: {pairs}.",
            f"{f['first_out'].team_name} missed out by {plural(f['gap'], 'point')}."]
    return headline, body


def render_playoff_round(s, f, rng):
    seed_of = f['seed_of']
    out = f['best_out']
    if f['upset']:
        headline = f"No. {seed_of[out]} {out.team_name} is knocked out"
    else:
        headline = f"{number(len(f['advancers'])).capitalize()} teams move on from {f['name']}"
    adv = join([f"{t.team_name} ({seed_of[t]})" for t in f['advancers']])
    gone = join([f"{t.team_name} ({seed_of[t]})" for t in sorted(f['out'], key=seed_of.get)])
    body = [f"{adv} advanced from {f['name']}.", f"{gone} were eliminated."]
    mvp = f['mvp']
    body.append(f"{name(mvp['player'])} of {mvp['team'].team_name} led the round, "
                f"helping win {plural(mvp['match_wins'], 'match', 'matches')}.")
    return headline, body


def render_champion(s, f, rng):
    champ, runner_up = f['champ'].team_name, f['runner_up'].team_name
    seed = f['seed_of'][f['champ']]
    headline = rng.choice([f"{champ} wins the {s.tier} title", f"Champions: {champ}"])
    final = ("in a deciding second final" if f['reset'] else "in the championship")
    body = [f"No. {seed} {champ} beat {runner_up} {score(f['final'])} {final} to win {s.tier}. "
            f"{f['third'].team_name} finished third."]
    # One sentence per player, so a player who won both awards is named once
    titles = {}
    for title, pid in (('Final Four MVP', f['final_four_mvp']), ('Playoff MVP', f['playoff_mvp'])):
        if pid:
            titles.setdefault(pid, []).append(title)
    for pid, won in titles.items():
        body.append(f"{name(s.awards.player_of[pid])} of {s.awards.team_of[pid].team_name} "
                    f"was {join(won)}.")
    return headline, body


def render_playoff_preview(s, f, rng):
    seed_of = f['seed_of']
    headline = f"{f['name']} preview"
    pairs = '; '.join(f"{a.team_name} ({seed_of[a]}) vs. {b.team_name} ({seed_of[b]})" for a, b in f['pairs'])
    body = []
    if f['byes']:
        body.append(f"The top four seeds, {join([t.team_name for t in f['byes']])}, join the field.")
    body.append(f"The opening matches: {pairs}.")
    return headline, body


RENDERERS = {
    'tournament': render_tournament,
    'snapped': render_snapped,
    'upset': render_upset,
    'sweep': render_sweep,
    'unbeaten': render_unbeaten,
    'standings': render_standings,
    'potw': render_potw,
    'star': render_star,
    'race': render_race,
    'h2h_preview': render_h2h_preview,
    'tourney_preview': render_tourney_preview,
    'preseason': render_preseason,
    'field_set': render_field_set,
    'playoff_round': render_playoff_round,
    'champion': render_champion,
    'playoff_preview': render_playoff_preview,
}

# How many stories of one kind can run in the same week
KIND_LIMIT = {'tournament': 2}

# Stories about the week ahead; one always runs when there is one
PREVIEWS = {'h2h_preview', 'tourney_preview', 'preseason', 'field_set', 'playoff_preview'}


def roundup(s, featured):
    """'Around the league': the tournament winners not already featured."""
    if s.week is None or s.week in H2H_WEEKS or s.current_week > WEEKS[-1]:
        return None
    lines = [f"{t.finish_order[0].team_name} won {tourney_name(t, s.all_tourneys)}, beating "
             f"{t.finish_order[1].team_name} in the final."
             for t in s.week_tourneys(s.week) if t.finish_order[0].team_name not in featured]
    if not lines:
        return None
    return {'kind': 'roundup', 'headline': 'Around the league', 'paragraphs': lines}


def league_news(tier, tier_data, awards, current_week, count=ARTICLES):
    """The most newsworthy articles for a tier as of current_week, lead story
    first: [{kind, headline, paragraphs}]. A story is skipped when its subject
    already leads another, and the best preview of the week ahead always
    makes the cut. In tournament weeks an 'Around the league' roundup of the
    other winners follows the count articles."""
    s = Season(tier, tier_data, awards, current_week)
    found = sorted(storylines(s), key=lambda st: -st.priority)
    preview = next((st for st in found if st.kind in PREVIEWS), None)
    picked, subjects, kinds = [], set(), {}
    for story in found:
        if len(picked) == count - (preview not in picked and preview is not None):
            break
        if story.subject in subjects or kinds.get(story.kind, 0) >= KIND_LIMIT.get(story.kind, 1):
            continue
        subjects.add(story.subject)
        kinds[story.kind] = kinds.get(story.kind, 0) + 1
        picked.append(story)
    if preview is not None and preview not in picked:
        picked.append(preview)

    chosen = []
    for story in picked:
        headline, paragraphs = RENDERERS[story.kind](s, story.facts, s.rng(story.kind, story.subject))
        chosen.append({'kind': story.kind, 'headline': headline, 'paragraphs': paragraphs})

    extra = roundup(s, subjects)
    if extra:
        chosen.append(extra)
    return chosen
