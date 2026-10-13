from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Filter active fields that have a valid protection group
        active_fields = []
        for f in environment.fields:
            if f.threat_level > 0:
                group_name = f"protecting {f.id}"
                if group_name in group_ids:
                    active_fields.append(f)
        
        if not active_fields or not components:
            for c in components:
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")
            return
        
        # Sort fields by threat level descending
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id = {f.id: f for f in active_fields}
        
        total_drones = len(components)
        plan = {f.id: 0 for f in active_fields}
        remaining = total_drones
        
        # 1. Most threatened field gets priority
        top = active_fields[0]
        need_top = top.drones_for_full_protection
        assign_top = min(need_top, remaining)
        plan[top.id] = assign_top
        remaining -= assign_top
        
        # 2. Try to fully protect other fields (descending threat)
        for f in active_fields[1:]:
            need = f.drones_for_full_protection
            if remaining >= need:
                plan[f.id] = need
                remaining -= need
        
        # 3. Use leftover to partially protect the highest-threat field not fully protected
        if remaining > 0:
            for f in active_fields[1:]:
                need = f.drones_for_full_protection
                if plan[f.id] < need:
                    assign = min(remaining, need - plan[f.id])
                    plan[f.id] += assign
                    remaining -= assign
                    break
        
        # Build drone info with current field assignment
        drone_info = []
        for c in components:
            current_field = None
            if c.target_id is not None:
                tid = str(c.target_id)
                for f in active_fields:
                    if str(f.id) == tid:
                        current_field = f.id
                        break
            drone_info.append({
                'component': c,
                'current_field': current_field,
                'location': c.location
            })
        
        def get_dist(drone_info, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            dx = drone_info['location'].x - cx
            dy = drone_info['location'].y - cy
            return (dx * dx + dy * dy) ** 0.5
        
        assignment = {}  # component -> field_id
        
        # Assign drones field by field in priority order
        for f in active_fields:
            need = plan[f.id]
            if need <= 0:
                continue
            unassigned = [d for d in drone_info if d['component'] not in assignment]
            if not unassigned:
                break
            
            if f.id == top.id:
                # Most threatened: strictly closest drones
                unassigned.sort(key=lambda d: get_dist(d, f))
                selected = unassigned[:need]
            else:
                # Other fields: prefer drones already assigned to this field for stability
                already_on = [d for d in unassigned if d['current_field'] == f.id]
                already_on.sort(key=lambda d: get_dist(d, f))
                if len(already_on) >= need:
                    selected = already_on[:need]
                else:
                    selected = already_on[:]
                    needed_more = need - len(selected)
                    remaining_unassigned = [d for d in unassigned if d not in already_on]
                    remaining_unassigned.sort(key=lambda d: get_dist(d, f))
                    selected.extend(remaining_unassigned[:needed_more])
            
            for d in selected:
                assignment[d['component']] = f.id
        
        # Apply group assignments
        for c in components:
            if c in assignment:
                fid = assignment[c]
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(c, group_name)
                else:
                    if "idle" in group_ids:
                        environment.assign_group(c, "idle")
            else:
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")