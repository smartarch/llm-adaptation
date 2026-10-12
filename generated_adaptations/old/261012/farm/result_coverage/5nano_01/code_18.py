from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # 1) Collect fields with positive threat and positive full-protection requirement
        threat_fields = [
            f for f in environment.fields
            if getattr(f, "threat_level", 0) > 0 and getattr(f, "drones_for_full_protection", 0) > 0
        ]

        # If no threat, idle all drones
        if not threat_fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Helpers
        def center_of(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        # 2) Build current protectors by field
        protectors_by_field = {}
        for idx, d in enumerate(components):
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    protectors_by_field.setdefault(tid, []).append(idx)

        # 3) Build field infos: remaining need and an efficiency metric
        field_infos = []
        for f in threat_fields:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            current = len(protectors_by_field.get(f.id, []))
            remaining = max(0, needed - current)
            eff = f.threat_level / max(1, remaining) if remaining > 0 else float("inf")
            field_infos.append((eff, f, remaining, current))

        field_infos.sort(key=lambda t: t[0], reverse=True)

        total_drones = len(components)
        allocated = set()
        assigned = {}

        # 4) Phase 1: Fully protect as many top fields as possible
        selected_fields = []
        remaining_capacity = total_drones
        for eff, f, remaining, current in field_infos:
            if remaining <= 0:
                # Field already fully protected; mark existing protectors
                for idx in protectors_by_field.get(f.id, []):
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)
                continue
            if remaining_capacity >= remaining:
                selected_fields.append(f)
                remaining_capacity -= remaining

        # Fallback: if nothing selected, protect the top-threat field
        if not selected_fields and threat_fields:
            selected_fields = [threat_fields[0]]

        # Phase 1 allocation: reuse current protectors, then fill with closest drones
        def dist_to_center_from_field(field, idx):
            d = components[idx]
            loc = getattr(d, "location", None)
            cx, cy = center_of(field)
            if loc is None:
                return float("inf")
            dx = loc.x - cx
            dy = loc.y - cy
            return (dx * dx + dy * dy) ** 0.5

        selected_ids = set([ff.id for ff in selected_fields])

        for f in sorted(selected_fields, key=lambda ff: getattr(ff, "threat_level", 0), reverse=True):
            center = center_of(f)
            cx, cy = center
            needed = int(getattr(f, "drones_for_full_protection", 0))

            current_ids = protectors_by_field.get(f.id, [])
            current_ids = [i for i in current_ids if i not in allocated]

            # Keep closest current protectors
            current_sorted = sorted(current_ids, key=lambda i: dist_to_center_from_field(f, i))
            keep = current_sorted[:min(len(current_sorted), max(0, needed))]
            for idx in keep:
                assigned[idx] = f"protecting {f.id}"
                allocated.add(idx)

            remaining = max(0, needed - len(keep))
            if remaining > 0:
                # Fill with closest unallocated drones (allowed to come from anywhere)
                candidates = []
                for idx, d in enumerate(components):
                    if idx in allocated:
                        continue
                    loc = getattr(d, "location", None)
                    dist = float("inf")
                    if loc is not None:
                        dx = loc.x - cx
                        dy = loc.y - cy
                        dist = (dx * dx + dy * dy) ** 0.5
                    candidates.append((dist, idx))
                candidates.sort()
                for i in range(min(remaining, len(candidates))):
                    idx = candidates[i][1]
                    assigned[idx] = f"protecting {f.id}"
                    allocated.add(idx)

        # 5) Phase 2: Partial protection with remaining drones
        # Compute remaining_to_protect after Phase 1
        remaining_to_protect = {}
        for f in threat_fields:
            needed = int(getattr(f, "drones_for_full_protection", 0))
            current_count = sum(1 for idx, gid in assigned.items() if gid == f"protecting {f.id}")
            remaining_to_protect[f.id] = max(0, needed - current_count)

        # Build list of available drones for Phase 2 (all not yet allocated)
        available = [idx for idx in range(len(components)) if idx not in allocated]

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
                    dx = loc.x - cx
                    dy = loc.y - cy
                    dist = (dx*dx + dy*dy) ** 0.5
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

        # 6) Final: apply groups
        for idx, d in enumerate(components):
            if idx in assigned:
                environment.assign_group(d, assigned[idx])
            else:
                environment.assign_group(d, "idle")