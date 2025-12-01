from typing import List
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        # Gather fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Sort fields by threat level (highest first)
        fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = fields[0]

        # Count current protectors for the top field
        cur_top = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id)

        # Prepare final_group_for for all drones
        final_group_for = {c: None for c in components}

        # Step 1: Keep existing top-field protectors and add more if needed (closest drones)
        top_protectors = []
        for c in components:
            if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == top_field.id:
                final_group_for[c] = f"protecting {top_field.id}"
                top_protectors.append(c)

        needed_top = max(0, int(getattr(top_field, "drones_for_full_protection", 0) - cur_top))
        if needed_top > 0:
            center_top = ((top_field.left + top_field.right) / 2.0, (top_field.top + top_field.bottom) / 2.0)
            candidates = []
            for c in components:
                if final_group_for[c] is not None:
                    continue
                loc = getattr(c, "location", None)
                if loc is None:
                    dist2 = float('inf')
                else:
                    dx = loc.x - center_top[0]
                    dy = loc.y - center_top[1]
                    dist2 = dx*dx + dy*dy
                candidates.append((dist2, c))
            candidates.sort(key=lambda t: t[0])
            for _, drone in candidates[:needed_top]:
                final_group_for[drone] = f"protecting {top_field.id}"

        # Step 2: Distribute remaining drones to other fields
        # Recompute current protections for all fields
        needs = {}
        for f in fields:
            current = sum(1 for c in components if getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == f.id)
            needs[f.id] = max(0, int(getattr(f, "drones_for_full_protection", 0) - current))

        # Adjust needs for the top field if we already allocated to it
        cur_top_final = sum(1 for c in components if final_group_for.get(c) == f"protecting {top_field.id}")
        if cur_top_final < top_field.drones_for_full_protection:
            needs[top_field.id] = max(0, int(top_field.drones_for_full_protection - cur_top_final))

        other_fields = [f for f in fields if f.id != top_field.id]

        # Drones not currently allocated to the top field
        free_drones = [c for c in components if final_group_for.get(c) != f"protecting {top_field.id}"]

        # If there are other fields and free drones, allocate based on a max-score heuristic
        # Precompute centers for fields
        centers = {f.id: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for f in other_fields}

        while free_drones and any(needs[f.id] > 0 for f in other_fields):
            best_pair = None
            best_score = -1.0
            # Evaluate best field for each drone, pick the overall best
            for drone in free_drones:
                loc = getattr(drone, "location", None)
                # Compute distance to centers for each field
                dist2_to_field = {}
                for f in other_fields:
                    center = centers[p := f.id]
                    if loc is None:
                        d2 = float('inf')
                    else:
                        dx = loc.x - center[0]
                        dy = loc.y - center[1]
                        d2 = dx*dx + dy*dy
                    dist2_to_field[f.id] = d2
                # Choose best field for this drone by threat/ distance
                if other_fields:
                    best_f = max(other_fields, key=lambda ff: (getattr(ff, "threat_level", 0) / (1.0 + dist2_to_field[ff.id])))
                    d2 = dist2_to_field[best_f.id]
                    score = (getattr(best_f, "threat_level", 0) / (1.0 + d2))
                    if score > best_score:
                        best_score = score
                        best_pair = (drone, best_f, d2)
            if best_pair is None:
                break
            drone, field, d2 = best_pair
            if needs[field.id] > 0:
                final_group_for[drone] = f"protecting {field.id}"
                needs[field.id] -= 1
                free_drones.remove(drone)
            else:
                # Field no longer needs drones; remove from consideration
                other_fields = [f for f in other_fields if f.id != field.id]

        # Step 3: Assign final groups to all drones
        for c in components:
            grp = final_group_for.get(c)
            if grp is None:
                grp = "idle"
            environment.assign_group(c, grp)