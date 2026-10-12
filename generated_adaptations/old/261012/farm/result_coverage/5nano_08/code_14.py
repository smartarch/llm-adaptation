from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify threatened fields that can be fully protected
        threatened = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0 and int(getattr(f, "drones_for_full_protection", 0)) > 0
        ]
        
        def assign_group_safe(drone, group_name):
            if group_name in group_ids:
                environment.assign_group(drone, group_name)
            else:
                environment.assign_group(drone, "idle")
        
        # If no threatened fields, idle all drones
        if not threatened:
            for d in components:
                assign_group_safe(d, "idle")
            return
        
        # Build a quick lookup for fields by id
        field_by_id = {f.id: f for f in threatened}
        
        # Current protection counts per field
        current_counts = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                fid = getattr(d, "target_id", None)
                if fid in field_by_id:
                    current_counts[fid] = current_counts.get(fid, 0) + 1
        
        # Precompute centers and max distances for scoring
        centers = {fid: ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0) for fid, f in field_by_id.items()}
        max_distances = {}
        for fid, f in field_by_id.items():
            cx, cy = centers[fid]
            maxd = 0.0
            any_drone = False
            for d in components:
                loc = getattr(d, "location", None)
                if loc is None:
                    continue
                dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
                if not any_drone or dist > maxd:
                    maxd = dist
                    any_drone = True
            max_distances[fid] = maxd if maxd > 0 else 1.0  # avoid division by zero
        
        # Remaining drones needed per field to reach full protection
        remaining = {}
        for fid, f in field_by_id.items():
            need = int(getattr(f, "drones_for_full_protection", 0)) - current_counts.get(fid, 0)
            remaining[fid] = max(0, need)
        
        assigned_ids = set()  # track drones we assign in this step
        distance_penalty = 0.8  # weight for travel cost in scoring
        
        # Compute best (drone, field) choice for each drone
        best_for_drone = {}  # drone -> (fid, score)
        for d in components:
            did = id(d)
            loc = getattr(d, "location", None)
            if loc is None:
                continue
            best_fid = None
            best_score = float("-inf")
            
            # Staying on current field if it still needs protection
            if getattr(d, "state", None) == "protecting":
                cur_fid = getattr(d, "target_id", None)
                if cur_fid in remaining and remaining[cur_fid] > 0:
                    f = field_by_id.get(cur_fid)
                    threat = getattr(f, "threat_level", 0)
                    rem = max(1, remaining[cur_fid])
                    score = threat / rem  # no travel cost for staying
                    if score > best_score:
                        best_score = score
                        best_fid = cur_fid
            
            # Consider moving to any field that still needs protection
            for fid, f in field_by_id.items():
                if remaining.get(fid, 0) <= 0:
                    continue
                cx, cy = centers[fid]
                dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
                dist_norm = dist / max_distances[fid]
                score = (getattr(f, "threat_level", 0) / max(1, remaining[fid])) - dist_norm * distance_penalty
                if score > best_score:
                    best_score = score
                    best_fid = fid
            
            if best_fid is not None and best_score > 0:
                best_for_drone[d] = (best_fid, best_score)
        
        # Group candidates by field and keep the top remaining[fid] drones per field
        per_field_candidates = {fid: [] for fid in field_by_id}
        for d, (fid, score) in best_for_drone.items():
            per_field_candidates[fid].append((score, d))
        
        for fid, lst in per_field_candidates.items():
            lst.sort(key=lambda x: x[0], reverse=True)
            limit = remaining.get(fid, 0)
            for i in range(min(limit, len(lst))):
                _, drone = lst[i]
                environment.assign_group(drone, f"protecting {fid}")
                assigned_ids.add(id(drone))
                remaining[fid] = max(0, remaining[fid] - 1)
        
        # Any drones not assigned go idle (explicit re-assignment)
        for d in components:
            if id(d) in assigned_ids:
                continue
            assign_group_safe(d, "idle")