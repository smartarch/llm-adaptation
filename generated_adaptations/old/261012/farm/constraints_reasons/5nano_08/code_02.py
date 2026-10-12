import math
from typing import List

# Assuming the base class is importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist(self, a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y
        return Point(cx, cy)

    def assign_drones(self, components: List, environment, group_ids, step: int):
        """
        Distribute drones among fields to maximize protection.
        Components: drones with attributes state, target_id, location (with x, y).
        environment.fields: field objects with id, left, top, right, bottom, threat_level, drones_for_full_protection
        Use environment.assign_group(component, group_id) to assign a drone.
        """

        # Gather threatened fields (threat_level > 0)
        fields = list(environment.fields)
        threatened_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort threatened fields by threat_level desc (most threatened first)
        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Helper: compute center of a field
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            class P:
                def __init__(self, x, y):
                    self.x = x
                    self.y = y
            return P(cx, cy)

        top_field = threatened_fields[0]

        # Helper: count drones currently protecting a given field
        def count_protecting(field_id: str) -> int:
            return sum(1 for d in components
                       if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == field_id)

        # Helper: assign a drone to protect a field
        def assign_protect(d, field_id: str):
            environment.assign_group(d, f"protecting {field_id}")

        # Helper: assign idle to a field (or idle)
        def assign_idle(d):
            environment.assign_group(d, "idle")

        # 1) Top field: fully protect with closest drones
        top_center = center_of(top_field)
        total_drones = len(components)
        current_top = count_protecting(top_field.id)
        required_top = min(top_field.drones_for_full_protection, total_drones)
        deficit_top = max(0, required_top - current_top)

        if deficit_top > 0:
            # Candidates: all drones not currently protecting top_field
            candidates = [d for d in components if not (getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == top_field.id)]
            # Split into idle first, then others
            idle_candidates = [d for d in candidates if getattr(d, "state", "") == "idle"]
            other_candidates = [d for d in candidates if getattr(d, "state", "") != "idle"]

            # Sort by distance to top_field center
            idle_candidates.sort(key=lambda d: self._dist(d.location, top_center))
            other_candidates.sort(key=lambda d: self._dist(d.location, top_center))

            selected = []
            # Take from idle first
            take = min(deficit_top, len(idle_candidates))
            selected.extend(idle_candidates[:take])
            deficit_top -= take

            if deficit_top > 0:
                take2 = min(deficit_top, len(other_candidates))
                selected.extend(other_candidates[:take2])
                deficit_top -= take2

            # If still deficit (unlikely), take from any remaining candidates by distance
            if deficit_top > 0:
                remaining = [d for d in candidates if d not in selected]
                remaining.sort(key=lambda d: self._dist(d.location, top_center))
                selected.extend(remaining[:deficit_top])

            # Assign selected drones to protect top_field
            for d in selected:
                assign_protect(d, top_field.id)

        # 2) Protect remaining fields (in threat order)
        # We'll go field by field, attempting to fully protect each using closest available drones.
        # We will avoid moving drones away from the top_field if it is already fully protected.
        # Note: We consider only clearly threatened fields beyond the top one.
        for field in threatened_fields[1:]:
            center = center_of(field)
            current = count_protecting(field.id)
            required = min(field.drones_for_full_protection, total_drones)
            deficit = max(0, required - current)

            if deficit <= 0:
                continue

            # Build candidate drones: not currently protecting this field
            candidates = [d for d in components if not (getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == field.id)]

            # Prioritize idle drones to reduce churn
            idle_candidates = [d for d in candidates if getattr(d, "state", "") == "idle"]
            other_candidates = [d for d in candidates if getattr(d, "state", "") != "idle"]

            idle_candidates.sort(key=lambda d: self._dist(d.location, center))
            other_candidates.sort(key=lambda d: self._dist(d.location, center))

            selected = []
            take = min(deficit, len(idle_candidates))
            selected.extend(idle_candidates[:take])
            deficit -= take

            if deficit > 0:
                take2 = min(deficit, len(other_candidates))
                selected.extend(other_candidates[:take2])
                deficit -= take2

            if deficit > 0:
                remaining = [d for d in candidates if d not in selected]
                remaining.sort(key=lambda d: self._dist(d.location, center))
                selected.extend(remaining[:deficit])

            for d in selected:
                assign_protect(d, field.id)

        # 3) Any drones not assigned to protection should be idle
        protected_field_ids = set(f.id for f in threatened_fields if getattr(f, "id", None))
        for d in components:
            # If drone is protecting some field, keep it; otherwise set to idle
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) in protected_field_ids:
                # Already protecting a valid field; keep as is
                continue
            else:
                # Ensure it's in idle group
                environment.assign_group(d, "idle")