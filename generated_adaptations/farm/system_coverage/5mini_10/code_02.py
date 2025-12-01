from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Strategy:
        - Identify fields with threat_level > 0.
        - Count currently protecting drones per field (drones with state == "protecting" and target_id == field.id).
        - Determine which fields are already fully protected (count >= drones_for_full_protection).
        - Select the single field with the highest threat_level as the priority target.
        - If the target is already fully protected, keep its protecting drones and keep drones protecting any other fully protected fields;
          assign all others to "idle".
        - Otherwise, select drones to fully protect the target:
            * Do not take drones that are protecting other already-fully-protected fields.
            * Prefer drones already protecting the target.
            * Among candidates, choose the closest to the target field center until the required count is reached.
        - Assign groups for all drones accordingly using environment.assign_group(...).
        """
        # Build list of fields that currently have threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        # Quick fallback: no threatened fields -> all idle
        if not fields:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    # If "idle" not present for some reason, assign to first available group
                    environment.assign_group(comp, group_ids[0])
            return

        # Map fields by id for quick lookup
        field_by_id = {f.id: f for f in fields}

        # Count currently protecting drones per field and track those drones
        protecting_counts = {f.id: 0 for f in fields}
        protecting_drones = {f.id: [] for f in fields}
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in protecting_drones:
                tid = d.target_id
                protecting_counts[tid] += 1
                protecting_drones[tid].append(d)

        # Fields that are already fully protected
        fully_protected_field_ids = {
            fid for fid, cnt in protecting_counts.items()
            if cnt >= field_by_id[fid].drones_for_full_protection
        }

        # Choose the priority target: highest threat_level (tie-break by id to be deterministic)
        def field_sort_key(f):
            # sort by threat_level desc, then id asc
            return (f.threat_level, f.id)
        target_field = max(fields, key=field_sort_key)
        target_id = target_field.id
        target_group = f"protecting {target_id}"

        # If target group not available in group_ids, fall back to assigning everyone idle
        if target_group not in group_ids:
            for comp in components:
                if "idle" in group_ids:
                    environment.assign_group(comp, "idle")
                else:
                    environment.assign_group(comp, group_ids[0])
            return

        # If target already fully protected: keep its protecting drones and any other fully-protected fields' drones
        if target_id in fully_protected_field_ids:
            for d in components:
                # keep drones protecting the target field
                if getattr(d, "state", None) == "protecting" and d.target_id == target_id:
                    environment.assign_group(d, target_group)
                # keep drones protecting other fully protected fields at their fields
                elif getattr(d, "state", None) == "protecting" and d.target_id in fully_protected_field_ids:
                    grp = f"protecting {d.target_id}"
                    # safe-guard: only assign if group exists, otherwise idle
                    if grp in group_ids:
                        environment.assign_group(d, grp)
                    else:
                        environment.assign_group(d, "idle" if "idle" in group_ids else group_ids[0])
                else:
                    # otherwise idle
                    environment.assign_group(d, "idle" if "idle" in group_ids else group_ids[0])
            return

        # Target is not fully protected: determine how many drones are needed
        required_total = int(target_field.drones_for_full_protection)
        already_protecting = protecting_counts.get(target_id, 0)
        # Number we need to ensure total equals required_total (we will select required_total drones for the target)
        need = max(0, required_total - already_protecting)

        # Build candidate pool: exclude drones that are currently protecting other already-fully-protected fields
        candidate_pool = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fully_protected_field_ids:
                # freeze these drones to stay where they are
                continue
            candidate_pool.append(d)

        # Compute geometric center of the target field (to measure distance)
        cx = (target_field.left + target_field.right) / 2.0
        cy = (target_field.top + target_field.bottom) / 2.0

        def dist2_to_target(drone):
            dx = getattr(drone.location, "x", 0) - cx
            dy = getattr(drone.location, "y", 0) - cy
            return dx * dx + dy * dy

        # Sort candidates: prefer drones already protecting the target (keep them), then by distance
        def candidate_key(d):
            is_protecting_target = (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == target_id)
            return (0 if is_protecting_target else 1, dist2_to_target(d))

        candidates_sorted = sorted(candidate_pool, key=candidate_key)

        # Select exactly required_total drones for the target (we want required_total total, including those already protecting)
        # If there are fewer than required_total candidates (unlikely), select all candidates
        selected_drones = candidates_sorted[:required_total]

        # Prepare a set of identity values for fast membership checks
        selected_ids = {id(d) for d in selected_drones}

        # Assign groups:
        for d in components:
            d_id = id(d)
            # If drone selected for target, assign to target protecting group
            if d_id in selected_ids:
                environment.assign_group(d, target_group)
            # Keep drones that are protecting some fully-protected field at their field
            elif getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in fully_protected_field_ids:
                grp = f"protecting {d.target_id}"
                if grp in group_ids:
                    environment.assign_group(d, grp)
                else:
                    environment.assign_group(d, "idle" if "idle" in group_ids else group_ids[0])
            else:
                # everyone else goes idle
                environment.assign_group(d, "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle"))