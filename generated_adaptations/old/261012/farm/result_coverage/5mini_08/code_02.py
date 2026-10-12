from typing import List
from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones to groups according to the following strategy:
        - Identify the field with the highest threat_level (only among fields with threat_level > 0).
          If multiple fields tie, pick the one with the smallest id (deterministic tie-break).
        - Count drones already targeting that field (target_id == field.id). If that count >= required,
          keep them assigned to that protecting group. If fewer, add the closest other drones until the
          required number is reached (or until we run out of drones).
        - All other drones are assigned to "idle".
        """
        # Helper to compute center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to compute Euclidean distance between drone and a point
        def dist(drone, point):
            dx = drone.location.x - point[0]
            dy = drone.location.y - point[1]
            return hypot(dx, dy)

        # Build list of fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, put everyone idle
        if not threatened_fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    # Fallback: pick any provided group (shouldn't happen given spec)
                    environment.assign_group(comp, group_ids[0])
            return

        # Choose the field with the highest threat_level. Tie-break by field.id for determinism.
        threatened_fields.sort(key=lambda f: (-f.threat_level, str(f.id)))
        target_field = threatened_fields[0]
        protect_group = f"protecting {target_field.id}"
        idle_group = "idle"

        # Compute required number of drones for full protection
        try:
            required = int(target_field.drones_for_full_protection)
        except Exception:
            required = 0

        # Determine drones already targeting this field (target_id == field.id)
        already_targeting = [d for d in components if d.target_id == target_field.id]

        # If already targeting are enough (>= required), keep them all there
        assigned_to_protect = set()
        for d in already_targeting:
            assigned_to_protect.add(d)

        # If not enough, pick closest drones among the rest to reach 'required'
        if len(assigned_to_protect) < required:
            need = required - len(assigned_to_protect)
            center = field_center(target_field)
            # Candidates: drones not already targeting this field
            candidates = [d for d in components if d not in assigned_to_protect]
            # Sort candidates by distance to the field center
            candidates.sort(key=lambda d: dist(d, center))
            # Select up to 'need' closest drones
            for d in candidates[:need]:
                assigned_to_protect.add(d)

        # Now assign groups: those in assigned_to_protect -> protect_group, others -> idle
        for comp in components:
            if comp in assigned_to_protect:
                # Ensure group exists in group_ids, otherwise fallback to first valid protecting group
                if protect_group in group_ids:
                    environment.assign_group(comp, protect_group)
                else:
                    # fallback: pick any protecting group that matches prefix or default to idle
                    matched = next((g for g in group_ids if g.startswith("protecting ")), None)
                    environment.assign_group(comp, matched if matched is not None else idle_group)
            else:
                if idle_group in group_ids:
                    environment.assign_group(comp, idle_group)
                else:
                    # fallback to any group if idle missing
                    environment.assign_group(comp, group_ids[0])