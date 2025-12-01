from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Always fully protect the single field with the highest threat_level using the closest drones.
        Keep drones that are protecting fields that are initially fully protected (locked).
        Prefer drones already protecting or moving to the target when selecting drones.
        """
        # Helper: squared distance from point (x,y) to rectangle field (0 if inside)
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

        # Determine idle group fallback
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Collect fields with threat_level > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threatened fields, assign all drones to idle
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Choose the target field: highest threat_level, tie-break by id (smallest lexicographic)
        sorted_fields = sorted(threatened_fields, key=lambda f: (-f.threat_level, f.id))
        target_field = sorted_fields[0]
        target_id = target_field.id
        target_group = f"protecting {target_id}"

        # If the protecting group for target isn't available, fallback to idle all
        if target_group not in group_ids:
            for d in components:
                environment.assign_group(d, idle_group)
            return

        # Build protecting counts and lists for threatened fields
        protecting_counts = {f.id: 0 for f in threatened_fields}
        protecting_drones = {f.id: [] for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in protecting_counts:
                    protecting_counts[tid] += 1
                    protecting_drones[tid].append(d)

        # Identify fields that are initially fully protected and lock their drones
        fully_protected_initial = set()
        for f in threatened_fields:
            cnt = protecting_counts.get(f.id, 0)
            if cnt >= int(f.drones_for_full_protection):
                fully_protected_initial.add(f.id)

        locked_ids = set()
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                locked_ids.add(id(d))

        # Count how many already protect the target
        existing_target_protectors = protecting_drones.get(target_id, [])
        already_protecting_count = len(existing_target_protectors)

        required_total = int(target_field.drones_for_full_protection)
        # If already fully protected, keep those protectors and keep locked protectors for other fully-protected fields
        if already_protecting_count >= required_total:
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_id:
                    environment.assign_group(d, target_group)
                elif getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fully_protected_initial:
                    grp = f"protecting {d.target_id}"
                    environment.assign_group(d, grp if grp in group_ids else idle_group)
                else:
                    environment.assign_group(d, idle_group)
            return

        # Need additional drones
        need = max(0, required_total - already_protecting_count)

        # Candidate drones: all drones except those locked and those already protecting target (they are counted)
        selected_ids = {id(d) for d in existing_target_protectors}
        candidates = [d for d in components if id(d) not in locked_ids and id(d) not in selected_ids]

        # Sort candidates by (moving_to_target, distance_to_rect, id) where moving_to_target is preferred
        def candidate_key(d):
            moving_pref = 0 if (getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == target_id) else 1
            loc = getattr(d, "location", None)
            if loc is None:
                dist2 = float("inf")
            else:
                dist2 = dist2_to_rect(getattr(loc, "x", 0), getattr(loc, "y", 0), target_field)
            return (moving_pref, dist2, id(d))

        candidates.sort(key=candidate_key)

        to_select = candidates[:need]
        final_selected_ids = selected_ids | {id(d) for d in to_select}

        # Assign groups: selected -> target_group, locked protectors remain at their fields, others idle
        for d in components:
            did = id(d)
            if did in final_selected_ids:
                environment.assign_group(d, target_group)
            elif getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fully_protected_initial:
                grp = f"protecting {d.target_id}"
                environment.assign_group(d, grp if grp in group_ids else idle_group)
            else:
                environment.assign_group(d, idle_group)