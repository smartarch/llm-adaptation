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

        if threat_fields_sorted:
            # Build a priority map: field_id -> priority index
            field_priority = {f.id: i for i, f in enumerate(threat_fields_sorted)}

            # Step 1: Balanced full protection distribution
            # Pre-fill with current protectors for each field
            for f in threat_fields_sorted:
                grp = f"protecting {f.id}"
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                        assignments[c] = grp

            # Compute current counts and deficits for full protection
            current_counts = {f.id: len([c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id])
                              for f in threat_fields_sorted}
            deficits = {f.id: max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_counts.get(f.id, 0))
                        for f in threat_fields_sorted}

            # Available drones not yet assigned
            assigned_set = set(assignments.keys())
            available = [d for d in components if d not in assigned_set]

            # Balance: repeatedly allocate from the field with the largest deficit
            while True:
                # choose field with max deficit
                max_def = -1
                chosen_field = None
                for f in threat_fields_sorted:
                    d = deficits.get(f.id, 0)
                    if d > max_def:
                        max_def = d
                        chosen_field = f
                if max_def <= 0 or not available:
                    break

                i = threat_fields_sorted.index(chosen_field)
                cx = (chosen_field.left + chosen_field.right) / 2.0
                cy = (chosen_field.top + chosen_field.bottom) / 2.0

                # Build candidate pool from available
                candidates = []
                for d in available:
                    st = getattr(d, "state", None)
                    if st == "idle":
                        loc = getattr(d, "location", None)
                        dist2 = float("inf")
                        if loc is not None:
                            dx = loc.x - cx
                            dy = loc.y - cy
                            dist2 = dx*dx + dy*dy
                        candidates.append((dist2, d))
                    elif st == "protecting":
                        t_id = getattr(d, "target_id", None)
                        pid = field_priority.get(t_id, 9999)
                        if pid > i:
                            loc = getattr(d, "location", None)
                            dist2 = float("inf")
                            if loc is not None:
                                dx = loc.x - cx
                                dy = loc.y - cy
                                dist2 = dx*dx + dy*dy
                            candidates.append((dist2, d))
                candidates.sort(key=lambda t: t[0])
                if not candidates:
                    break
                dist2, drone = candidates[0]
                assignments[drone] = f"protecting {chosen_field.id}"
                available.remove(drone)
                deficits[chosen_field.id] = max(0, deficits[chosen_field.id] - 1)

            # Step 2: Partial protection distribution using remaining drones
            # Recompute current counts and deficits
            for f in threat_fields_sorted:
                grp = f"protecting {f.id}"
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                        assignments[c] = grp
            current_counts = {f.id: len([c for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id])
                              for f in threat_fields_sorted}
            deficits = {f.id: max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_counts.get(f.id, 0))
                        for f in threat_fields_sorted}
            remaining = [d for d in components if d not in assignments]

            while True:
                max_def = -1
                chosen_field = None
                for f in threat_fields_sorted:
                    d = deficits.get(f.id, 0)
                    if d > max_def:
                        max_def = d
                        chosen_field = f
                if max_def <= 0 or not remaining:
                    break

                i = threat_fields_sorted.index(chosen_field)
                cx = (chosen_field.left + chosen_field.right) / 2.0
                cy = (chosen_field.top + chosen_field.bottom) / 2.0

                candidates = []
                for d in remaining:
                    st = getattr(d, "state", None)
                    if st == "idle":
                        loc = getattr(d, "location", None)
                        dist2 = float("inf")
                        if loc is not None:
                            dx = loc.x - cx
                            dy = loc.y - cy
                            dist2 = dx*dx + dy*dy
                        candidates.append((dist2, d))
                    elif st == "protecting":
                        t_id = getattr(d, "target_id", None)
                        pid = field_priority.get(t_id, 9999)
                        if pid >= i:
                            loc = getattr(d, "location", None)
                            dist2 = float("inf")
                            if loc is not None:
                                dx = loc.x - cx
                                dy = loc.y - cy
                                dist2 = dx*dx + dy*dy
                            candidates.append((dist2, d))
                candidates.sort(key=lambda t: t[0])
                if not candidates:
                    break
                dist2, drone = candidates[0]
                assignments[drone] = f"protecting {chosen_field.id}"
                remaining.remove(drone)
                deficits[chosen_field.id] = max(0, deficits[chosen_field.id] - 1)

        # Step 3: Assign leftovers to idle
        for c in components:
            if c not in assignments:
                assignments[c] = "idle"

        # Apply group assignments
        for comp, gid in assignments.items():
            environment.assign_group(comp, gid)