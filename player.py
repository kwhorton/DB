import pandas as pd

class Player:

    def __init__(self,pid,aim,speed,throw,hands):
        self.pid = pid
        self.aim = aim
        self.name = None
        self.yeargroup=None
        self.speed = speed
        self.throw = throw
        self.hands = hands
        self.aimmax = aim
        self.speedmax = speed
        self.throwmax = throw
        self.handsmax = hands
        self.all_stats = []
        

    def get_average_score(self):
        average_score = 0.25*(self.aim + self.speed + self.throw + self.hands)
        return average_score

    def get_average_score_week(self,week):
        x = [(stats['Aim'],stats['Speed'],stats['Throw'],stats['Hands']) for stats in self.all_stats if stats['Week']==week]
        average_score = 0.25*sum(x[0])
        return average_score


    def get_player_perf(self,schedule,week):
        player_games = []
        matches = [match1 for match1 in schedule if match1.week==week]
        for match1 in matches:
            player_games.append([game for game in match1.games if self in game.players1+game.players2])
        player_games = [item for sublist in player_games for item in sublist]
        #Set all stats to 0
        num_throws, num_targeted, num_contact_good, num_contact_bad, num_hit_good, num_hit_bad = 0,0,0,0,0,0
        num_catch_good, num_catch_bad, num_block_good, num_block_bad  = 0,0,0,0

        for game in player_games:
            for play in game.log:
                # OFFENSIVE STATS
                #if player was thrower, increase # of throws
                if play['Thrower'] == self.pid:
                    num_throws += 1
                    #if player scored a hit, increase # of contacts and hits
                    if play['Result'] == 'Hit':
                        num_contact_good += 1
                        num_hit_good += 1
                    #if the ball was caught, increase # of contacts and times caught
                    elif play['Result'] == 'Catch':
                        num_contact_good += 1
                        num_catch_bad += 1
                    #if the ball was blocked, increase # of contacts
                    elif play['Result'] == 'Block':
                        num_contact_good += 1
                        num_block_good += 1
                # DEFENSIVE STATS
                #if player was the target, increase # of times targeted
                elif play['Target'] == self.pid:
                    num_targeted += 1
                    #if player was hit, increase # of contacts and times hit
                    if play['Result'] == 'Hit':
                        num_contact_bad += 1
                        num_hit_bad += 1
                    #if the ball was caught, increase # of contacts and catches
                    elif play['Result'] == 'Catch':
                        num_contact_bad += 1
                        num_catch_good += 1
                    #if the ball was blocked, incraease nubmer of contacts
                    elif play['Result'] == 'Block':
                        num_contact_bad += 1
                        num_block_bad += 1

        aim_perf, speed_perf, throw_perf, hands_perf = None,None,None,None
        if num_throws > 0:
            aim_perf = num_contact_good/num_throws
        if num_contact_good >0:
            throw_perf = (num_hit_good - num_catch_bad)/num_contact_good
        if num_targeted > 0:
            speed_perf = 1 - num_contact_bad/num_targeted
        if num_contact_bad >0:
            hands_perf = (num_catch_good - num_hit_bad)/num_contact_bad

        stats = {'Week': week,
                 'Aim': self.aimmax,
                 'Speed': self.speedmax,
                 'Throw': self.throwmax,
                 'Hands': self.handsmax,
                 'GP': len(player_games),
                 'Throws': num_throws,
                 'Hits': num_hit_good,
                 'Blocked': num_block_bad,
                 'Caught': num_catch_bad,
                 'Targeted': num_targeted,
                 'Hit': num_hit_bad,
                 'Blocks': num_block_good,
                 'Catches': num_catch_good,
                 'Aim_Perf': round(aim_perf,3) if aim_perf != None else None,
                 'Throw_Perf': round(throw_perf,3) if throw_perf != None else None,
                 'Speed_Perf': round(speed_perf,3) if speed_perf != None else None,
                 'Hands_Perf': round(hands_perf,3) if hands_perf != None else None}
        self.all_stats.append(stats)
        return stats


def get_improvements(gp):
    if gp<=9:
        return [-0.5,-0.5,0,0.5,1,1,1,1,1]
    elif gp<= 14:
        return [-0.5,-0.5,0,0.5,1,1.5,1.5,1.5,2]
    elif gp<= 19:
        return [-1,-0.5,0,0.5,1,1.5,1.5,2,2.5]
    elif gp<=24:
        return [-1,-0.5,0,0.5,1,1.5,2,2.5,3]
    else:
        return [-0.5,0,0.5,1,1.5,2,2.5,3,3]


class PlayerDB:
    """
    PlayerDB class definition (for reference)
    """
    def __init__(self, player_id, name, yeargroup):
        self.player_id = player_id
        self.name = name
        self.yeargroup = yeargroup
        self.seasons = []
        self.stats = []

        
def update_players(teams,schedule,week):

    all_perf = []
    matches = [match1 for match1 in schedule if match1.week == week]
    for team in teams:
        for player in team.players:
            stats = player.get_player_perf(schedule,week)
            stats['Player'] = player.pid
            stats['Team'] = team.team_name
            all_perf.append(stats)

    all_perf_df = pd.DataFrame(all_perf)

    aimq = all_perf_df['Aim_Perf'].quantile([0.05,0.10,0.6,0.7,0.8,0.9,0.95,0.99])
    speedq = all_perf_df['Speed_Perf'].quantile([0.05,0.10,0.6,0.7,0.8,0.9,0.95,0.99])
    throwq = all_perf_df['Throw_Perf'].quantile([0.05,0.10,0.6,0.7,0.8,0.9,0.95,0.99])
    handsq = all_perf_df['Hands_Perf'].quantile([0.05,0.10,0.6,0.7,0.8,0.9,0.95,0.99])
    

    for team in teams:
        for player in team.players:
            p_gp = [stats['GP'] for stats in player.all_stats if stats['Week']==week][0]
            p_aim = [stats['Aim_Perf'] for stats in player.all_stats if stats['Week']==week][0]
            p_speed = [stats['Speed_Perf'] for stats in player.all_stats if stats['Week']==week][0]
            p_throw = [stats['Throw_Perf'] for stats in player.all_stats if stats['Week']==week][0]
            p_hands = [stats['Hands_Perf'] for stats in player.all_stats if stats['Week']==week][0]
            if p_gp == 0:
                aim_plus = 0
            else:
                imps = get_improvements(p_gp)
                if p_aim != None:
                    player.aimmax += imps[sum(p_aim > aimq)]
                    player.aim = player.aimmax
                if p_speed != None:
                    player.speedmax += imps[sum(p_speed > speedq)]
                    player.speed = player.speedmax
                if p_throw != None:
                    player.throwmax += imps[sum(p_throw > throwq)]
                    player.throw = player.throwmax
                if p_hands != None:
                    player.handsmax += imps[sum(p_hands > handsq)]
                    player.hands = player.handsmax
            
    

    # A different approach:
     ### create a function that finds the average performances across the tier
     ### Feed those averages into a function within player class and update players that way


    #Within each tier
    # For all teams, get the week's stats for team's players
    # Rack and stack
    # Adjust max attributes
    ## Should be dependent on how many games were played
    ## Fewer games -> smaller adjustment
    # Set current values to new maxes


    
