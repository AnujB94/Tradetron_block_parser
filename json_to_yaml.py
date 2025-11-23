import json

def parse_operand(op):
    """Parses the Left or Right side of a comparison."""
    if isinstance(op, dict):
        if "function_name" in op:
            name = op.get("function_name")
            tf = op.get("timeframe", "")
            inputs = [str(v) for k, v in op.get("inputs", {}).items()]
            params = ", ".join([tf] + inputs) if tf or inputs else ""
            return f"{name}({params})" if params else name
        
        if "instrument" in op:
            inst = op["instrument"]
            # FIX: Get 'keyword' from the main object (op), not the instrument object (inst)
            keyword = op.get('keyword', 'Value')
            symbol = inst.get('symbol_token', 'Unknown')
            return f"{keyword} ({symbol})"
            
    return str(op)

def parse_condition(condition_node):
    """Recursive function to handle Groups and Comparisons."""
    c_type = condition_node.get("condition_type")

    if c_type == "GROUP":
        logic = condition_node.get('connection_logic', 'AND')
        sub_conditions = [parse_condition(c) for c in condition_node.get("conditions", [])]
        
        if len(sub_conditions) > 1:
            separator = f"\n    {logic}\n    "
            return separator.join(sub_conditions)
            
        return sub_conditions[0] if sub_conditions else ""

    elif c_type == "COMPARE":
        left = parse_operand(condition_node.get("left"))
        op = condition_node.get("operator")
        right = parse_operand(condition_node.get("right"))
        return f"{left} {op} {right}"
    
    return ""

def parse_position(pos):
    t_type = pos.get("transaction_type", "")
    prod = pos.get("product_type", "")
    qty = pos.get("quantity_setup", {}).get("value", 0)
    
    inst = pos.get("instrument", {})
    ex = inst.get("exchange", "")
    sym = inst.get("symbol_token", "")
    i_type = inst.get("instrument_type", "")
    
    expiry = inst.get("expiry_config", {}).get("type", "-")
    
    # --- OFFSET LOGIC ---
    strike_config = inst.get("strike_config", {})
    strike = strike_config.get("selection_method", "-")
    offset = strike_config.get("offset", 0)
    
    if offset > 0:
        strike = f"{strike}+{offset}"
    elif offset < 0:
        strike = f"{strike}{offset}" 
    
    details = [ex, sym, i_type]
    if i_type in ["OPTION", "CALL", "PUT"]:
        details.extend([expiry, strike])
    details.extend([prod, str(qty)])
    
    return f"{t_type} [ {', '.join(details)} ]"

def convert_json_to_text(json_data):
    output = []
    
    for strategy_set in json_data.get("strategy_sets", []):
        set_idx = strategy_set.get("set_index", 0)
        output.append(f"Set #{set_idx + 1}")
        output.append("-" * 25)
        
        for phase in strategy_set.get("phases", []):
            p_type = phase.get("phase_type", "Unknown Phase")
            output.append(f"Phase: {p_type}")
            
            conditions = phase.get("entry_conditions", {})
            if conditions:
                readable_logic = parse_condition(conditions)
                output.append("  Conditions:")
                output.append(f"    {readable_logic}")
            
            positions = phase.get("positions", [])
            if positions:
                output.append("\n  Positions:")
                for pos in positions:
                    output.append(f"    {parse_position(pos)}")
            
            output.append("\n")
            
    return "\n".join(output)