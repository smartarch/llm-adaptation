import enum
import random

from base_classes.components import Component
from dragon.simulation import DragonHuntSimulation, Map


class Dragon(Component):

    HP = 0
    FireAttackProb = 0
    EatAttackProb = 0
    Regeneration = 0  # HP regained in each step without an attack (after the Dragon was attacked for the first time)

    # type hint
    simulation: DragonHuntSimulation

    def __init__(self, simulation):
        super().__init__(simulation)
        self.hp = self.HP
        self.got_attacked_this_step = False
        self.fight_started = False  # whether the Dragon has already been attacked
        self.attack_log = ""  # save the last attack for logging purposes

    def actuate(self):
        self.attack_log = ""
        if self.got_attacked_this_step:
            self.attack_back()
        elif self.fight_started and 0 < self.hp < self.HP:
            self.hp = min(self.HP, self.hp + self.Regeneration)
        self.got_attacked_this_step = False

    def get_attacked(self, damage):
        self.hp -= damage
        self.got_attacked_this_step = True
        self.fight_started = True

    def attack_back(self):
        prob = random.random()
        if prob < self.FireAttackProb:
            self.fire_attack()
        elif prob < self.FireAttackProb + self.EatAttackProb:
            self.eat_attack()

    def fire_attack(self):
        self.attack_log = "fire"
        villagers = self.simulation.get_villagers_in(Map.CAVE)
        for villager in villagers:
            villager.get_attacked(1)

    def eat_attack(self):
        self.attack_log = "eat"
        villagers = self.simulation.get_villagers_in(Map.CAVE)
        if not villagers:
            return
        villager = random.choice(villagers)
        villager.get_attacked(villager.hp)  # kill the villager

    def __repr__(self):
        return f"{self.id}({self.hp})"
