"""Postseason, run per tier after the regular season.

12 teams qualify: the 4 division winners (seeds 1-4, who get byes) and the
next 8 teams by record (seeds 5-12). Three rounds:
  Round 1 - seeds 5-12 play the 8-team double-elimination bracket; it stops
            as soon as the top 4 are known.
  Round 2 - those 4 plus the 4 bye teams play the same bracket; top 4 advance.
  Round 3 - Final Four, a 4-team double-elimination bracket for the title.
Every round is seeded by playoff seed. Playoff results never add to
team.score / team.games, so regular-season standings are unchanged.
"""
from match import Match
from player import update_players
from league import record_key, PLAYOFF_WEEKS


def playoff_seeds(teams):
    """12 qualifiers in seed order: division winners, then the next 8 teams,
    each group ranked by record_key."""
    leaders, rest, seen = [], [], set()
    for team in sorted(teams, key=lambda t: record_key(t.score, t.games)):
        (rest if team.division in seen else leaders).append(team)
        seen.add(team.division)
    return leaders + rest[:8]


class PlayoffRound:

    def __init__(self, team_list, year, week, round_num):
        self.team_list = team_list      # in seed order; never re-sorted
        self.year = year
        self.week = week
        self.round = round_num
        self.matches = []
        self.advancers = []             # rounds 1-2: the 4 teams moving on
        self.finish_order = []          # round 3: champion first

    def play(self, team1, team2):
        match = Match(team1, team2, "T", self.year, self.week)
        match.run_match()
        self.matches.append(match)
        return match.get_wl_teams()

    def run_qualifier(self):
        """The regular-season 8-team bracket, cut off once the top 4 are set:
        both 2-0 teams plus the two 2-1 teams that win in round 4. The 7th/8th
        and 5th/6th games and everything after round 4 aren't played."""
        s = self.team_list
        w1, l1 = self.play(s[0], s[7])
        w2, l2 = self.play(s[3], s[4])
        w3, l3 = self.play(s[2], s[5])
        w4, l4 = self.play(s[1], s[6])
        w5, _ = self.play(l1, l2)       # losers bracket; losers are out
        w6, _ = self.play(l3, l4)
        w8, l8 = self.play(w1, w2)      # main bracket
        w9, l9 = self.play(w3, w4)
        w10, _ = self.play(w5, l8)      # losers bracket; losers are out
        w11, _ = self.play(w6, l9)
        self.advancers = [w8, w9, w10, w11]

    def run_final_four(self):
        """4-team double elimination, with a second final if the losers-bracket
        team wins the first."""
        s = self.team_list
        w1, l1 = self.play(s[0], s[3])
        w2, l2 = self.play(s[1], s[2])
        w3, l3 = self.play(w1, w2)      # winners final
        w4, l4 = self.play(l1, l2)      # loser finishes 4th
        w5, l5 = self.play(w4, l3)      # loser finishes 3rd
        champ, runner_up = self.play(w3, w5)
        if champ is w5:
            champ, runner_up = self.play(champ, runner_up)
        self.finish_order = [champ, runner_up, l5, l4]


def run_playoffs(teams, year):
    """Play all three rounds for one tier, updating players after each week
    as in the regular season. Returns (seeds, [round 1, round 2, round 3])."""
    seeds = playoff_seeds(teams)
    by_seed = lambda team: seeds.index(team)
    week1, week2, week3 = PLAYOFF_WEEKS

    round1 = PlayoffRound(seeds[4:], year, week1, 1)
    round1.run_qualifier()
    update_players(teams, round1.matches, week1)

    round2 = PlayoffRound(seeds[:4] + sorted(round1.advancers, key=by_seed), year, week2, 2)
    round2.run_qualifier()
    update_players(teams, round2.matches, week2)

    round3 = PlayoffRound(sorted(round2.advancers, key=by_seed), year, week3, 3)
    round3.run_final_four()
    update_players(teams, round3.matches, week3)

    return seeds, [round1, round2, round3]
