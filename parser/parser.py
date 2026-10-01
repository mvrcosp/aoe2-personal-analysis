import os
from pathlib import Path
from datetime import datetime
from mgz.model import parse_match

print(datetime.now())


REPLAY_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "raw"
    / "AgeIIDE_Replay_510406093.aoe2record"
)


def main():
    print(f"Parsing replay: {REPLAY_PATH}")

    with REPLAY_PATH.open("rb") as replay:
        match = parse_match(replay)

    print("Replay parsed successfully!")
    print(f"Map: {match.map.name}")
    print(f"Perspective player: {match.file.perspective.number}")


if __name__ == "__main__":
    main()