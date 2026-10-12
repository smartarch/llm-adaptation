from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember last target field id for each drone (by id(d) as key)
        self._drone_last_target = {}
        self._last_step = -1

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather threatened fields (threat_level > 0) and sort by threat
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threatened_fields.sort(key=lambda fld: fld.threat_level, reverse=True)

        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        centers = {fld.id: field_center(fld) for fld in threatened_fields}

        def dist_to_field(drone, field_id):
            cx, cy = centers[field_id]
            dx = drone.location.x - cx
            dy = drone.location.y - cy
            return (dx * dx + dy * dy) ** 0.5

        # Build current protection mapping
        # drones_protecting[field_id] -> list of drone objects currently protecting that field
        drones_protecting = {fld.id: [] for fld in threatened_fields}
        idle_drones = []
        for d in components:
            cur_state = getattr(d, "state", None)
            cur_target = getattr(d, "target_id", None)
            if cur_state == "protecting" and cur_target in drones_protecting:
                drones_protecting[cur_target].append(d)
            else:
                idle_drones.append(d)

        plan = {}  # drone -> group_id

        if threatened_fields:
            top_field = threatened_fields[0]
            top_group = f"protecting {top_field.id}"

            # Drones already protecting the top field stay in place
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    plan[d] = top_group

            current_top = len([d for d, g in plan.items() if g == top_group])
            needed_top = max(0, top_field.drones_for_full_protection - current_top)

            if needed_top > 0:
                # Candidates: all drones not already protecting the top field
                candidates = [d for d in components if plan.get(d, None) != top_group]
                # Bias: prefer drones that previously protected the top field
                def priority(d):
                    last = self._drone_last_target.get(id(d), None)
                    bias = 0
                    if last == top_field.id:
                        bias = -1  # prefer
                    return (bias, dist_to_field(d, top_field.id))
                candidates.sort(key=priority)

                for d in candidates[:needed_top]:
                    plan[d] = top_group

            # Update last targets for those assigned to top
            for d, g in list(plan.items()):
                if g == top_group:
                    self._drone_last_target[id(d)] = top_field.id

            # Ensure other fields get protection as needed
            remaining = [d for d in components if d not in plan]

            for fld in threatened_fields[1:]:
                group_name = f"protecting {fld.id}"
                current_on_field = len([d for d, g in plan.items() if g == group_name])
                needed = max(0, fld.drones_for_full_protection - current_on_field)
                if needed <= 0:
                    continue
                # Choose closest remaining drones to this field
                remaining.sort(key=lambda dv: dist_to_field(dv, fld.id))
                for d in remaining[:needed]:
                    plan[d] = group_name
                # Remove assigned drones from remaining
                remaining = [d for d in remaining if d not in plan]

            # Step 3: Try to ensure at least half protection (if possible)
            total = len(components)
            protected_now = len([d for d in components if plan.get(d, None) and plan[d].startswith("protecting")])
            min_protected = (total + 1) // 2
            if protected_now < min_protected:
                # Try to protect more with top field if possible
                top_group = f"protecting {top_field.id}"
                current_top = len([d for d in components if plan.get(d) == top_group])
                need_more = max(0, top_field.drones_for_full_protection - current_top)
                if need_more > 0:
                    add_candidates = [d for d in components if d not in plan]
                    add_candidates.sort(key=lambda dv: dist_to_field(dv, top_field.id))
                    for d in add_candidates[:need_more]:
                        plan[d] = top_group
                    # update
                    protected_now = len([d for d in components if plan.get(d) == top_group])

            # If still not enough, fill other fields a bit more (without over-protecting)
            if protected_now < min_protected:
                for fld in threatened_fields[1:]:
                    group_name = f"protecting {fld.id}"
                    current_on_field = len([d for d in components if plan.get(d) == group_name])
                    if current_on_field >= fld.drones_for_full_protection:
                        continue
                    remaining = [d for d in components if d not in plan]
                    remaining.sort(key=lambda dv: dist_to_field(dv, fld.id))
                    for d in remaining[:1]:  # try to add a little protection
                        plan[d] = group_name
                        protected_now += 1
                        if protected_now >= min_protected:
                            break
                    if protected_now >= min_protected:
                        break

        # Step 4: Assign groups to drones
        # Any drone not in plan becomes idle
        for d in components:
            group = plan.get(d, "idle")
            if group not in group_ids:
                group = "idle"
            environment.assign_group(d, group)

        # Update last_target for drones (for stickiness)
        for d in components:
            grp = plan.get(d, "idle")
            if grp != "idle" and grp.startswith("protecting"):
                field_id = grp[len("protecting "):]
                self._drone_last_target[id(d)] = field_id
            else:
                self._drone_last_target[id(d)] = None

        self._last_step = step