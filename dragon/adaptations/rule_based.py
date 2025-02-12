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
            simulation.assign_group(farmer, "farm")
        for farmer in farmers_cave:
            simulation.assign_group(farmer, "village")

        for warrior in warriors:
            if warrior.location == Map.CAVE:
                simulation.assign_group(warrior, "attack")
            elif warrior.location == Map.VILLAGE:
                simulation.assign_group(warrior, "cave")

        if len(farmers_village) >= 2:  # enough farmers for spawning
            if simulation.wheat >= Farmer.SpawnCost:
                if simulation.wheat >= Warrior.SpawnCost and len(warriors) <= len(farmers_village) + len(farmers_cave):
                    simulation.assign_group(farmers_village[0], "spawn warrior")
                    simulation.assign_group(farmers_village[1], "spawn warrior")
                else:
                    simulation.assign_group(farmers_village[0], "spawn farmer")
                    simulation.assign_group(farmers_village[1], "spawn farmer")


class RuleBasedRandomAdaptation(Adaptation):

    def adapt(self, simulation: "DragonHuntSimulation", step: int):

        village = [component for component in simulation.components if component.location == Map.VILLAGE]
        cave = [component for component in simulation.components if component.location == Map.CAVE]

        for villager in village:
            simulation.assign_group(villager, random.choice(["farm", "cave", "spawn farmer", "spawn warrior"]))
        for villager in cave:
            simulation.assign_group(villager, random.choice(["attack", "cave", "village"]))
