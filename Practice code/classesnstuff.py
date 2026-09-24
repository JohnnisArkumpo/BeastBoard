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

class Student:
    def __init__(self,name,grade):
        self.name = name
        self.grade = grade

s1 = Student("Anna", "A")

# print(s1.name)
# print(s1.grade)

s1.grade = "B"

# print(s1.grade)

class Animal:
    def __init__(self,sound):
        self.sound = sound
    def make_sound(self):
        return f"{self.sound}"

class Dog(Animal):
    def __init__(self,sound):
        Animal.__init__(self,sound)

class Cat(Animal):
    def __init__(self,sound):
        Animal.__init__(self,sound)

c1 = Cat("Meow")
d1 = Dog("woof")

for x in (c1,d1):
    print(f"{x.make_sound}")