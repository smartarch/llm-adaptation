from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather all fields with positive threat level
        threatened_fields = [
            f for f in environment.fields if getattr(f, "threat_level", 0) > 0
        ]

        # If no threatened fields, idle all drones
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (desc) and id (asc) for deterministic tie-breaking
        threatened_fields.sort(
            key=lambda f: (-getattr(f, "threat_level", 0), str(getattr(f, "id", "")))
        )

        top_field = threatened_fields[0]
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))

        # If top field doesn't require protection, idle all
        if top_required <= 0:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Center of the top field for distance calculations
        top_cx = (top_field.left + top_field.right) / 2.0
        top_cy = (top_field.top + top_field.bottom) / 2.0

        # Map drones currently protecting fields (from their read-only state)
        currently_protecting_by_field = {}
        for d in components:
            if getattr(d, "state", None) == "protecting":
                tid = getattr(d, "target_id", None)
                if tid is not None:
                    currently_protecting_by_field.setdefault(tid, []).append(d)

        top_current = currently_protecting_by_field.get(top_field.id, [])
        assigned_final = set()  # drones we explicitly assign to a final group

        # Re-assign current top-field protectors to the correct group
        for d in top_current:
            environment.assign_group(d, f"protecting {top_field.id}")
            assigned_final.add(d)

        # If top field already has enough drones, we may still help others with remaining drones
        if len(top_current) >= top_required:
            # Attempt to partially protect second field with remaining drones (optional)
            if len(threatened_fields) > 1:
                second_field = threatened_fields[1]
                second_required = int(getattr(second_field, "drones_for_full_protection", 0))
                if second_required > 0:
                    second_current = currently_protecting_by_field.get(second_field.id, [])
                    # Drones available to assign to second field
                    remaining = [d for d in components if d not in assigned_final and d not in second_current]
                    if remaining:
                        # Center of second field
                        second_cx = (second_field.left + second_field.right) / 2.0
                        second_cy = (second_field.top + second_field.bottom) / 2.0
                        # Number needed to reach full protection for second field
                        needed_second = max(0, second_required - len(second_current))
                        # Sort available drones by distance to second field center
                        remaining.sort(key=lambda d: (
                            (getattr(d, "location", None).x - second_cx) ** 2 +
                            (getattr(d, "location", None).y - second_cy) ** 2
                        ))
                        for i in range(min(needed_second, len(remaining))):
                            d = remaining[i]
                            environment.assign_group(d, f"protecting {second_field.id}")
                            assigned_final.add(d)
            # All other drones will be idle
            for d in components:
                if d not in assigned_final:
                    environment.assign_group(d, "idle")
            return

        # We need more drones to reach top_field full protection
        need_top = top_required - len(top_current)
        if need_top > 0:
            # Candidates are drones not already assigned to top_field
            candidates = [d for d in components if d not in assigned_final]
            # Sort by distance to top center
            candidates.sort(key=lambda d: (
                (getattr(d, "location", None).x - top_cx) ** 2 +
                (getattr(d, "location", None).y - top_cy) ** 2
            ))
            for i in range(min(need_top, len(candidates))):
                d = candidates[i]
                environment.assign_group(d, f"protecting {top_field.id}")
                assigned_final.add(d)

        # After top field is handled, attempt to allocate any remaining drones to second field for partial protection
        # (optional enhancement to reduce damage further)
        if len(threatened_fields) > 1:
            second_field = threatened_fields[1]
            second_required = int(getattr(second_field, "drones_for_full_protection", 0))
            if second_required > 0:
                second_current = currently_protecting_by_field.get(second_field.id, [])
                # Drones already assigned to top_field in this tick
                top_assigned = assigned_final.copy()
                # Drones available for second after top allocation
                available_for_second = [d for d in components if d not in top_assigned and d not in second_current]
                if available_for_second and len(second_current) < second_required:
                    second_cx = (second_field.left + second_field.right) / 2.0
                    second_cy = (second_field.top + second_field.bottom) / 2.0
                    available_for_second.sort(key=lambda d: (
                        (getattr(d, "location", None).x - second_cx) ** 2 +
                        (getattr(d, "location", None).y - second_cy) ** 2
                    ))
                    needed_second = max(0, second_required - len(second_current))
                    for i in range(min(needed_second, len(available_for_second))):
                        d = available_for_second[i]
                        environment.assign_group(d, f"protecting {second_field.id}")
                        assigned_final.add(d)

        # Finally, assign any drones not in assigned_final to idle
        for d in components:
            if d not in assigned_final:
                environment.assign_group(d, "idle")