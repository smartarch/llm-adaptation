from typing import List
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: compute Euclidean distance between drone and field center
        def distance_to_field(drone, field):
            fx = (field.left + field.right) / 2.0
            fy = (field.top + field.bottom) / 2.0
            dx = getattr(drone.location, "x", 0) - fx
            dy = getattr(drone.location, "y", 0) - fy
            return math.hypot(dx, dy)

        # Find fields with threat_level > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign everyone to idle
        if not threatened_fields:
            idle_group = "idle"
            if idle_group not in group_ids:
                # Fallback: if idle group not present for some reason, do nothing
                return
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Choose the field with highest threat_level; deterministic tie-break by field.id
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        top_field = threatened_fields[0]
        protect_group = f"protecting {top_field.id}"
        idle_group = "idle"

        # Ensure group ids exist; if protecting group is not available, fallback to idle for all
        if protect_group not in group_ids or idle_group not in group_ids:
            for comp in components:
                # Assign to idle if available, else skip
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
            return

        needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Identify drones already protecting the top field
        already_protecting = []
        others = []
        for comp in components:
            if getattr(comp, "state", None) == "protecting" and getattr(comp, "target_id", None) == top_field.id:
                already_protecting.append(comp)
            else:
                others.append(comp)

        # If already enough, keep those drones; otherwise select additional drones
        selected = list(already_protecting)
        if len(selected) < needed:
            # Build candidate lists:
            # prefer drones that are NOT protecting other fields first
            non_protecting_others = []
            protecting_others = []
            for comp in others:
                if getattr(comp, "state", None) == "protecting":
                    # protecting some other field
                    protecting_others.append(comp)
                else:
                    non_protecting_others.append(comp)

            # Sort each candidate list by distance to top_field
            non_protecting_others.sort(key=lambda c: distance_to_field(c, top_field))
            protecting_others.sort(key=lambda c: distance_to_field(c, top_field))

            # Fill from non_protecting_others first
            for comp in non_protecting_others:
                if len(selected) >= needed:
                    break
                selected.append(comp)

            # If still need, take from protecting_others
            for comp in protecting_others:
                if len(selected) >= needed:
                    break
                selected.append(comp)

        # Create a set for quick membership checks
        selected_set = set(selected)

        # Assign groups: selected -> protecting top_field; all others -> idle
        for comp in components:
            if comp in selected_set:
                environment.assign_group(comp, protect_group)
            else:
                environment.assign_group(comp, idle_group)