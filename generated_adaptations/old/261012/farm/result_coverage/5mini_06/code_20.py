from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (getattr(field, "left", 0.0) + getattr(field, "right", 0.0)) / 2.0
        cy = (getattr(field, "top", 0.0) + getattr(field, "bottom", 0.0)) / 2.0
        return cx, cy

    def _dist(self, x1, y1, x2, y2):
        return math.hypot(x1 - x2, y1 - y2)

    def assign_drones(self, components, environment, group_ids, step: int):
        idle_group = "idle"

        # Build component info indexed by idx
        comps = []
        for idx, comp in enumerate(components):
            comps.append({
                "idx": idx,
                "comp": comp,
                "x": getattr(comp.location, "x", 0.0),
                "y": getattr(comp.location, "y", 0.0),
                "state": getattr(comp, "state", None),
                "target_id": getattr(comp, "target_id", None)
            })
        idx_to_info = {c["idx"]: c for c in comps}
        all_idxs = [c["idx"] for c in comps]

        # Threatened fields
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not fields:
            # nothing to protect
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Primary field: highest threat (tie-break by id)
        fields.sort(key=lambda f: (f.threat_level, f.id), reverse=True)
        primary = fields[0]
        primary_group = f"protecting {primary.id}"
        required_primary = max(0, int(getattr(primary, "drones_for_full_protection", 0)))

        # Helper: rank candidate drones for a field (prefer protecting/moving to that field, then by distance)
        def rank_candidates(field, candidate_idxs):
            cx, cy = self._field_center(field)
            ranked = []
            for i in candidate_idxs:
                info = idx_to_info[i]
                dist = self._dist(info["x"], info["y"], cx, cy)
                if info["state"] == "protecting" and info["target_id"] == field.id:
                    pr = 0
                elif info["state"] == "moving_to_field" and info["target_id"] == field.id:
                    pr = 1
                else:
                    pr = 2
                ranked.append((pr, dist, i))
            ranked.sort(key=lambda t: (t[0], t[1], t[2]))
            return [t[2] for t in ranked]

        # Gather current protectors and movers per field
        protectors = {f.id: [i for i in all_idxs if idx_to_info[i]["state"] == "protecting" and idx_to_info[i]["target_id"] == f.id] for f in fields}
        movers = {f.id: [i for i in all_idxs if idx_to_info[i]["state"] == "moving_to_field" and idx_to_info[i]["target_id"] == f.id] for f in fields}

        assignments = {}

        # --- Primary allocation: choose required_primary closest drones (prefer protectors/movers) ---
        # Compose ranking for all drones
        primary_ranked = rank_candidates(primary, all_idxs)
        chosen_primary = primary_ranked[:min(required_primary, len(primary_ranked))]
        for idx in chosen_primary:
            assignments[idx] = primary_group if primary_group in group_ids else idle_group

        assigned_idxs = set(chosen_primary)
        remaining_idxs = [i for i in all_idxs if i not in assigned_idxs]

        # --- Preserve useful ongoing protections for other fields ---
        # Keep full protections and near-complete protections (>= half of required) to avoid oscillation
        kept_fields = []
        for f in fields:
            if f.id == primary.id:
                continue
            req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
            if req == 0:
                continue
            cur_prot = [i for i in protectors.get(f.id, []) if i in remaining_idxs]
            cur_moves = [i for i in movers.get(f.id, []) if i in remaining_idxs]
            total_current = len(cur_prot) + len(cur_moves)
            # Keep if already fully protected or close to full
            if total_current >= req:
                # keep enough protectors/movers (prefer protectors first)
                keep_idxs = cur_prot + [i for i in cur_moves if i not in cur_prot]
                # assign at most req (but keep all protectors if > req)
                to_assign = keep_idxs[:req] if len(cur_prot) + len(cur_moves) >= req else keep_idxs
                for i in to_assign:
                    assignments[i] = f"protecting {f.id}" if f"protecting {f.id}" in group_ids else idle_group
                    if i in remaining_idxs:
                        remaining_idxs.remove(i)
                kept_fields.append(f.id)
            else:
                # near-complete threshold: keep if protectors alone >= ceil(req/2)
                if len(cur_prot) >= -(-req // 2):  # ceil(req/2)
                    for i in cur_prot:
                        assignments[i] = f"protecting {f.id}" if f"protecting {f.id}" in group_ids else idle_group
                        if i in remaining_idxs:
                            remaining_idxs.remove(i)
                    kept_fields.append(f.id)

        # --- Attempt to fully protect additional fields greedily ---
        # Evaluate candidate fields (excluding primary and already kept)
        candidate_fields = [f for f in fields if f.id != primary.id and f.id not in kept_fields]
        # While we have remaining drones try to complete fields with best score
        while candidate_fields and remaining_idxs:
            best = None
            # Score = threat / extra_needed * (1 / (1 + avg_dist)) to prefer closer fields
            for f in candidate_fields:
                req = max(0, int(getattr(f, "drones_for_full_protection", 0)))
                if req == 0:
                    continue
                cur_prot = [i for i in protectors.get(f.id, []) if i in remaining_idxs]
                cur_moves = [i for i in movers.get(f.id, []) if i in remaining_idxs]
                have = len(cur_prot) + len(cur_moves)
                extra_needed = max(0, req - have)
                if extra_needed == 0:
                    # can keep them without consuming drones
                    score = float("inf")
                    chosen_extra = []
                else:
                    if extra_needed > len(remaining_idxs):
                        continue
                    # choose best extra_needed drones by distance
                    ranked = rank_candidates(f, remaining_idxs)
                    chosen_extra = ranked[:extra_needed]
                    # compute avg distance of chosen extras
                    cx, cy = self._field_center(f)
                    dists = [self._dist(idx_to_info[i]["x"], idx_to_info[i]["y"], cx, cy) for i in chosen_extra] or [1.0]
                    avg_dist = sum(dists) / len(dists)
                    threat = getattr(f, "threat_level", 0.0)
                    score = (threat + 1e-9) / extra_needed * (1.0 / (1.0 + avg_dist))
                # deterministic tie-break by id
                if best is None or (score, f.id) > (best[0], best[1].id):
                    best = (score, f, extra_needed, chosen_extra, cur_prot, cur_moves)
            if best is None:
                break
            score, field_sel, extra_needed, chosen_extra, cur_prot, cur_moves = best
            # If score is finite but extra_needed > remaining count, skip
            if extra_needed > len(remaining_idxs):
                candidate_fields = [f for f in candidate_fields if f.id != field_sel.id]
                continue
            # Assign protectors/movers if present
            keep_list = [i for i in cur_prot] + [i for i in cur_moves if i not in cur_prot]
            for i in keep_list:
                if i in remaining_idxs:
                    assignments[i] = f"protecting {field_sel.id}" if f"protecting {field_sel.id}" in group_ids else idle_group
                    remaining_idxs.remove(i)
            # Assign chosen extras
            for i in chosen_extra:
                if i in remaining_idxs:
                    assignments[i] = f"protecting {field_sel.id}" if f"protecting {field_sel.id}" in group_ids else idle_group
                    remaining_idxs.remove(i)
            # remove considered field
            candidate_fields = [f for f in candidate_fields if f.id != field_sel.id]

        # --- Final assignments for remaining drones ---
        # Let drones that are already moving_to_field continue to their target (assign to that protecting group)
        for i in list(remaining_idxs):
            info = idx_to_info[i]
            if info["state"] == "moving_to_field" and info["target_id"] is not None:
                grp = f"protecting {info['target_id']}"
                if grp in group_ids:
                    assignments[i] = grp
                    remaining_idxs.remove(i)
                    continue
            # otherwise idle
            assignments[i] = idle_group
            remaining_idxs.remove(i)

        # Ensure everyone is assigned explicitly
        for idx in all_idxs:
            if idx not in assignments:
                assignments[idx] = idle_group

        # Apply assignments
        for idx, grp in assignments.items():
            comp = idx_to_info[idx]["comp"]
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(comp, grp)