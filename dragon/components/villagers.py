import enum
import random

from base_classes.components import Component
from dragon.simulation import Map, DragonHuntSimulation


class VillagerState(enum.Enum):
    IDLE = 0
    FARMING = 1
    MOVING_TO_VILLAGE = 2
    MOVING_TO_CAVE = 3
    ATTACKING = 4


class Villager(Component):

    HP = 0
    Attack = 0
    Farming = 0
    SpawnCost = 0

    # type hint
    simulation: DragonHuntSimulation

    def __init__(self, simulation):
        super().__init__(simulation)
        self.location = Map.VILLAGE
        self.state = VillagerState.IDLE
        self.hp = self.HP
        self.name = get_name()

    def actuate(self):
        if self.state == VillagerState.IDLE:
            pass
        elif self.state == VillagerState.FARMING and self.location == Map.VILLAGE:
            self.simulation.wheat += self.Farming
        elif self.state == VillagerState.ATTACKING and self.location == Map.CAVE:
            self.simulation.dragon.get_attacked(self.Attack)
        elif self.state == VillagerState.MOVING_TO_VILLAGE:
            self.location = Map.VILLAGE
            self.state = VillagerState.IDLE
        elif self.state == VillagerState.MOVING_TO_CAVE:
            self.location = Map.CAVE
            self.state = VillagerState.IDLE

    def get_attacked(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.die()

    def die(self):
        self.simulation.remove_component(self)

    def __repr__(self):
        return f"{self.id}({self.state})"


class Farmer(Villager):
    HP = 0
    Attack = 0
    Farming = 0
    SpawnCost = 0

    @property
    def role(self):
        return "Farmer"


class Warrior(Villager):
    HP = 0
    Attack = 0
    Farming = 0
    SpawnCost = 0

    @property
    def role(self):
        return "Warrior"


NAMES = ["James", "David", "Christopher", "George", "Ronald", "John", "Richard", "Daniel", "Kenneth", "Anthony", "Robert", "Charles", "Paul", "Steven", "Kevin", "Michael", "Joseph", "Mark", "Edward", "Jason", "William", "Thomas", "Donald", "Brian", "Jeff", "Mary", "Jennifer", "Lisa", "Sandra", "Michelle", "Patricia", "Maria", "Nancy", "Donna", "Laura", "Linda", "Susan", "Karen", "Carol", "Sarah", "Barbara", "Margaret", "Betty", "Ruth", "Kimberly", "Elizabeth", "Dorothy", "Helen", "Sharon", "Deborah"]
random.shuffle(NAMES)


def get_name():
    return NAMES[Farmer._count + Warrior._count]  # a trick to get unique names (_count is used to assign unique IDs to components)
