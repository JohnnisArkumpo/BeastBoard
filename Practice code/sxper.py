class Sxperhuman:
    clr = "red"
    def __init__(self,name,px,py,power_type,team):
        self.__name = name
        self.x = px
        self.y = py
        self.power_type = power_type
        self.team = team
        self.powers = []
    def move(self, x, y):
        self.x+=x
        self.y+=y
        print(f"I moved")
        return (self.x,self.y)
    def attack(self):
        pass
    def collide(self):
        pass
    def voiceline(self):
        return self.power_type, self.team
    def info(self):
        return self.__name

class Villian(Sxperhuman):
    def __init__(self,name,px,py,power_type,team):
        Sxperhuman.__init__(self,name,px,py,power_type,team)
        self.size = 25


Sxperhuman.clr = "Blue"

supe = Sxperhuman("p1",50,50,"jump","player_team")
vil = Villian("opn1",25,75,"hit","opponent")


for x in (supe, vil):
    x.move(5,5)