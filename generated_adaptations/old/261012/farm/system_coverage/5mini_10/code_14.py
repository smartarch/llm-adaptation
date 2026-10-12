from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        1. Find the field with highest threat_level (>0) — that's the mandatory target.
        2. Lock drones protecting fields that are initially fully protected (they cannot be reassigned).
        3. Treat drones that are protecting or moving_to_field (with target == target field) as committed to the target.
           Select nearest additional drones (excluding locked ones) to reach full protection for the target.
        4. With remaining available drones, iterate other threatened fields in descending threat order and
           try to fully protect each (selecting nearest drones). If not enough drones remain to fully protect the next
           field, assign the remaining ones to it (partial protection).
        5. Assign locked drones to remain on their fields, assigned drones to their protecting groups, and all others idle.
        """
        # Helpers
        def dist2_to_rect(x, y, field):
            dx = 0.0
            if x < field.left:
                dx = field.left - x
            elif x > field.right:
                dx = x - field.right
            dy = 0.0
            if y < field.top:
                dy = field.top - y
            elif y > field.bottom:
                dy = y - field.bottom
            return dx * dx + dy * dy

        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Collect threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # Nothing to protect
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Choose top-threat field (tie-break by id for determinism)
        target_field = max(threatened_fields, key=lambda f: (f.threat_level, f.id))
        target_id = target_field.id
        target_group = f"protecting {target_id}"
        if target_group not in group_ids:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Build protecting counts and lists (state == "protecting")
        protecting_counts = {f.id: 0 for f in threatened_fields}
        protecting_drones = {f.id: [] for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in protecting_counts:
                    protecting_counts[tid] += 1
                    protecting_drones[tid].append(d)

        # Identify initially fully protected fields and lock their protecting drones
        fully_protected_initial = set()
        for f in threatened_fields:
            cnt = protecting_counts.get(f.id, 0)
            if cnt >= int(f.drones_for_full_protection):
                fully_protected_initial.add(f.id)

        locked_ids = set()
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                locked_ids.add(id(d))

        # Determine drones committed to the target: protecting or moving_to_field with target == target_id
        committed_to_target = []
        for d in components:
            st = getattr(d, "state", None)
            tid = getattr(d, "target_id", None)
            if tid == target_id and (st == "protecting" or st == "moving_to_field"):
                committed_to_target.append(d)
        committed_ids = {id(d) for d in committed_to_target}
        already_committed_count = len(committed_to_target)

        required_total = int(target_field.drones_for_full_protection)
        # If already enough committed, we'll keep them; else select nearest additional drones (excluding locked)
        final_assigned = {}  # drone_id -> field_id

        # Keep locked drones assigned to their fields
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                final_assigned[id(d)] = fid

        # Mark committed to target as assigned to target
        for d in committed_to_target:
            final_assigned[id(d)] = target_id

        # If not enough committed, select nearest additional drones (exclude locked and already committed)
        if already_committed_count < required_total:
            need = required_total - already_committed_count
            candidates = [d for d in components if id(d) not in locked_ids and id(d) not in committed_ids]
            # Sort by (distance to target rect, prefer moving/protecting to target, id)
            def cand_key_target(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float("inf")
                else:
                    dist2 = dist2_to_rect(getattr(loc, "x", 0), getattr(loc, "y", 0), target_field)
                st = getattr(d, "state", None)
                tid = getattr(d, "target_id", None)
                moving_pref = 0 if (st == "moving_to_field" and tid == target_id) else 1
                protecting_pref = 0 if (st == "protecting" and tid == target_id) else 1
                return (dist2, moving_pref, protecting_pref, id(d))
            candidates.sort(key=cand_key_target)
            to_take = candidates[:need]
            for d in to_take:
                final_assigned[id(d)] = target_id

        # Build available_drones pool for additional allocations: those not locked and not already assigned
        available_drones = [d for d in components if id(d) not in locked_ids and id(d) not in final_assigned]

        # Allocate remaining drones to other fields in descending threat order (excluding target)
        other_fields = sorted([f for f in threatened_fields if f.id != target_id],
                              key=lambda f: (-f.threat_level, f.id))
        for field in other_fields:
            if not available_drones:
                break
            grp_name = f"protecting {field.id}"
            if grp_name not in group_ids:
                continue
            required = int(field.drones_for_full_protection)
            # We will attempt to allocate up to 'required' drones to this field (full protection if possible).
            # Selection key: primarily distance to field rect, then prefer moving_to_field/protecting to this field, then id.
            def cand_key_field(d):
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float("inf")
                else:
                    dist2 = dist2_to_rect(getattr(loc, "x", 0), getattr(loc, "y", 0), field)
                st = getattr(d, "state", None)
                tid = getattr(d, "target_id", None)
                moving_pref = 0 if (st == "moving_to_field" and tid == field.id) else 1
                protecting_pref = 0 if (st == "protecting" and tid == field.id) else 1
                return (dist2, moving_pref, protecting_pref, id(d))
            available_drones.sort(key=cand_key_field)
            # Select up to required
            take_count = min(required, len(available_drones))
            # If not enough to fully protect but this is the highest remaining threat, we still assign what we have (partial).
            selected = available_drones[:take_count]
            for d in selected:
                final_assigned[id(d)] = field.id
            # Remove selected from available_drones
            sel_ids = {id(d) for d in selected}
            available_drones = [d for d in available_drones if id(d) not in sel_ids]

        # Any remaining available_drones just go idle (we could also assign them to highest threat field partially,
        # but the loop above already would have assigned them to the highest-threat remaining field).
        # Now perform final assignments using environment.assign_group
        for d in components:
            did = id(d)
            if did in final_assigned:
                fid = final_assigned[did]
                group = f"protecting {fid}"
                # Safety: if group missing, fall back to idle
                if group in group_ids:
                    environment.assign_group(d, group)
                else:
                    environment.assign_group(d, idle_group)
            else:
                # not assigned -> idle
                environment.assign_group(d, idle_group)