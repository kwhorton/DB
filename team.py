class Team:

    def __init__(self, team_name, division, players):
        self.team_name = team_name
        self.players = players
        self.division = division
        self.rating = 0
        self.score = []
        self.games = []     # (games won, games played), one per score entry

    def get_team_rating(self):
        team_scores = 0
        for player in self.players:
            team_scores += player.get_average_score()
        self.rating = team_scores/len(self.players)
