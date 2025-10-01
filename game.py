## Game class
## Input: team objects
import random
import math

class Game:

    def __init__(self, players1, players2):
        self.players1 = players1
        self.players2 = players2
        for player in self.players1 + self.players2:
            player.live = 1
            player.ball = 0
        self.log = []
        self.reservoir1 = 0
        self.reservoir2 = 0
 
    def assign_balls(self):
        holders = random.sample(self.players1+self.players2,5)
        playerids = [player.pid for player in self.players1 + self.players2]
        
        for player in holders:
            player.ball = 1
            
        holderids = [player.pid for player in holders if player.ball==1]
        self.log.append({"Thrower": None,
                    "Target": None,
                    "Result": None,
                    "Alive": playerids,
                    "Holders": holderids,
                    "Reservoir1": 0,
                    "Reservoir2": 0})
                            
    def put_in_reservoir(self,u,p):
        u3 = random.random()
        if u3 < p:
        #Ball goes to targeted team
            if u < 0.5:
                self.reservoir2 += 1
            else:
                self.reservoir1 += 1
        else:
        #Ball goes to throwing team
            if u < 0.5:
                self.reservoir1 += 1
            else:
                self.reservoir2 += 1

    def get_prob(self, val1, val2, lam = 0.004):
        return 1/(1+math.exp(lam*(val2-val1)))

    def throw_ball(self):

        #Select thrower/target
        u = random.random()
        holders = [player for player in self.players1+self.players2 if player.live == 1 and player.ball == 1]
        thrower = random.choice(holders)
        if thrower in self.players1:
            u=0.25
            target = random.choice([player for player in self.players2 if player.live ==1])
        else:
            u=0.75
            target = random.choice([player for player in self.players1 if player.live ==1])

        u1 = random.random()

        if u1 < self.get_prob(thrower.aim, target.speed):
            #contact
            if target.ball == 1:
                u2 = random.random()
                if u2 < self.get_prob(thrower.throw, target.hands):
                    #Hit
                    result = "Hit"
                    #Un-alive target
                    target.live = 0
                    #Put thrown ball in reservoir
                    self.put_in_reservoir(u,p=0.8)
                    #Take away held ball
                    target.ball = 0
                    #Put held ball in reservoir
                    self.put_in_reservoir(u,p=1)
                    
                else:
                    #Block
                    result = "Block"
                    #Put thrown ball in reservoir
                    self.put_in_reservoir(u,p=0.5)
            else:
                u1 = random.random()
                if u1 < self.get_prob(thrower.throw, 0.25*target.hands):
                    #Hit
                    result = "Hit"
                    #Un-alive target
                    target.live = 0
                    #Put thrown ball in reservoir
                    self.put_in_reservoir(u,p=0.8)
                else:
                    #Catch
                    result = "Catch"
                    #Un-alive thrower
                    thrower.live = 0
                    #Re-alive player from targeted team
                    if thrower in self.players1:
                        out_players = [player for player in self.players2 if player.live == 0]
                    else:
                        out_players = [player for player in self.players1 if player.live == 0]
                    if len(out_players) > 0:
                        re_alive = random.choice(out_players)
                        re_alive.live = 1
                    #Give target the ball
                    target.ball = 1
                    

        else:
            #miss
            result = "Miss"
            #Put thrown ball in reservoir
            self.put_in_reservoir(u,p=0.8)

        #Take away thrown ball    
        thrower.ball = 0
        
        #Add the play to the log
        aliveids = [player.pid for player in self.players1 + self.players2 if player.live == 1]
        holderids = [player.pid for player in self.players1 + self.players2 if player.ball==1]
        self.log.append({"Thrower": thrower.pid,
                    "Target": target.pid,
                    "Result": result,
                    "Alive": aliveids,
                    "Holders": holderids,
                    "Reservoir1": self.reservoir1,
                    "Reservoir2": self.reservoir2})

        
    def reassign_balls(self):
        #For each team

        ## Who doesn't have a ball
        players_alive_noball_1 = [player for player in self.players1 if (player.live == 1 and player.ball == 0)]

        ## If there's something in the reservoir, dish it out
        if self.reservoir1 > 0:
            flag = True
        else:
            flag = False

        while(flag):
            ## Do any players still need a ball?
            if len(players_alive_noball_1) > 0:
                ## Pick one to receive
                picker_upper = random.choice(players_alive_noball_1)
                ## Give that player the ball
                picker_upper.ball = 1
                ## Remove that player from the list of those tha need a ball
                players_alive_noball_1 = [player for player in self.players1 if (player.live == 1 and player.ball == 0)]
                #players_alive_noball_1 = players_alive_noball_1.remove(picker_upper)
                ## Remove a ball from the reservoir
                self.reservoir1 += -1
            else:
                flag = False
            ## Any balls left in reservoir?
            if self.reservoir1 == 0:
                flag = False


        ## Who doesn't have a ball
        players_alive_noball_2 = [player for player in self.players2 if (player.live == 1 and player.ball == 0)]

        ## If there's something in the reservoir, dish it out
        if self.reservoir2 > 0:
            flag = True
        else:
            flag = False

        while(flag):
            ## Do any players still need a ball?
            if len(players_alive_noball_2) > 0:
                ## Pick one to receive
                picker_upper = random.choice(players_alive_noball_2)
                ## Give that player the ball
                picker_upper.ball = 1
                ## Remove that player from the list of those tha need a ball
                players_alive_noball_2 = [player for player in self.players2 if (player.live == 1 and player.ball == 0)]
                #players_alive_noball_2 = players_alive_noball_2.remove(picker_upper)
                ## Remove a ball from the reservoir
                self.reservoir2 += -1
            else:
                flag = False
            ## Any balls left in reservoir?
            if self.reservoir2 == 0:
                flag = False

    def run_game(self):
        self.assign_balls()
        aliveids1 = [player.pid for player in self.players1 if player.live == 1]
        aliveids2 = [player.pid for player in self.players2 if player.live == 1]
        while(len(aliveids1)>0 and len(aliveids2)>0):
            self.throw_ball()
            self.reassign_balls()
            aliveids1 = [player.pid for player in self.players1 if player.live == 1]
            aliveids2 = [player.pid for player in self.players2 if player.live == 1]
        if len(aliveids1)>0:
            self.winner = 1
        else:
            self.winner = 2
