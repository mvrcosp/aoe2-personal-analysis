import os
from mgz.fast import operation, meta
from mgz.fast.header import parse
from mgz.fast.enums import Operation, Action

with open("/home/mvrcosp/repos/aoe2-personal-analysis/data/raw/AgeIIDE_Replay_510444990.aoe2record", "rb") as f:
    eof = os.fstat(f.fileno()).st_size
    header = parse(f)
    meta(f)

    while f.tell() < eof:
        try:
            op_type, payload = operation(f)
        except EOFError:
            break

        if op_type == Operation.ACTION:
            action_type, action_data = payload
            if action_type == Action.RESIGN:
                print(f"Player {action_data['player_id']} resigned")
            elif action_type == Action.RESEARCH:
                print(f"Player {action_data['player_id']} researched {action_data['technology_id']}")
            elif action_type == Action.BUILD:
                print(f"Player {action_data['player_id']} built {action_data['building_id']}")

        elif op_type == Operation.CHAT:
            print(f"Chat: {payload}")