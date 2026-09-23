class Myclass:
    x=5
p1 = Myclass()
# print(p1.x)

class Standin:
    pass


class Person:
    def __init__(self,name,age=18):
        self.name = name
        self.age = age
    def greeting(self):
        print(f"Hello, my name is {self.name}, and I'm {self.age} years old")

thisDude = Person("John", 23)

# thisDude.greeting()

class Sxperhuman:
    clr = "red"
    def __init__(self,name,position,power_type,team):
        self.name = name
        self.position = position
        self.power_type = power_type
        self.team = team
    def move(self):
        pass
    def attack(self):
        pass
    def collide(self):
        pass

class Student:
    def __init__(self,name,grade):
        self.name = name
        self.grade = grade

s1 = Student("Anna", "A")

# print(s1.name)
# print(s1.grade)

s1.grade = "B"

# print(s1.grade)

