import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Assign drones so that the field with the highest threat_level is fully protected
        by the closest drones. Keep drones already assigned (protecting or moving_to_field)
        to that target field. All other drones are assigned to 'idle'.
        """
        # Find fields that currently have threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, put all drones to idle
        if not threatened_fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    # fallback: assign first allowed group if 'idle' not present
                    environment.assign_group(comp, group_ids[0] if group_ids else "idle")
            return

        # Choose the field with the highest threat level
        target_field = max(threatened_fields, key=lambda f: f.threat_level)
        target_group = f"protecting {target_field.id}"

        # Compute field center for distance calculations
        center_x = (target_field.left + target_field.right) / 2.0
        center_y = (target_field.top + target_field.bottom) / 2.0

        # Number of drones required for full protection (use ceil to be safe)
        try:
            required = int(math.ceil(float(target_field.drones_for_full_protection)))
        except Exception:
            # fallback if attribute missing or invalid
            required = 0

        # Identify drones already effectively assigned to this field (protecting or en route)
        current_assigned = []
        for c in components:
            if getattr(c, "target_id", None) == target_field.id and getattr(c, "state", None) in ("protecting", "moving_to_field"):
                current_assigned.append(c)

        num_current = len(current_assigned)
        needed = max(0, required - num_current)

        # Prepare candidate drones (those not already assigned to this target field)
        candidates = []
        for c in components:
            if c in current_assigned:
                continue
            loc = getattr(c, "location", None)
            if loc is None:
                # treat unknown location as very far
                dist = float("inf")
            else:
                dx = getattr(loc, "x", 0) - center_x
                dy = getattr(loc, "y", 0) - center_y
                dist = math.hypot(dx, dy)
            candidates.append((dist, c))

        # Sort candidates by distance and pick the closest ones needed
        candidates.sort(key=lambda tup: tup[0])
        newly_assigned = [c for _, c in candidates[:needed]]

        # Build set of drones that should be assigned to the protecting group
        protecting_set = set(current_assigned) | set(newly_assigned)

        # Ensure the target group name exists in group_ids; otherwise we will fallback to 'idle'
        use_protect_group = target_group if target_group in group_ids else None
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Assign every component exactly one group (explicitly re-assigning those that stay)
        for c in components:
            if c in protecting_set and use_protect_group is not None:
                environment.assign_group(c, use_protect_group)
            else:
                environment.assign_group(c, idle_group)