# Improved adaptation strategy:
# - Protect fields in order of descending threat_level.
# - For each field, allocate the closest available drones to reach full_protection.
# - Keep already-protecting drones on their current targets unless they are the most logical choice to reallocate
#   (we'll avoid moving already-protecting drones to other fields in this simple strategy to reduce jitter).
# - Remaining drones become idle.

from typing import List
import abc
import math

try:
    from generated_adaptations.base_classes.farm import FarmAdaptation
except Exception:
    class FarmAdaptation(abc.ABC):
        def __init__(self, **kwargs):
            pass

        @abc.abstractmethod
        def assign_drones(self, components, environment, group_ids, step: int):
            pass


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _center_of_field(self, field):
        left = getattr(field, "left", 0)
        top = getattr(field, "top", 0)
        right = getattr(field, "right", 0)
        bottom = getattr(field, "bottom", 0)
        cx = (left + right) / 2.0
        cy = (top + bottom) / 2.0
        return cx, cy

    def _distance(self, p, q):
        dx = getattr(p, "x", 0) - getattr(q, "x", 0)
        dy = getattr(p, "y", 0) - getattr(q, "y", 0)
        return (dx * dx + dy * dy) ** 0.5

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with threat > 0
        fields = getattr(environment, "fields", []) or []
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # If no threat, send all drones to idle
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level descending
        threat_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Prepare: compute current protecting drones per field
        field_current = {}
        for f in threat_fields:
            fid = getattr(f, "id", None)
            curr = []
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                    curr.append(d)
            field_current[fid] = curr

        # Drones available to assign (not currently protecting a field or we allow realloc if needed)
        # We'll prefer assigning idle or not currently protecting; we won't move drones already protecting a field
        available = []
        for d in components:
            if getattr(d, "state", None) == "protecting":
                # skip reallocating already protecting drones
                continue
            available.append(d)

        # Also consider drones moving_to_field as available if they are heading to threat fields yet to be protected
        moving_to = [d for d in components if getattr(d, "state", None) == "moving_to_field"]
        moving_to_available = []
        for d in moving_to:
            # If their target is among threat fields and that field still needs protection, we could keep them on the path.
            # For simplicity, treat moving_to_field drones as available if they are heading to a top field
            target = getattr(d, "target_id", None)
            if target in [getattr(f, "id", None) for f in threat_fields]:
                moving_to_available.append(d)

        # Combine and dedupe
        available = available + moving_to_available
        # Remove duplicates while preserving order
        seen = set()
        avail_unique = []
        for d in available:
            if id(d) not in seen:
                avail_unique.append(d)
                seen.add(id(d))
        available = avail_unique

        # Helper to assign a drone to a field's protecting group
        def assign_to_field(drone, field):
            fid = getattr(field, "id", None)
            if fid is None:
                return
            environment.assign_group(drone, f"protecting {fid}")

        # Step through threat fields by priority and fill to full protection
        allocated = set()  # track drones we assign in this run

        for field in threat_fields:
            fid = getattr(field, "id", None)
            if fid is None:
                continue

            current = field_current.get(fid, [])
            current_count = len(current)
            required = getattr(field, "drones_for_full_protection", 0)

            # If already fully protected, keep existing drones and continue
            if current_count >= max(0, required):
                for d in current:
                    allocated.add(id(d))
                    # Ensure they are in the correct group (protecting {fid})
                    environment.assign_group(d, f"protecting {fid}")
                continue

            need = max(0, required - current_count)
            # Choose closest available drones
            candidates = []
            for d in available:
                # compute distance to field center
                cx, cy = self._center_of_field(field)
                # drone location
                dx = getattr(d.location, "x", 0)
                dy = getattr(d.location, "y", 0)
                dist = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
                candidates.append((dist, d))

            # sort by distance
            candidates.sort(key=lambda t: t[0])
            for dist, d in candidates:
                if need <= 0:
                    break
                assign_to_field(d, field)
                allocated.add(id(d))
                available.remove(d)
                need -= 1

            # If any still needed after exhausted available, skip (not enough drones)

        # Step: Remaining drones go idle
        for d in components:
            if id(d) in allocated:
                continue
            environment.assign_group(d, "idle")