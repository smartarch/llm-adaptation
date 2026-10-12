from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper: safe group membership check
        def valid_group(name):
            return name in group_ids

        # Build list of fields with positive threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Pick the field with the highest threat_level (break ties by id for determinism)
        highest = max(threatened_fields, key=lambda f: (f.threat_level, str(f.id)))

        # Field center for distance calculations
        cx = (highest.left + highest.right) / 2.0
        cy = (highest.top + highest.bottom) / 2.0

        # Number of drones required for full protection
        needed = int(getattr(highest, "drones_for_full_protection", 0))

        # Prepare component list with indices for stable handling
        comps = list(components)
        n = len(comps)

        # Compute distances of every drone to the highest-threat field center
        distances = []
        for i, c in enumerate(comps):
            lx = getattr(c.location, "x", 0.0)
            ly = getattr(c.location, "y", 0.0)
            dist = math.hypot(lx - cx, ly - cy)
            distances.append((dist, i))

        # Identify drones already protecting the highest field
        protecting_now = [i for i, c in enumerate(comps)
                          if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == highest.id]

        assigned_indices = set()

        # If already fully protected, keep those drones (keep all currently protecting that field)
        if len(protecting_now) >= needed and needed > 0:
            assigned_indices.update(protecting_now)
        else:
            # Need to gather closest drones (and keep any currently protecting the highest field)
            assigned_indices.update(protecting_now)
            remaining_needed = max(0, min(needed, n) - len(assigned_indices))
            # Sort drones by distance and pick the closest ones that are not already included
            distances.sort(key=lambda x: x[0])
            for _, idx in distances:
                if remaining_needed <= 0:
                    break
                if idx in assigned_indices:
                    continue
                assigned_indices.add(idx)
                remaining_needed -= 1

        # Now assign groups:
        # - Drones in assigned_indices => protecting highest field
        # - For other drones: if they are protecting some other threatened field, keep them protecting it (explicit reassign)
        # - Otherwise set to idle
        # Precompute valid protecting group names for threatened fields
        threatened_ids = {f.id for f in threatened_fields}
        for i, c in enumerate(comps):
            if i in assigned_indices:
                grp = f"protecting {highest.id}"
                if not valid_group(grp):
                    # Fallback to idle if group not present (should not happen per spec)
                    grp = "idle"
                environment.assign_group(c, grp)
            else:
                # Keep other protected drones protecting their fields if that field is still threatened
                if getattr(c, "state", None) == "protecting":
                    tgt = getattr(c, "target_id", None)
                    if tgt in threatened_ids:
                        grp = f"protecting {tgt}"
                        if valid_group(grp):
                            environment.assign_group(c, grp)
                            continue
                # Otherwise idle
                environment.assign_group(c, "idle")