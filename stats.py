from typing import Optional

from components.drone import Drone, DroneState
from components.field import Field
from simulation import SmartFarmSimulation
import csv


class Stats:

    def __init__(self, simulation: "SmartFarmSimulation", file_name: str):
        self.simulation = simulation
        self.csv_file = csv.writer(open(file_name, "w", newline=""))

    def write_header(self):
        row = self.global_stats(None, header=True)
        for drone in self.simulation.drones:
            row += self.drone_stats(drone, header=True)
        for field in self.simulation.fields:
            row += self.field_stats(field, header=True)
        self.csv_file.writerow(row)

    def write_row(self, step: int):
        row = self.global_stats(step)
        for drone in self.simulation.drones:
            row += self.drone_stats(drone)
        for field in self.simulation.fields:
            row += self.field_stats(field)
        row = [f"{value:.2f}" if isinstance(value, float) else value for value in row]
        self.csv_file.writerow(row)

    def global_stats(self, step: Optional[int], header=False):
        if header:
            return ["step", "damage"] + [state.name for state in DroneState]
        total_dmg = sum(field.damage for field in self.simulation.fields)
        drones_in_states = [
            sum(1 for drone in self.simulation.drones if drone.state == state)
            for state in DroneState
        ]
        return [step, total_dmg] + drones_in_states

    @staticmethod
    def drone_stats(drone: Drone, header=False):
        if header:
            return [f"{drone.id}_battery", f"{drone.id}_state", f"{drone.id}_target"]
        return [drone.battery, drone.state.name, drone.target.id if drone.target is not None else None]

    @staticmethod
    def field_stats(field: Field, header=False):
        if header:
            return [f"{field.id}_damage", f"{field.id}_threat_level", f"{field.id}_protecting_drones"]
        return [field.damage, field.threat_level(), len(field.protectingDrones)]
