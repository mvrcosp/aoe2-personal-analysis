import os
from mgz.fast import operation, meta
from mgz.fast.header import parse
from mgz.fast.enums import Operation

with open("/home/mvrcosp/repos/aoe2-personal-analysis/data/raw/AgeIIDE_Replay_510444990.aoe2record", "rb") as f:
    eof = os.fstat(f.fileno()).st_size
    header = parse(f)
    meta(f)

    elapsed_ms = 0
    while f.tell() < eof:
        try:
            op_type, payload = operation(f)
        except EOFError:
            break

        if op_type == Operation.SYNC:
            increment, checksum, data = payload
            elapsed_ms += increment

    minutes = elapsed_ms / 1000 / 60
    print(f"Game duration: {minutes:.1f} minutes")