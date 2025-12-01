from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (getattr(field, "left", 0.0) + getattr(field, "right", 0.0)) / 2.0
        cy = (getattr(field, "top", 0.0) + getattr(field, "bottom", 0.0)) / 2.0
        return cx, cy

    def _distance(self, x1, y1, x2, y2):
        return math.hypot(x1 - x2, y1 - y2)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat (these are the only ones with protecting groups)
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        idle_group = "idle"
        if not fields:
            # No threatened fields -> all drones idle
            for comp in components:
                environment.assign_group(comp, idle_group)
            return

        # Choose the highest-threat field (tie-break deterministically by id)
        fields.sort(key=lambda f: (f.threat_level, f.id), reverse=True)
        primary = fields[0]
        primary_group = f"protecting {primary.id}"

        # Prepare per-component info and index mapping
        comps_info = []
        for idx, comp in enumerate(components):
            lx = getattr(comp.location, "x", 0.0)
            ly = getattr(comp.location, "y", 0.0)
            comp_state = getattr(comp, "state", None)
            comp_target = getattr(comp, "target_id", None)
            cx_p, cy_p = self._field_center(primary)
            dist_to_primary = self._distance(lx, ly, cx_p, cy_p)
            comps_info.append({
                "idx": idx,
                "comp": comp,
                "x": lx, "y": ly,
                "state": comp_state,
                "target_id": comp_target,
                "dist_to_primary": dist_to_primary
            })

        total_drones = len(components)
        required_primary = int(getattr(primary, "drones_for_full_protection", 0))
        required_primary = max(0, required_primary)

        # Rank drones for primary assignment: protecting primary, moving to primary, then closest
        def primary_priority(info):
            if info["state"] == "protecting" and info["target_id"] == primary.id:
                return (0, info["dist_to_primary"])
            if info["state"] == "moving_to_field" and info["target_id"] == primary.id:
                return (1, info["dist_to_primary"])
            return (2, info["dist_to_primary"])

        comps_info_sorted = sorted(comps_info, key=primary_priority)
        # Select up to required_primary drones for primary
        selected_primary_idxs = [info["idx"] for info in comps_info_sorted[:min(required_primary, total_drones)]]

        # Keep track of assignments by index (will fill for all)
        assignments = dict()  # idx -> group_name

        # Assign selected primary drones
        for idx in selected_primary_idxs:
            if primary_group in group_ids:
                assignments[idx] = primary_group
            else:
                assignments[idx] = idle_group  # fallback

        # Remaining drone indices
        remaining_idxs = [info["idx"] for info in comps_info if info["idx"] not in selected_primary_idxs]

        # Now try to fully protect additional fields in descending threat order
        other_fields = [f for f in fields if f.id != primary.id]
        other_fields.sort(key=lambda f: (f.threat_level, f.id), reverse=True)

        # Build quick lookup for components by index
        idx_to_info = {info["idx"]: info for info in comps_info}

        for field in other_fields:
            if not remaining_idxs:
                break
            req = int(getattr(field, "drones_for_full_protection", 0))
            req = max(0, req)
            if req == 0:
                continue
            # Current protectors among remaining (already protecting this field)
            current_protectors = [i for i in remaining_idxs
                                  if idx_to_info[i]["state"] == "protecting" and idx_to_info[i]["target_id"] == field.id]
            have = len(current_protectors)
            need = req - have
            if need <= 0:
                # Already fully protected by existing protectors; keep them assigned
                grp = f"protecting {field.id}"
                for i in list(current_protectors):
                    assignments[i] = grp if grp in group_ids else idle_group
                    if i in remaining_idxs:
                        remaining_idxs.remove(i)
                continue

            # If enough remaining drones to reach full protection, pick the best ones
            if len(remaining_idxs) >= need:
                cx, cy = self._field_center(field)
                cand_infos = []
                for i in remaining_idxs:
                    info = idx_to_info[i]
                    # priority for selection: moving_to_field to that field first, then distance
                    if info["state"] == "moving_to_field" and info["target_id"] == field.id:
                        sel_prio = 0
                    elif info["state"] == "protecting" and info["target_id"] == field.id:
                        sel_prio = 0
                    else:
                        sel_prio = 1
                    dist = self._distance(info["x"], info["y"], cx, cy)
                    cand_infos.append((sel_prio, dist, i))
                cand_infos.sort(key=lambda t: (t[0], t[1]))
                selected_for_field = [t[2] for t in cand_infos[:need]]
                grp = f"protecting {field.id}"
                # assign current protectors + newly selected
                for i in list(current_protectors):
                    assignments[i] = grp if grp in group_ids else idle_group
                    if i in remaining_idxs:
                        remaining_idxs.remove(i)
                for i in selected_for_field:
                    assignments[i] = grp if grp in group_ids else idle_group
                    if i in remaining_idxs:
                        remaining_idxs.remove(i)
                # continue to next field
            else:
                # Not enough drones to fully protect this field now; skip full protection
                continue

        # After attempts to fully protect additional fields, assign remaining drones to best partial targets
        if remaining_idxs:
            partial_fields = [f for f in fields]  # includes primary and others
            # For each remaining drone, assign to the best field according to score = distance / (1 + threat)
            for i in list(remaining_idxs):
                info = idx_to_info[i]
                best_field = None
                best_score = float("inf")
                for f in partial_fields:
                    grp = f"protecting {f.id}"
                    if grp not in group_ids:
                        continue
                    cx, cy = self._field_center(f)
                    d = self._distance(info["x"], info["y"], cx, cy)
                    threat = getattr(f, "threat_level", 0.0)
                    score = d / (1.0 + threat)  # lower is better: closer and/or higher threat preferred
                    if score < best_score:
                        best_score = score
                        best_field = f
                if best_field is not None:
                    grp = f"protecting {best_field.id}"
                    assignments[i] = grp if grp in group_ids else idle_group
                else:
                    assignments[i] = idle_group
                remaining_idxs.remove(i)

        # Ensure every component has an assignment; fallback to idle if something missed
        for idx in range(len(components)):
            if idx not in assignments:
                assignments[idx] = idle_group

        # Finally, apply assignments by calling environment.assign_group on each component
        for idx, grp in assignments.items():
            comp = idx_to_info[idx]["comp"]
            if grp not in group_ids:
                grp = idle_group
            environment.assign_group(comp, grp)