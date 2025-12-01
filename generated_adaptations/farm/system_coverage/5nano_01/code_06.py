from typing import List
# The base class is assumed to be importable as described
from generated_adaptations.base_classes.farm import FarmAdaptation  # type: ignore

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Gather fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Sort fields by decreasing threat, then by id for deterministic ordering
        threat_fields_sorted = sorted(threat_fields, key=lambda f: (-f.threat_level, f.id))

        assignments = {}  # component -> group_id

        # Helper: determine field priority index
        field_priority = {f.id: i for i, f in enumerate(threat_fields_sorted)}

        # Step 1: Fully protect as many top fields as possible, prioritizing higher-threat fields
        for i, f in enumerate(threat_fields_sorted):
            grp = f"protecting {f.id}"

            # Current protectors for this field
            current_protectors = [
                c for c in components
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
            ]
            # Ensure current protectors stay in this field's group
            for c in current_protectors:
                assignments[c] = grp

            current_count = len(current_protectors)
            required = int(getattr(f, "drones_for_full_protection", 0))
            needed = max(0, required - current_count)

            if needed <= 0:
                continue

            # Center of the field
            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0

            # Candidate pool: idle drones first, then drones from lower-priority fields
            candidates = []
            for c in components:
                if c in assignments:
                    continue
                state = getattr(c, "state", None)

                # Only allow using idle drones or drones protecting lower-priority fields
                if state == "idle":
                    loc = getattr(c, "location", None)
                    dist2 = float("inf")
                    if loc is not None:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        dist2 = dx*dx + dy*dy
                    candidates.append((dist2, c))
                elif state == "protecting":
                    t_id = getattr(c, "target_id", None)
                    pid = field_priority.get(t_id, 9999)
                    if pid > i:  # can reallocate from lower-priority fields
                        loc = getattr(c, "location", None)
                        dist2 = float("inf")
                        if loc is not None:
                            dx = loc.x - cx
                            dy = loc.y - cy
                            dist2 = dx*dx + dy*dy
                        candidates.append((dist2, c))
                # else: ignore moving drones that are moving to a field or in unknown state

            # Sort by distance and assign up to needed drones
            candidates.sort(key=lambda t: t[0])
            for dist2, d in candidates[:needed]:
                assignments[d] = grp

        # Step 2: Partial protection for remaining fields using leftovers
        # Remaining drones that are not yet assigned
        remaining = [c for c in components if c not in assignments]

        for i, f in enumerate(threat_fields_sorted):
            if not remaining:
                break
            grp = f"protecting {f.id}"
            # Current protectors for this field (could have changed)
            current_protectors = [
                c for c in components
                if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
            ]
            current_count = len(current_protectors)

            # If already fully protected, ensure they are in the correct group
            for c in current_protectors:
                assignments[c] = grp

            # If already full, skip
            if current_count >= int(getattr(f, "drones_for_full_protection", 0)):
                continue

            # Number of additional drones we would like to place for partial protection
            remaining_needed = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_count)

            if remaining_needed <= 0:
                continue

            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0

            # Build candidate pool from remaining
            candidates = []
            for c in remaining:
                # Do not steal from higher-priority fields
                t_id = getattr(c, "target_id", None)
                pid = field_priority.get(t_id, 9999)
                if pid < i:
                    continue  # skip higher priority field's drone
                loc = getattr(c, "location", None)
                dist2 = float("inf")
                if loc is not None:
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist2 = dx*dx + dy*dy
                candidates.append((dist2, c))

            candidates.sort(key=lambda t: t[0])

            # Assign as many as possible to partially protect this field
            take = min(remaining_needed, len(candidates))
            for dist2, d in candidates[:take]:
                assignments[d] = grp
                remaining.remove(d)

        # Step 3: Any drone not assigned yet -> idle
        for c in components:
            if c not in assignments:
                assignments[c] = "idle"

        # Apply group assignments
        for comp, group_id in assignments.items():
            environment.assign_group(comp, group_id)