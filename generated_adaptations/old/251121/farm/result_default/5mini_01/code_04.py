import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Greedy multi-field protector:
        - Sort fields by descending threat_level.
        - For each threatened field, ensure it is fully protected by assigning the closest available drones.
        - If a field is already fully protected by drones currently targeting it (protecting/moving_to_field),
          keep those drones locked to that field.
        - Continue to next field until drones are exhausted.
        - Any remaining drones are assigned to 'idle'.
        """
        # Helper: compute Euclidean distance from drone to field center
        def dist_to_field_center(drone, field):
            loc = getattr(drone, "location", None)
            center_x = (field.left + field.right) / 2.0
            center_y = (field.top + field.bottom) / 2.0
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0) - center_x
            dy = getattr(loc, "y", 0) - center_y
            return math.hypot(dx, dy)

        # Collect threatened fields sorted by threat descending
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # Nothing to protect: assign all drones to idle
            idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
            for c in components:
                environment.assign_group(c, idle_group)
            return

        threatened_fields.sort(key=lambda f: f.threat_level, reverse=True)

        # Map field_id -> list of drones currently targeting/protecting that field
        current_assigned = {}
        for f in threatened_fields:
            current_assigned[f.id] = []
        for c in components:
            tid = getattr(c, "target_id", None)
            st = getattr(c, "state", None)
            if tid is None:
                continue
            # consider drones that are protecting or moving_to_field as currently assigned
            if st in ("protecting", "moving_to_field") and tid in current_assigned:
                current_assigned[tid].append(c)

        # Start with all drones available
        available = set(components)
        locked = set()  # drones locked to fields we've decided to fully protect
        assignments = {}  # drone -> group_name

        # Iterate fields by decreasing threat. For each, try to fully protect using closest available drones.
        for field in threatened_fields:
            # required drones (ceil to be safe)
            try:
                required = int(math.ceil(float(field.drones_for_full_protection)))
            except Exception:
                required = 0

            if required <= 0:
                continue

            # Drones that are currently targeting this field (and are candidates to stay)
            currently = [d for d in current_assigned.get(field.id, []) if d in available and d not in locked]

            # If already fully protected by current assignments, lock and keep them
            if len(currently) >= required:
                for d in currently:
                    assignments[d] = f"protecting {field.id}" if f"protecting {field.id}" in group_ids else "idle"
                    locked.add(d)
                    if d in available:
                        available.remove(d)
                continue

            # Need additional drones. We may choose from available drones (which may include drones currently assigned elsewhere
            # except those already locked because they protect other fields fully)
            # Build list of candidate drones = available - locked (locked already removed from available)
            candidates = list(available)  # available already excludes previously locked ones
            # Sort candidates by distance to this field center
            candidates.sort(key=lambda d: dist_to_field_center(d, field))

            # Select best 'required' drones from candidates
            selected = candidates[:required]

            # Assign and lock the selected drones
            for d in selected:
                assignments[d] = f"protecting {field.id}" if f"protecting {field.id}" in group_ids else "idle"
                locked.add(d)
                if d in available:
                    available.remove(d)

            # If we selected fewer than required (not enough drones), we still lock what we have and continue;
            # remaining fields will not be protected if no drones remain.

        # Any drones not assigned are idle
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
        for d in components:
            group = assignments.get(d, idle_group)
            environment.assign_group(d, group)