# Strategy rationale and implementation notes:
# - Objective: improve protection by fully protecting the highest-threat field first,
#   then help additional fields if drones remain, while avoiding destabilizing protections on-the-fly.
# - Approach:
#   1) Identify all fields with threat_level > 0, sort by threat descending.
#   2) Recalculate current protection counts for all threatened fields.
#   3) For the top field, allocate the minimum number of closest non-protecting drones needed to reach full_protection.
#   4) Recalculate protection counts, then for the remaining fields (in threat order) allocate any remaining drones
#      to achieve full protection if possible, always using the closest available drones.
#   5) Drones that are not assigned to protection in this step and are not currently protecting anything are sent idle.
# - This keeps drones protecting already-protected fields unless they are needed for higher-threat fields,
#   prioritizes speed (closest drones), and avoids leaving the top threat unprotected.

from typing import List

# Assuming the base class is importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # No threat: idle all drones
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (highest first)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Helper to compute field center
        def center_of(field):
            cx = (getattr(field, "left", 0) + getattr(field, "right", 0)) / 2.0
            cy = (getattr(field, "top", 0) + getattr(field, "bottom", 0)) / 2.0
            return cx, cy

        # Track drones assigned to protect in this cycle
        assigned_to_protect = set()

        # Step 1: compute current protection counts for all threatened fields
        counts = {f.id: 0 for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t in counts:
                    counts[t] += 1

        # Step 2: Ensure the top field is fully protected
        top_field = threatened_fields[0]
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        top_current = counts.get(top_field.id, 0)
        top_needed = max(0, top_required - top_current)

        if top_needed > 0:
            cx, cy = center_of(top_field)
            # Build candidate drones: those not already protecting the top field, and not already assigned
            candidates = []
            for d in components:
                if d in assigned_to_protect:
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    # Already protecting the top field, skip as candidate
                    continue
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))
            candidates.sort(key=lambda x: x[0])

            for dist, drone in candidates:
                if top_needed <= 0:
                    break
                environment.assign_group(drone, f"protecting {top_field.id}")
                assigned_to_protect.add(drone)
                # count increment for top field
                counts[top_field.id] = counts.get(top_field.id, 0) + 1
                top_needed -= 1

        # Step 3: Recompute counts to reflect any changes
        counts = {f.id: 0 for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                t = getattr(d, "target_id", None)
                if t in counts:
                    counts[t] += 1

        # Step 4: Allocate remaining drones to other threatened fields in order
        # Use remaining non-assigned drones, closest to each field center.
        for field in threatened_fields[1:]:
            required = int(getattr(field, "drones_for_full_protection", 0))
            current = counts.get(field.id, 0)
            needed = max(0, required - current)
            if needed <= 0:
                continue

            cx, cy = center_of(field)
            candidates = []
            for d in components:
                if d in assigned_to_protect:
                    continue
                # If drone is already protecting this field, skip (would be counted in current)
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    continue
                dx = getattr(d.location, "x", 0.0) - cx
                dy = getattr(d.location, "y", 0.0) - cy
                dist = (dx*dx + dy*dy) ** 0.5
                candidates.append((dist, d))
            candidates.sort(key=lambda x: x[0])

            for dist, drone in candidates:
                if needed <= 0:
                    break
                environment.assign_group(drone, f"protecting {field.id}")
                assigned_to_protect.add(drone)
                counts[field.id] = counts.get(field.id, 0) + 1
                needed -= 1

        # Step 5: Idle drones that are not protecting anything and were not assigned to protection
        for d in components:
            if d in assigned_to_protect:
                continue
            if getattr(d, "state", None) == "protecting":
                # Drone is protecting some field; leave it as is
                continue
            environment.assign_group(d, "idle")