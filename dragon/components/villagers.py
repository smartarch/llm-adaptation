import enum
import random

from base_classes.components import Component
from dragon.simulation import Map, DragonHuntSimulation


class VillagerState(enum.StrEnum):
    IDLE = "idle"
    FARMING = "farming"
    MOVING_TO_VILLAGE = "moving_to_village"
    MOVING_TO_CAVE = "moving_to_cave"
    ATTACKING = "attacking"
    SPAWNING = "spawning_new_villager"
    EATING = "eating"


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
        self.log_state = VillagerState.IDLE  # for logging
        self.hp = self.HP
        self.name = get_name()
        self.steps_since_meal = 0  # number of consecutive steps without a meal (new villagers start fed)

    def actuate(self):
        self.log_state = self.state
        if self.state == VillagerState.EATING and self.location == Map.VILLAGE and self.simulation.farm.wheat >= self.simulation.meal_cost:
            self.simulation.farm.wheat -= self.simulation.meal_cost
            self.steps_since_meal = 0
        else:
            self.steps_since_meal += 1

        if self.state in (VillagerState.IDLE, VillagerState.SPAWNING, VillagerState.EATING):
            pass
        elif self.state == VillagerState.FARMING and self.location == Map.VILLAGE:
            self.simulation.farm.new_wheat += self.Farming
        elif self.state == VillagerState.ATTACKING and self.location == Map.CAVE:
            self.attack()
        elif self.state == VillagerState.MOVING_TO_VILLAGE:
            self.location = Map.VILLAGE
            self.state = VillagerState.IDLE
        elif self.state == VillagerState.MOVING_TO_CAVE:
            self.location = Map.CAVE
            self.state = VillagerState.IDLE

        # starvation: the villager did not eat for `meal_interval` consecutive steps
        if self.is_starving and self.simulation.starvation_damage:
            self.get_attacked(self.simulation.starvation_damage)

    @property
    def is_starving(self) -> bool:
        return bool(self.simulation.meal_interval) and self.steps_since_meal >= self.simulation.meal_interval

    def attack(self):
        if self.simulation.hungry_cannot_attack and self.is_starving:
            return  # too weak to fight
        self.simulation.dragon.get_attacked(self.Attack)

    @property
    def role(self):
        return

    def get_attacked(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.die()

    def die(self):
        self.simulation.remove_component(self)

    def __repr__(self):
        return f"{self.name} ({self.role})"

    def __str__(self):
        return self.name


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
    index = Farmer._count + Warrior._count
    name = NAMES[index % len(NAMES)]
    count = index // len(NAMES)
    if count > 0:
        name += str(count)
    return name
