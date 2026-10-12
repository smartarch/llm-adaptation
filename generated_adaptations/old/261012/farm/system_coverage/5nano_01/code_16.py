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
        field_index = {f.id: i for i, f in enumerate(threat_fields_sorted)}

        assignments = {}  # component -> group_id

        if threat_fields_sorted:
            # Pre-assign current protectors to their groups
            for f in threat_fields_sorted:
                grp = f"protecting {f.id}"
                for c in components:
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id:
                        assignments[c] = grp

            # Build deficits: how many drones are needed to fully protect each field
            deficits = {}
            for f in threat_fields_sorted:
                current = len([
                    c for c in components
                    if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id
                ])
                deficits[f.id] = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current)

            # Pool of unassigned drones
            unassigned = [c for c in components if c not in assignments]

            # Balance allocation by selecting field with largest threat * deficit
            while True:
                best_field = None
                best_score = -1.0
                for f in threat_fields_sorted:
                    d = deficits.get(f.id, 0)
                    if d <= 0:
                        continue
                    score = float(f.threat_level) * float(d)
                    if score > best_score:
                        best_score = score
                        best_field = f

                if best_field is None or not unassigned:
                    break

                i = field_index[best_field.id]
                cx = (best_field.left + best_field.right) / 2.0
                cy = (best_field.top + best_field.bottom) / 2.0

                candidates = []
                for d in unassigned:
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
                        pid = field_index.get(t_id, 9999)
                        # Only reallocate from lower-priority fields
                        if pid > i:
                            loc = getattr(d, "location", None)
                            dist2 = float("inf")
                            if loc is not None:
                                dx = loc.x - cx
                                dy = loc.y - cy
                                dist2 = dx*dx + dy*dy
                            candidates.append((dist2, d))

                if not candidates:
                    break
                candidates.sort(key=lambda t: t[0])
                _, drone = candidates[0]
                assignments[drone] = f"protecting {best_field.id}"
                unassigned.remove(drone)
                deficits[best_field.id] -= 1

        # Step 2: Assign any remaining drones to idle (to ensure every drone is assigned)
        for c in components:
            if c not in assignments:
                assignments[c] = "idle"

        # Apply group assignments
        for comp, gid in assignments.items():
            environment.assign_group(comp, gid)