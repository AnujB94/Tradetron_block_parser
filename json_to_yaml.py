import json

def parse_instrument_str(inst):
    """Helper to get a clean symbol name for operands."""
    if not inst or not isinstance(inst, dict):
        return "Unknown"
    return inst.get("symbol_token", "")

def parse_operand(op):
    """
    Parses operands to look like UI text: 
    e.g. 'LTP (NIFTY)' or '0' instead of dictionaries.
    """
    # 1. Handle Static Numbers (e.g. {'type': 'number', 'title': '0'})
    if isinstance(op, dict) and op.get("type") == "number":
        return str(op.get("title", op.get("value", "0")))

    if not isinstance(op, dict):
        return str(op)

    # 2. Handle Indicators / Keywords
    name = op.get("function_name") or op.get("keyword") or op.get("pattern_name")
    
    if name:
        # Special handling for Set/Get Runtime to look cleaner
        if name == "Set Runtime":
            # Use params if available
            params = op.get("params", {})
            var = params.get("variable_name", "Var")
            val = parse_operand(params.get("value", ""))
            return f"Set Runtime({var} = {val})"
        
        if name in ["Get Runtime", "Get Runtime Number"]:
            params = op.get("params", {})
            return f"Get Runtime ({params.get('variable_name', '')})"

        # Handle standard inputs/instrument
        inputs = op.get("inputs", {})
        inst = inputs.get("instrument") or op.get("instrument")
        
        # If there is an instrument, format as Keyword (Symbol)
        if inst:
            symbol = parse_instrument_str(inst)
            # Handle timeframe if present (e.g., Low(15m))
            tf = op.get("timeframe")
            if tf:
                return f"{name} ({symbol}, {tf})"
            return f"{name} ({symbol})"
            
    return str(op)

def parse_condition(condition_node):
    """Recursive function to handle Groups and Comparisons."""
    if not isinstance(condition_node, dict):
        return ""

    c_type = condition_node.get("condition_type")

    if c_type == "GROUP":
        logic = condition_node.get('connection_logic', 'AND')
        sub_conditions = [parse_condition(c) for c in condition_node.get("conditions", [])]
        if len(sub_conditions) > 1:
            return f"\n      {logic} ".join(sub_conditions)
        return sub_conditions[0] if sub_conditions else ""

    elif c_type == "COMPARE":
        left = parse_operand(condition_node.get("left"))
        op = condition_node.get("operator")
        right = parse_operand(condition_node.get("right"))
        return f"{left} {op} {right}"
    
    # Handle standalone keywords (like Set Runtime sitting in conditions)
    elif "keyword" in condition_node:
        return parse_operand(condition_node)
    
    return ""

def parse_position(pos):
    """
    Formats position to match the image style:
    BUY [ NFO, NIFTY, CALL, -, ATM, MIS, 1 ]
    """
    t_type = pos.get("transaction_type", "BUY")
    prod = pos.get("product_type", "MIS")
    
    qty_setup = pos.get("quantity_setup", {})
    qty_val = str(qty_setup.get("value", 1))
    
    inst = pos.get("instrument", {})
    ex = inst.get("exchange", "NFO")
    sym = inst.get("symbol_token", "NIFTY")
    i_type = inst.get("instrument_type", "FUT")
    
    # Expiry - Use "-" if it's dynamic/current to match image style often seen
    expiry_conf = inst.get("expiry_config", {})
    expiry = "-" 
    if expiry_conf.get("type") == "Specific Date":
        expiry = expiry_conf.get("date")

    # Strike Logic
    strike_str = "-"
    if i_type in ["CALL", "PUT"]:
        strike_config = inst.get("strike_config", {})
        method = strike_config.get("selection_method", "ATM")
        offset = strike_config.get("offset", 0)
        
        if offset == 0:
            strike_str = method
        elif offset > 0:
            strike_str = f"{method}+{offset}"
        else:
            strike_str = f"{method}{offset}"
            
    # Assemble the list inside brackets
    # Format: [ Exchange, Symbol, InstType, Expiry, Strike, Product, Qty ]
    details_list = [ex, sym, i_type, expiry, strike_str, prod, qty_val]
    
    return f"{t_type} [ {', '.join(details_list)} ]"

def convert_json_to_text(json_data):
    output = []
    
    for strategy_set in json_data.get("strategy_sets", []):
        set_idx = strategy_set.get("set_index", 1)
        output.append(f"Set #{set_idx}")
        output.append("-" * 35)
        
        for phase in strategy_set.get("phases", []):
            p_type = phase.get("phase_type", "Entry")
            
            # Phase Header
            output.append(f"Phase: {p_type}")
            
            # Conditions Section
            conditions = phase.get("conditions", {})
            output.append("  Conditions:")
            if conditions:
                readable_logic = parse_condition(conditions)
                # Split logic by newlines to ensure indentation
                for line in readable_logic.split('\n'):
                    output.append(f"    {line}")
            else:
                output.append("    (None)")
            
            # Positions Section
            positions = phase.get("positions", [])
            if positions:
                output.append("\n  Positions:")
                for pos in positions:
                    output.append(f"    {parse_position(pos)}")
            
            output.append("") # Empty line between phases
            
    return "\n".join(output)


input_json = {
  "strategy_sets": [
    {
      "set_index": 1,
      "phases": [
        {
          "phase_type": "Entry",
          "conditions": {
            "condition_type": "GROUP",
            "connection_logic": "AND",
            "conditions": [
              {
                "condition_type": "COMPARE",
                "left": {
                  "keyword": "LTP",
                  "inputs": {
                    "instrument": {
                      "exchange": "NSE",
                      "symbol_token": "NIFTY 50",
                      "instrument_type": "EQUITY"
                    }
                  }
                },
                "operator": ">",
                "right": {
                  "type": "number",
                  "title": "0"
                }
              },
              {
                "description": "Captures the Low of the previous 15m candle at the moment of entry to use as Stop Loss.",
                "keyword": "Set Runtime",
                "params": {
                  "variable_name": "EntryCandleLow",
                  "value": {
                    "function_name": "LOW",
                    "timeframe": "15m",
                    "position_offset": -1,
                    "instrument": {
                      "exchange": "NSE",
                      "symbol_token": "NIFTY 50",
                      "instrument_type": "EQUITY"
                    }
                  }
                }
              }
            ]
          },
          "positions": [
            {
              "description": "Leg 1: Buy ATM Nifty Call",
              "transaction_type": "BUY",
              "product_type": "NRML",
              "instrument": {
                "exchange": "NFO",
                "symbol_token": "NIFTY",
                "instrument_type": "CALL",
                "expiry_config": {
                  "type": "Current Week",
                  "offset": 0
                },
                "strike_config": {
                  "selection_method": "ATM",
                  "offset": 0
                }
              },
              "quantity_setup": {
                "type": "Lots",
                "value": 1
              }
            },
            {
              "description": "Leg 2: Sell OTM Nifty Call (200 points higher = approx 4 strikes)",
              "transaction_type": "SELL",
              "product_type": "NRML",
              "instrument": {
                "exchange": "NFO",
                "symbol_token": "NIFTY",
                "instrument_type": "CALL",
                "expiry_config": {
                  "type": "Current Week",
                  "offset": 0
                },
                "strike_config": {
                  "selection_method": "ATM",
                  "offset": 4
                }
              },
              "quantity_setup": {
                "type": "Lots",
                "value": 1
              }
            }
          ]
        },
        {
          "phase_type": "Exit",
          "conditions": {
            "description": "Exit if current Nifty Price closes below the stored Entry Candle Low.",
            "condition_type": "COMPARE",
            "left": {
              "keyword": "LTP",
              "inputs": {
                "instrument": {
                  "exchange": "NSE",
                  "symbol_token": "NIFTY 50",
                  "instrument_type": "EQUITY"
                }
              }
            },
            "operator": "<",
            "right": {
              "keyword": "Get Runtime",
              "params": {
                "variable_name": "EntryCandleLow"
              }
            }
          },
          "positions": []
        }
      ]
    }
  ]
}

print(convert_json_to_text(input_json))