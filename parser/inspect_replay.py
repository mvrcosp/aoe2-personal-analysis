from pathlib import Path

from mgz.fast.header import decompress, parse_version


REPLAY_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "raw"
    / "AgeIIDE_Replay_510406093.aoe2record"
)


def main():
    with REPLAY_PATH.open("rb") as replay:
        header = decompress(replay)
        version, game, save, log = parse_version(header, replay)

    print(f"version: {version}")
    print(f"game: {game}")
    print(f"save: {save}")
    print(f"log: {log}")


if __name__ == "__main__":
    main()