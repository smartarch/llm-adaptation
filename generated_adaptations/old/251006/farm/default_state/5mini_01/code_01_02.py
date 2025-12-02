from math import hypot
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Find all fields with threat_level > 0.
        - Pick the field with the highest threat_level. If tie, pick the one whose nearest drone is closest.
        - Ensure that field is fully protected by assigning the closest drones to it (prefer drones already targeting it).
        - If the field already has enough protecting drones (state == "protecting"), keep them there.
        - Assign every other drone to "idle".
        """
        # Prepare group name helper
        idle_group = "idle"

        # Validate idle group existence; if not present, we do nothing (but attempt to use it)
        if idle_group not in group_ids:
            # If "idle" isn't available, abort assigning to avoid invalid group ids.
            # But still attempt to not crash: just return.
            return

        # Candidate fields with positive threat
        candidate_fields = [f for f in getattr(environment, "fields", []) if getattr(f, "threat_level", 0) > 0]

        if not candidate_fields:
            # No threats: assign all drones to idle
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Compute field centers and minimal drone distances for tie-breaking
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Precompute drone positions
        drone_positions = {}
        for comp in components:
            loc = getattr(comp, "location", None)
            if loc is None:
                drone_positions[comp] = (0.0, 0.0)
            else:
                drone_positions[comp] = (getattr(loc, "x", 0.0), getattr(loc, "y", 0.0))

        # For each candidate field compute (threat_level, min_distance_to_any_drone) for tie-break
        field_scores = []
        for f in candidate_fields:
            cx, cy = field_center(f)
            min_dist = min(hypot(px - cx, py - cy) for px, py in drone_positions.values()) if drone_positions else float('inf')
            field_scores.append((f, f.threat_level, min_dist))

        # Sort by descending threat_level, then ascending min_dist
        field_scores.sort(key=lambda t: (-t[1], t[2]))

        # Select the top-priority field
        target_field = field_scores[0][0]
        target_group = f"protecting {target_field.id}"
        # If the group isn't available in provided group_ids, we can't assign to it; fallback to idle for all.
        if target_group not in group_ids:
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        required = int(getattr(target_field, "drones_for_full_protection", 0))

        # Find drones already protecting this field
        protecting_now = [c for c in components if getattr(c, "target_id", None) == target_field.id and getattr(c, "state", None) == "protecting"]

        # If already fully protected, keep those protecting drones there and idle the rest
        if len(protecting_now) >= required:
            protecting_set = set(protecting_now[:required])  # keep at most required (though len>=required)
            # Explicitly assign each component
            for comp in components:
                if comp in protecting_set:
                    environment.assign_group(comp, target_group)
                else:
                    environment.assign_group(comp, idle_group)
            return

        # Otherwise we need to select the closest drones to meet 'required'
        # Sort all drones by (distance to field center, prefer those already targeting this field)
        cx, cy = field_center(target_field)
        def sort_key(comp):
            px, py = drone_positions.get(comp, (0.0, 0.0))
            dist = hypot(px - cx, py - cy)
            # Prefer drones already targeting the field (secondary priority)
            already_targeting = 0 if getattr(comp, "target_id", None) == target_field.id else 1
            return (dist, already_targeting)

        sorted_drones = sorted(components, key=sort_key)

        # Pick first 'required' drones (or all if fewer exist)
        selected_for_protect = set(sorted_drones[:required])

        # Explicitly assign every drone to either protecting group or idle
        for comp in components:
            if comp in selected_for_protect:
                environment.assign_group(comp, target_group)
            else:
                environment.assign_group(comp, idle_group)