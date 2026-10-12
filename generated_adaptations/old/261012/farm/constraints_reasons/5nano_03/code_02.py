from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: drone index -> group_id (e.g., "protecting fieldX" or "idle")
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        n_drones = len(components)

        # Gather fields with threat > 0
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened_fields:
            for idx, comp in enumerate(components):
                environment.assign_group(comp, "idle")
                self.prev_assignments[idx] = "idle"
            return

        # Sort fields by threat desc, then by id to break ties deterministically
        threatened_fields.sort(key=lambda f: (-f.threat_level, getattr(f, "id", "")))
        top_field = threatened_fields[0]
        top_group = f"protecting {top_field.id}"

        # If the top group's not in the provided group_ids, fall back to idling
        if top_group not in group_ids:
            for idx, comp in enumerate(components):
                environment.assign_group(comp, "idle")
                self.prev_assignments[idx] = "idle"
            return

        # Field center for distance computations
        top_center_x = (top_field.left + top_field.right) / 2.0
        top_center_y = (top_field.top + top_field.bottom) / 2.0

        # Identify drones currently protecting the top field
        current_top_indices = []
        for i, comp in enumerate(components):
            if comp.state == "protecting" and comp.target_id == top_field.id:
                current_top_indices.append(i)

        # How many drones are needed for full protection of the top field?
        drones_for_top = getattr(top_field, "drones_for_full_protection", 0)
        needed_top = min(drones_for_top, n_drones)

        top_indices = set(current_top_indices)

        # If not enough drones on top, pick closest from others
        if len(top_indices) < needed_top:
            candidates = []
            for i, comp in enumerate(components):
                if i in top_indices:
                    continue
                dx = comp.location.x - top_center_x
                dy = comp.location.y - top_center_y
                dist2 = dx * dx + dy * dy
                candidates.append((dist2, i))
            candidates.sort()
            to_add = min(needed_top - len(top_indices), len(candidates))
            for k in range(to_add):
                top_indices.add(candidates[k][1])

        # Remaining drones indices to consider for other fields
        remaining_indices = [i for i in range(n_drones) if i not in top_indices]

        # Build current counts for other fields
        field_id_to_current_count = {f.id: 0 for f in threatened_fields}
        for i, comp in enumerate(components):
            if comp.state == "protecting" and comp.target_id in field_id_to_current_count:
                field_id_to_current_count[comp.target_id] += 1

        # Prepare assignment mapping
        assign_map = {}  # drone_index -> group_id

        # 1) Continuity pass: try to keep drones on their previously protected field if feasible
        indices_to_consider = list(remaining_indices)
        for i in list(indices_to_consider):
            prev_group = self.prev_assignments.get(i)
            if prev_group and prev_group.startswith("protecting "):
                prev_field_id = prev_group[len("protecting "):]
                # Do not move if it's already the top field
                if prev_field_id != top_field.id:
                    # Check capacity for that field
                    field_cap = next((f.drones_for_full_protection for f in threatened_fields if f.id == prev_field_id), None)
                    if field_cap is not None and field_id_to_current_count.get(prev_field_id, 0) < field_cap:
                        assign_map[i] = f"protecting {prev_field_id}"
                        field_id_to_current_count[prev_field_id] += 1
                        indices_to_consider.remove(i)

        # 2) Fill remaining to other fields by threat level (greedy, closest drone)
        # Build fields excluding the top field, sorted by threat
        other_fields = [f for f in threatened_fields if f.id != top_field.id]
        other_fields.sort(key=lambda f: -f.threat_level)

        for f in other_fields:
            if not indices_to_consider:
                break
            field_cap = getattr(f, "drones_for_full_protection", 0)
            cur = field_id_to_current_count.get(f.id, 0)
            need = max(0, field_cap - cur)
            if need <= 0:
                continue

            # For each need, pick the closest drone from the remaining pool
            for _ in range(need):
                if not indices_to_consider:
                    break
                best_idx = None
                best_dist2 = None
                center_x = (f.left + f.right) / 2.0
                center_y = (f.top + f.bottom) / 2.0
                for idx in indices_to_consider:
                    c = components[idx]
                    dx = c.location.x - center_x
                    dy = c.location.y - center_y
                    d2 = dx * dx + dy * dy
                    if best_dist2 is None or d2 < best_dist2:
                        best_dist2 = d2
                        best_idx = idx
                if best_idx is None:
                    break
                assign_map[best_idx] = f"protecting {f.id}"
                field_id_to_current_count[f.id] = field_id_to_current_count.get(f.id, 0) + 1
                indices_to_consider.remove(best_idx)

        # 3) Remaining drones become idle (or could be kept idle by design)
        for idx in indices_to_consider:
            assign_map[idx] = "idle"

        # 4) If some drones were already in top_indices, ensure they get the top_group
        for i in top_indices:
            assign_map[i] = top_group

        # 5) Apply assignments and store memory
        for i, comp in enumerate(components):
            group = assign_map.get(i, "idle")
            environment.assign_group(comp, group)
            self.prev_assignments[i] = group