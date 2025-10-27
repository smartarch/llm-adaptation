from typing import Optional
import csv

from dragon.components.villagers import VillagerState, Villager, Farmer, Warrior
from dragon.simulation import DragonHuntSimulation, Map


class Stats:

    def __init__(self, simulation: "DragonHuntSimulation", file_name: str):
        self.simulation = simulation
        self._csv_file = open(file_name, "w", newline="")
        self.csv_writer = csv.writer(self._csv_file)

    def write_header(self):
        row = self.global_stats(None, header=True)
        self.csv_writer.writerow(row)

    def write_row(self, step: int):
        row = self.global_stats(step)
        row = [f"{value:.2f}" if isinstance(value, float) else value for value in row]
        self.csv_writer.writerow(row)

    def global_stats(self, step: Optional[int], header=False):
        if header:
            return ["step", "dragon_hp", "wheat"] + [state.name for state in VillagerState] + ["farmers_village", "farmers_cave", "warriors_village", "warriors_cave", "spawned_farmers", "spawned_warriors"] + ["dragon_attack"]
        counts_in_states = [
            sum(1 for component in self.simulation.last_components if isinstance(component, Villager) and component.log_state == state)
            for state in VillagerState
        ]
        villager_counts = [
            sum(1 for component in self.simulation.last_components if isinstance(component, Farmer) and component.location == Map.VILLAGE),
            sum(1 for component in self.simulation.last_components if isinstance(component, Farmer) and component.location == Map.CAVE),
            sum(1 for component in self.simulation.last_components if isinstance(component, Warrior) and component.location == Map.VILLAGE),
            sum(1 for component in self.simulation.last_components if isinstance(component, Warrior) and component.location == Map.CAVE)
        ]
        new_spawns = set(self.simulation.components) - set(self.simulation.last_components)
        spawned = [sum(1 for component in new_spawns if isinstance(component, Farmer)), sum(1 for component in new_spawns if isinstance(component, Warrior))]
        return [step, self.simulation.dragon_hp, self.simulation.farm.wheat] + counts_in_states + villager_counts + spawned + [self.simulation.dragon.attack_log]

    def close_file(self):
        self._csv_file.close()
