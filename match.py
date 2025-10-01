from game import *
class Match:

    def __init__(self, team1, team2, match_type, year, week):

        self.team1 = team1
        self.team2 = team2
        self.match_type = match_type
        self.year = year
        self.week = week
        self.games = []
        self.winner = None
        self.match_score = None
        self.set_results = []

    def select_players(self, team):

        player_scores = []
        for player in team.players:
            average_score = 0.25*(player.aim + player.speed + player.throw + player.hands)
            player_scores.append((player,average_score))

        sorted_players = sorted(player_scores, key = lambda item: item[1], reverse = True)

        top_5_players = [player for player, score in sorted_players[:5]]

        return top_5_players

    def run_match(self):

        if self.match_type == "H":

            #run a best of 5 set match
            #each set is best of 7 games

            #Give home team a 10 point advantage

            for player in self.team2.players:
                player.aim += 10
                player.speed += 10
                player.throw += 10
                player.hands += 10
                player.aimmax += 10
                player.speedmax += 10
                player.throwmax += 10
                player.handsmax += 10

            #pick the players

            match_score = [0,0]
            match_flag = True
            while match_flag:

                set_score = [0,0]
                set_flag = True

                while set_flag:

                    players1 = self.select_players(self.team1)
                    players2 = self.select_players(self.team2)

                    game = Game(players1, players2)
                    game.run_game()
                    self.games.append(game)

                    #degrade all players by 5%
                    for player in players1+players2:
                        player.aim *= 0.95
                        player.hands *= 0.95
                        player.speed *= 0.95
                        player.throw *= 0.95

                    #improve all non-players by 5%

                    non_players = [player for player in self.team1.players + self.team2.players if player not in players1 + players2]

                    for player in non_players:
                        player.aim = min(player.aim*1.05,player.aimmax)
                        player.speed = min(player.speed*1.05,player.speedmax)
                        player.throw = min(player.throw*1.05,player.throwmax)
                        player.hands = min(player.hands*1.05,player.handsmax)

                    

                    set_score[game.winner-1] += 1

                    if set_score[0] == 4:
                        set_flag = False
                        match_score[0] += 1
                        self.set_results.append(set_score)
                    elif set_score[1] == 4:
                        set_flag = False
                        match_score[1] += 1
                        self.set_results.append(set_score)

                    # after a set, improve all players by 10%

                for player in self.team1.players + self.team2.players:
                    player.aim = min(player.aim*1.1,player.aimmax)
                    player.speed = min(player.speed*1.1,player.speedmax)
                    player.throw = min(player.throw*1.1,player.throwmax)
                    player.hands = min(player.hands*1.1,player.handsmax)


                if match_score[0] == 3:
                    match_flag = False
                    self.winner = 1
                    self.match_score = match_score
                    self.team1.score.append(15)
                    self.team2.score.append(5*match_score[1])
                elif match_score[1] == 3:
                    match_flag= False
                    self.winner = 2
                    self.match_score = match_score
                    self.team2.score.append(15)
                    self.team1.score.append(5*match_score[0])

            # Remove home field advantage

            for player in self.team2.players:
                player.aimmax += -10
                player.speedmax += -10
                player.throwmax += -10
                player.handsmax += -10
                
            # Revert all scores back to max

            for player in self.team1.players + self.team2.players:
                player.aim = player.aimmax
                player.speed = player.speedmax
                player.throw = player.throwmax
                player.hands = player.handsmax
   

            
                        
        elif self.match_type == "T":

            #run a best of 5 match
   

            match_score = [0,0]
            match_flag = True
            while match_flag:

                players1 = self.select_players(self.team1)
                players2 = self.select_players(self.team2)

                game = Game(players1, players2)
                game.run_game()
                self.games.append(game)

                #degrade all players by 5%
                for player in players1+players2:
                    player.aim *= 0.95
                    player.hands *= 0.95
                    player.speed *= 0.95
                    player.throw *= 0.95

                #improve all non-players by 5%

                non_players = [player for player in self.team1.players + self.team2.players if player not in players1 + players2]

                for player in non_players:
                    player.aim = min(player.aim*1.05,player.aimmax)
                    player.speed = min(player.speed*1.05,player.speedmax)
                    player.throw = min(player.throw*1.05,player.throwmax)
                    player.hands = min(player.hands*1.05,player.handsmax)

                    

                match_score[game.winner-1] += 1

                if match_score[0] == 3:
                    match_flag = False
                    self.winner = 1
                    self.match_score = match_score
                elif match_score[1] == 3:
                    match_flag = False
                    self.winner = 2
                    self.match_score = match_score
                        
            # Revert all scores back to max

            for player in self.team1.players + self.team2.players:
                player.aim = player.aimmax
                player.speed = player.speedmax
                player.throw = player.throwmax
                player.hands = player.handsmax
                

    def get_wl_teams(self):
        if self.winner == 1:
            return self.team1, self.team2
        else:
            return self.team2, self.team1
