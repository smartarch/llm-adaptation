"""Randomly assign all drones except those in MOVING_TO_FIELD state."""
import random

from farm.components.drone import DroneState
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        for drone in components:
            if drone.state == DroneState.MOVING_TO_FIELD:
                continue
            field = random.choice(environment.fields)
            environment.assign_group(drone, f"protecting {field.id}")
