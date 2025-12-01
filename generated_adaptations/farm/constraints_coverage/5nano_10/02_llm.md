Reasoning and adaptation strategy

Goal and constraints
- We must divide the drone components into groups: "idle" and, for each field with threat_level > 0, a group named "protecting {field.id}".
- The drones must be reassigned each step; a drone that should continue its current action must still be explicitly reassigned to that same group.
- The strategy should always protect the field with the highest threat level, using as many drones as needed for full protection (field.drones_for_full_protection). If the field is already fully protected, we should keep those drones protecting it.
- Drones not needed for the top-priority protection should be idle (we avoid reassigning them to other fields unless needed).

Strategy description
- Identify the field with the highest threat level (threat_level > 0). If none, assign all drones to idle.
- Let the target field be highest_field. Determine required_drones = highest_field.drones_for_full_protection (default to 1 if not provided; ensure non-negative).
- Determine how many drones are currently protecting that field (state == "protecting" and target_id == highest_field.id).
- If current_protecting >= required_drones:
  - Keep all drones currently protecting that field in the "protecting {highest_field.id}" group.
  - Reassign all other drones to "idle".
- If current_protecting < required_drones:
  - We need additional drones: needed = required_drones - current_protecting.
  - Build a candidate list from drones not currently protecting the highest field, and sort by distance to the field center (field center is the average of left/right and top/bottom).
  - Pick the closest 'needed' drones from candidates and assign them to "protecting {highest_field.id}".
  - All remaining drones get assigned to "idle".
- This approach emphasizes minimal disruption to other fields, prioritizes the most threatening field, and uses spatial proximity to select the closest available drones.

Python code

```py
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify the field with the highest threat > 0
        fields = getattr(environment, "fields", []) or []
        highest_field = None
        max_threat = 0.0
        for f in fields:
            t = getattr(f, "threat_level", 0.0)
            if t > max_threat and t > 0:
                max_threat = t
                highest_field = f

        # If no threatening field, idle all drones
        if highest_field is None:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Compute center of the field for distance calculations
        cx = (getattr(highest_field, "left", 0.0) + getattr(highest_field, "right", 0.0)) / 2.0
        cy = (getattr(highest_field, "top", 0.0) + getattr(highest_field, "bottom", 0.0)) / 2.0

        # How many drones are required for full protection
        required = int(getattr(highest_field, "drones_for_full_protection", 1))
        if required < 0:
            required = 0

        # Current drones protecting this field
        defending_indices = []
        for i, d in enumerate(components):
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == highest_field.id:
                defending_indices.append(i)

        protect_group = f"protecting {highest_field.id}"

        if len(defending_indices) >= required:
            # Field already fully protected; keep current protectors, others idle
            defending_set = set(defending_indices)
            for idx, d in enumerate(components):
                if idx in defending_set:
                    environment.assign_group(d, protect_group)
                else:
                    environment.assign_group(d, "idle")
            return

        # Need more drones to reach full protection
        needed = max(0, required - len(defending_indices))

        # Build candidate list: drones not currently protecting this field
        defending_set = set(defending_indices)
        candidates = []
        for idx, d in enumerate(components):
            if idx in defending_set:
                continue
            loc = getattr(d, "location", None)
            if loc is None:
                dist = float("inf")
            else:
                dx = getattr(loc, "x", 0.0) - cx
                dy = getattr(loc, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
            candidates.append((dist, idx))

        candidates.sort(key=lambda t: t[0])
        selected = [idx for (_, idx) in candidates[:needed]]
        selected_set = set(selected)

        # Assign selected drones to protect the highest-threat field; others idle
        for idx, d in enumerate(components):
            if idx in defending_set or idx in selected_set:
                environment.assign_group(d, protect_group)
            else:
                environment.assign_group(d, "idle")
```