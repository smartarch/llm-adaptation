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

        # Map field_id to field object and compute centers
        field_by_id = {f.id: f for f in threatened_fields}
        centers = {}
        for f in threatened_fields:
            centers[f.id] = (
                (getattr(f, "left", 0) + getattr(f, "right", 0)) / 2.0,
                (getattr(f, "top", 0) + getattr(f, "bottom", 0)) / 2.0,
            )

        # Step 1: Compute current protection counts (protecting) and arriving counts
        protecting_counts = {f.id: 0 for f in threatened_fields}
        arriving_counts = {f.id: 0 for f in threatened_fields}
        for d in components:
            s = getattr(d, "state", None)
            t = getattr(d, "target_id", None)
            if s == "protecting" and t in protecting_counts:
                protecting_counts[t] += 1
            elif s == "moving_to_field" and t in arriving_counts:
                arriving_counts[t] += 1
        # Include any arriving_drones information present on fields
        for f in threatened_fields:
            arriving_counts[f.id] += int(getattr(f, "arriving_drones", 0)) if isinstance(getattr(f, "arriving_drones", 0), int) else 0

        # Step 2: Compute deficits for each field
        deficits = {}
        for f in threatened_fields:
            current = protecting_counts.get(f.id, 0) + arriving_counts.get(f.id, 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            deficits[f.id] = max(0, required - current)

        if all(v == 0 for v in deficits.values()):
            # All fields fully protected; idle non-protecting drones
            for d in components:
                if getattr(d, "state", None) != "protecting":
                    environment.assign_group(d, "idle")
            return

        # Step 3: Greedy global allocation
        assigned = set()

        # Loop until no deficits or run out of candidates
        while any(deficits[fid] > 0 for fid in deficits) and len(assigned) < len(components):
            best_score = -1.0
            best_drone = None
            best_field_id = None

            for d in components:
                if d in assigned:
                    continue
                # We allow reassigning non-protecting drones; skip currently protecting drones
                if getattr(d, "state", None) == "protecting":
                    continue
                dx = getattr(d.location, "x", 0.0)
                dy = getattr(d.location, "y", 0.0)

                # Evaluate best field for this drone
                best_for_drone_score = -1.0
                best_for_drone_field = None

                for fid, need in deficits.items():
                    if need <= 0:
                        continue
                    cx, cy = centers[fid]
                    dist = ((dx - cx) ** 2 + (dy - cy) ** 2) ** 0.5
                    threat = getattr(field_by_id[fid], "threat_level", 0)
                    score = float(threat) / (dist + 1e-6)
                    if score > best_for_drone_score:
                        best_for_drone_score = score
                        best_for_drone_field = fid

                if best_for_drone_field is not None and best_for_drone_score > best_score:
                    best_score = best_for_drone_score
                    best_drone = d
                    best_field_id = best_for_drone_field

            if best_drone is None or best_field_id is None or best_score <= 0:
                break

            # Assign the best drone to the best field
            environment.assign_group(best_drone, f"protecting {best_field_id}")
            assigned.add(best_drone)
            deficits[best_field_id] -= 1

        # Step 4: Idle drones not assigned to protection
        for d in components:
            if d in assigned:
                continue
            if getattr(d, "state", None) == "protecting":
                continue
            environment.assign_group(d, "idle")