from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields with positive threat and positive full-protection requirement
        threat_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0 and getattr(f, "drones_for_full_protection", 0) > 0
        ]

        # If no threat, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helper: field center
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # Build current protectors by field
        protectors_by_field = {}
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    protectors_by_field.setdefault(tid, []).append(idx)

        total_drones = len(components)
        allocated = set()
        assigned = {}

        # Compute efficiency and current needs for each field
        field_infos = []
        for f in threat_fields:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            current_ids = protectors_by_field.get(f.id, [])
            current_count = len(current_ids)
            need = max(0, needed - current_count)
            eff = f.threat_level / max(1, need) if need > 0 else float("inf")
            field_infos.append((eff, f, need, current_ids))

        # Sort by efficiency (high to low)
        field_infos.sort(key=lambda t: t[0], reverse=True)

        # Phase 1: fully protect selected fields greedily
        for eff, f, need, current_ids in field_infos:
            center_x, center_y = center_of(f)
            if need <= 0:
                # Field already fully protected; ensure its protectors are accounted
                for idx in current_ids:
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)
                continue

            # Keep the closest current protectors (up to needed)
            current_sorted = sorted(
                current_ids,
                key=lambda idx: (
                    (getattr(components[idx], "location", None) and
                     ((components[idx].location.x - center_x) ** 2 +
                      (components[idx].location.y - center_y) ** 2) ** 0.5) or float("inf")
                )
            )
            keep_n = min(len(current_sorted), need)
            keep = current_sorted[:keep_n]
            for idx in keep:
                assigned[idx] = f"protecting {f.id}"
                allocated.add(idx)

            remaining = max(0, need - keep_n)
            if remaining > 0:
                # Fill with closest unallocated drones
                candidates = []
                for idx, d in enumerate(components):
                    if idx in allocated:
                        continue
                    loc = getattr(d, "location", None)
                    dist = float("inf")
                    if loc is not None:
                        dist = ((loc.x - center_x) ** 2 + (loc.y - center_y) ** 2) ** 0.5
                    candidates.append((dist, idx))
                candidates.sort()
                for i in range(min(remaining, len(candidates))):
                    idx = candidates[i][1]
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)

        # Phase 2: Partial protection with remaining drones
        # Compute remaining needs after Phase 1
        remaining_to_protect = {}
        for f in threat_fields:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            current_count = len([idx for idx, gid in assigned.items() if gid == f"protecting {f.id}"])
            remaining_to_protect[f.id] = max(0, needed - current_count)

        # Build available drones for Phase 2:
        # Do not move drones currently protecting fields not in the selected set
        # We only consider drones that are not currently protecting
        available = [idx for idx, d in enumerate(components) if getattr(d, "state", "") != "protecting"]

        # Fields needing partial protection, sorted by threat
        fields_needing = [f for f in threat_fields if remaining_to_protect.get(f.id, 0) > 0]
        fields_needing.sort(key=lambda ff: ff.threat_level, reverse=True)

        for f in fields_needing:
            need = remaining_to_protect.get(f.id, 0)
            if need <= 0:
                continue
            cx, cy = center_of(f)
            dist_list = []
            for idx in available:
                d = components[idx]
                loc = getattr(d, "location", None)
                dist = float("inf")
                if loc is not None:
                    dist = ((loc.x - cx) ** 2 + (loc.y - cy) ** 2) ** 0.5
                dist_list.append((dist, idx))
            dist_list.sort()
            taken = 0
            for dist, idx in dist_list:
                if taken >= need:
                    break
                assigned[idx] = f"protecting {f.id}"
                allocated.add(idx)
                available.remove(idx)
                taken += 1
            remaining_to_protect[f.id] = max(0, remaining_to_protect.get(f.id, 0) - taken)

        # Final: assign groups
        for idx, d in enumerate(components):
            if idx in assigned:
                environment.assign_group(d, assigned[idx])
            else:
                environment.assign_group(d, "idle")