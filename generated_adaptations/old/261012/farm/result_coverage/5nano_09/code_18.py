from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Identify fields with positive threat
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # 2) Sort fields by a priority: threat * drones_for_full_protection (higher is more valuable)
        fields_sorted = sorted(
            fields,
            key=lambda f: getattr(f, "threat_level", 0) * max(1, int(getattr(f, "drones_for_full_protection", 0))),
            reverse=True,
        )
        field_by_id = {f.id: f for f in fields_sorted}

        # 3) Current protection counts per field
        current_counts = {f.id: 0 for f in fields_sorted}
        protect_by_field = {f.id: [] for f in fields_sorted}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in current_counts:
                    protect_by_field[tid].append(d)
                    current_counts[tid] += 1

        assigned = set()

        # Helpers
        def center_of(f):
            cx = (getattr(f, "left", 0.0) + getattr(f, "right", 0.0)) / 2.0
            cy = (getattr(f, "top", 0.0) + getattr(f, "bottom", 0.0)) / 2.0
            return cx, cy

        def dist_sq_to_field(drone, f):
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            cx, cy = center_of(f)
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return dx * dx + dy * dy

        # Stage A: determine the maximum set of fields we can fully protect
        total_drones = len(components)
        full_set = []
        needed_so_far = 0
        for f in fields_sorted:
            fid = f.id
            current = current_counts.get(fid, 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, required - current)
            if need <= 0:
                continue
            if needed_so_far + need <= total_drones:
                full_set.append(f)
                needed_so_far += need
            else:
                break

        # Stage A: allocate to full_set fields
        for f in full_set:
            fid = f.id
            pid = f"protecting {fid}"
            if pid not in group_ids:
                continue

            current = current_counts.get(fid, 0)
            required = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, required - current)
            if need <= 0:
                # Ensure current protectors for this field are in the correct group
                for d in components:
                    if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid:
                        environment.assign_group(d, pid)
                        assigned.add(d)
                continue

            # Use idle first
            idle_candidates = [d for d in components if getattr(d, "state", None) == "idle" and d not in assigned]
            take_idle = min(need, len(idle_candidates))
            for i in range(take_idle):
                d = idle_candidates[i]
                environment.assign_group(d, pid)
                assigned.add(d)
                need -= 1
                current_counts[fid] = current_counts.get(fid, 0) + 1
            if need <= 0:
                continue

            # Safe steals: from donors not in full_set and with at least 2 protectors
            donors = []
            for d in components:
                if d in assigned:
                    continue
                st = getattr(d, "state", None)
                if st != "protecting":
                    continue
                donor_fid = getattr(d, "target_id", None)
                donor_field = field_by_id.get(donor_fid)
                if donor_field is None:
                    continue
                if donor_field.id in [ff.id for ff in full_set]:
                    continue
                donor_cur = current_counts.get(donor_fid, 0)
                donor_required = int(getattr(donor_field, "drones_for_full_protection", 0))
                if donor_cur > 1 and donor_cur < donor_required:
                    # avoid stealing from strictly more dangerous donors
                    if getattr(donor_field, "threat_level", 0) <= getattr(f, "threat_level", 0):
                        donors.append((d, donor_field))

            # Sort donors by distance to target field to minimize travel
            donors.sort(key=lambda pair: dist_sq_to_field(pair[0], f))
            for d, donor_field in donors[:need]:
                environment.assign_group(d, pid)
                assigned.add(d)
                current_counts[fid] = current_counts.get(fid, 0) + 1
                donor_id = donor_field.id
                current_counts[donor_id] = max(0, current_counts.get(donor_id, 0) - 1)

        # Stage B: ensure fully protected fields have their protectors in the correct group
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_by_id:
                    pid = f"protecting {tid}"
                    if pid in group_ids:
                        environment.assign_group(d, pid)
                        assigned.add(d)

        # Stage C: partial protection with remaining drones
        # Build list of needs for fields not yet fully protected (in order of threat)
        needs = []
        for f in fields_sorted:
            fid = f.id
            pid = f"protecting {fid}"
            if pid not in group_ids:
                continue
            need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - current_counts.get(fid, 0))
            if need > 0:
                needs.append((f, need))

        # Available drones not yet assigned
        available = [d for d in components if d not in assigned]

        # Distribute partially by descending threat, one drone at a time to the closest available
        needs.sort(key=lambda t: getattr(t[0], "threat_level", 0), reverse=True)
        for f, need in needs:
            if need <= 0:
                continue
            while need > 0 and available:
                best_idx = None
                best_dist = float("inf")
                for idx, d in enumerate(available):
                    dist = dist_sq_to_field(d, f)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx
                if best_idx is None:
                    break
                drone = available.pop(best_idx)
                environment.assign_group(drone, f"protecting {f.id}")
                assigned.add(drone)
                need -= 1
                current_counts[f.id] = current_counts.get(f.id, 0) + 1

        # Stage D: any remaining drones go idle
        for d in components:
            if d not in assigned:
                environment.assign_group(d, "idle")