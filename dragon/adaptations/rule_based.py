import random
from typing import TYPE_CHECKING

from base_classes.adaptation import Adaptation
from dragon.components.villagers import Farmer, Warrior, VillagerState
from dragon.simulation import DragonHuntSimulation, Map

if TYPE_CHECKING:
    from dragon.simulation import DragonHuntSimulation


class RuleBasedMTAdaptation(Adaptation):
    """All warriors should attack, all farmers should farm. If we have enough wheat, spawn new villager while keeping same number of farmers and warriors."""

    def adapt(self, simulation: "DragonHuntSimulation", step: int):
        farmers_village = [component for component in simulation.components if isinstance(component, Farmer) and component.location == Map.VILLAGE]
        farmers_cave = [component for component in simulation.components if isinstance(component, Farmer) and component.location == Map.CAVE]
        warriors = [component for component in simulation.components if isinstance(component, Warrior)]

        for farmer in farmers_village:
            farmer.state = VillagerState.FARMING
        for farmer in farmers_cave:
            farmer.state = VillagerState.MOVING_TO_VILLAGE

        for warrior in warriors:
            if warrior.location == Map.CAVE:
                warrior.state = VillagerState.ATTACKING
            elif warrior.location == Map.VILLAGE:
                warrior.state = VillagerState.MOVING_TO_CAVE

        if len(farmers_village) >= 2:  # enough farmers for spawning
            if simulation.wheat >= Farmer.SpawnCost:
                if simulation.wheat >= Warrior.SpawnCost and len(warriors) <= len(farmers_village) + len(farmers_cave):
                    simulation.spawn_warrior(farmers_village[:2])
                else:
                    simulation.spawn_farmer(farmers_village[:2])
