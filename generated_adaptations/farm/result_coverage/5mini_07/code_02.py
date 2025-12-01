import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        # Compute center of a field rectangle
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, loc, point):
        return math.hypot(loc.x - point[0], loc.y - point[1])

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare mapping of component -> group to assign
        assignment = {}

        # Collect fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        if not fields:
            # No threatened fields: assign all drones to idle
            for c in components:
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")
                else:
                    # Fallback: assign first available group if 'idle' not present
                    environment.assign_group(c, group_ids[0] if group_ids else "idle")
            return

        # Sort fields by descending threat_level, tiebreaker by id for determinism
        fields.sort(key=lambda f: (-f.threat_level, str(f.id)))

        # Helper to record assignments and mark drones as used
        assigned_set = set()

        def mark_assign(comp, group_name):
            assignment[comp] = group_name
            assigned_set.add(comp)

        # Choose the top-priority field (highest threat)
        top_field = fields[0]
        top_group_name = f"protecting {top_field.id}"
        top_center = self._field_center(top_field)
        required_top = int(getattr(top_field, "drones_for_full_protection", 0))

        # Determine drones that are already targeting/protecting the top field
        already_targeting_top = [c for c in components if getattr(c, "target_id", None) == top_field.id]
        # Prefer those already targeting; mark them assigned to top field (we may keep extras)
        for c in already_targeting_top:
            # Only assign to valid group ids
            if top_group_name in group_ids:
                mark_assign(c, top_group_name)

        # Count how many are assigned so far to top field
        assigned_top_count = sum(1 for c in assignment if assignment.get(c) == top_group_name)

        # If fewer than required, pick closest available drones to reach required count
        if assigned_top_count < required_top:
            need = required_top - assigned_top_count
            # Available drones are those not yet assigned
            available = [c for c in components if c not in assigned_set]
            # Sort available by distance to top_field center
            available.sort(key=lambda c: self._distance(c.location, top_center))
            for c in available[:need]:
                if top_group_name in group_ids:
                    mark_assign(c, top_group_name)

        # At this point top field is as protected as we can make it with available drones.
        # Now consider other fields, in descending threat order. Try to fully protect them only if enough drones remain.
        # Compute currently available drones
        available_drones = [c for c in components if c not in assigned_set]

        # Iterate remaining fields (excluding top)
        for field in fields[1:]:
            group_name = f"protecting {field.id}"
            if group_name not in group_ids:
                continue
            required = int(getattr(field, "drones_for_full_protection", 0))
            if required <= 0:
                continue
            if len(available_drones) >= required:
                # Pick closest 'required' drones to this field center
                center = self._field_center(field)
                available_drones.sort(key=lambda c: self._distance(c.location, center))
                chosen = available_drones[:required]
                for c in chosen:
                    mark_assign(c, group_name)
                # Refresh available_drones
                available_drones = [c for c in components if c not in assigned_set]
            else:
                # Not enough drones to fully protect this field; skip (leave drones idle)
                continue

        # Any remaining drones become idle
        for c in components:
            if c not in assignment:
                # Assign to idle if available, else pick any valid group (should not happen)
                if "idle" in group_ids:
                    assignment[c] = "idle"
                else:
                    assignment[c] = group_ids[0] if group_ids else "idle"

        # Finally, perform the assignments through environment.assign_group for every component
        for c, grp in assignment.items():
            environment.assign_group(c, grp)