from typing import List
import math

# Import the base class to derive from
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_top_field_id = None

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Focused, stability-first protection strategy:
        - Identify the field with the highest threat (threat_level > 0).
        - Use idle drones first to fully protect that field (up to drones_for_full_protection).
        - If already fully protected, set all other drones to idle and do not move protecting drones off their fields.
        - Drones are chosen by proximity to the field center to minimize travel time.
        - Maintains a memory of the last top field to reduce thrashing across steps (optional tie-breaker).
        """

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            self._last_top_field_id = None
            return

        # Identify top field by threat level
        top_field = max(threatened_fields, key=lambda f: getattr(f, "threat_level", 0.0))
        top_id = top_field.id
        full_needed = int(getattr(top_field, "drones_for_full_protection", 0))

        # Current drones protecting the top field
        current_top = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_id]
        current_count = len(current_top)

        # Re-affirm their group
        for d in current_top:
            environment.assign_group(d, f"protecting {top_id}")

        assigned = set(current_top)

        # If already fully protected (or full_needed == 0), idle all others
        if current_count >= max(1, full_needed):
            for d in components:
                if d not in assigned:
                    environment.assign_group(d, "idle")
            self._last_top_field_id = top_id
            return

        needed = max(0, full_needed - current_count)

        # Idle drones (not currently protecting any field)
        idle = [d for d in components if getattr(d, "state", "") != "protecting"]

        if idle and needed > 0:
            cx, cy = field_center(top_field)
            idle.sort(key=lambda d: math.hypot(getattr(d.location, "x", 0.0) - cx, getattr(d.location, "y", 0.0) - cy))
            for i in range(min(needed, len(idle))):
                d = idle[i]
                environment.assign_group(d, f"protecting {top_id}")
                assigned.add(d)
                needed -= 1
                if needed <= 0:
                    break

        # After using idle drones, if still not full, we do not steal from other protected fields
        # to minimize disruption, per stability-first approach.

        # Finalize: any drones not assigned to the top field become idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")

        self._last_top_field_id = top_id