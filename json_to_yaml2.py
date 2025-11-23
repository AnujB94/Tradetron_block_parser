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
            return f"{inst.get('keyword', 'Value')} ({inst.get('symbol_token')})"
            
    return str(op)

def parse_condition(condition_node):
    """Recursive function to handle Groups and Comparisons with multiline formatting."""
    c_type = condition_node.get("condition_type")

    if c_type == "GROUP":
        logic = condition_node.get('connection_logic', 'AND')
        sub_conditions = [parse_condition(c) for c in condition_node.get("conditions", [])]
        
        if len(sub_conditions) > 1:
            # Join with newline + logic + newline (and indentation spaces)
            # The indentation here (4 spaces) aligns with the parent container
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
    strike = inst.get("strike_config", {}).get("selection_method", "-")
    
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
        output.append("-" * 20)
        
        for phase in strategy_set.get("phases", []):
            p_type = phase.get("phase_type", "Unknown Phase")
            output.append(f"Phase: {p_type}")
            
            conditions = phase.get("entry_conditions", {})
            if conditions:
                readable_logic = parse_condition(conditions)
                output.append("  Conditions:")
                # Indent the whole block by 4 spaces
                output.append(f"    {readable_logic}")
            
            positions = phase.get("positions", [])
            if positions:
                output.append("\n  Positions:")
                for pos in positions:
                    output.append(f"    {parse_position(pos)}")
            
            output.append("\n")
            
    return "\n".join(output)

# --- EXECUTION WITH YOUR DATA ---

input_json = {
  "strategy_sets": [
    {
      "set_index": 0,
      "phases": [
        {
          "phase_type": "Entry",
          "entry_conditions": {
            "condition_type": "GROUP",
            "connection_logic": "AND",
            "conditions": [
              {
                "condition_type": "COMPARE",
                "left": { "function_name": "Time", "timeframe": "1m", "inputs": {} },
                "operator": ">",
                "right": "11:30"
              },
              {
                "condition_type": "COMPARE",
                "left": { "function_name": "Time", "timeframe": "1m", "inputs": {} },
                "operator": "<",
                "right": "11:35"
              }
            ]
          },
          "positions": [
            {
              "instrument": {
                "exchange": "NSE",
                "symbol_token": "NIFTY",
                "instrument_type": "CALL",
                "expiry_config": { "type": "Current Week" },
                "strike_config": { "selection_method": "ATM" }
              },
              "transaction_type": "BUY",
              "product_type": "MIS",
              "quantity_setup": { "type": "Fixed Quantity", "value": 1 }
            },
            {
              "instrument": {
                "exchange": "NSE",
                "symbol_token": "NIFTY",
                "instrument_type": "PUT",
                "expiry_config": { "type": "Current Week" },
                "strike_config": { "selection_method": "ATM" }
              },
              "transaction_type": "BUY",
              "product_type": "MIS",
              "quantity_setup": { "type": "Fixed Quantity", "value": 1 }
            }
          ]
        }
      ]
    }
  ]
}

print(convert_json_to_text(input_json))