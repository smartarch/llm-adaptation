"""Assign drones randomly."""
import random

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        for drone in components:
            field = random.choice(environment.fields)
            environment.assign_group(drone, f"protecting {field.id}")
