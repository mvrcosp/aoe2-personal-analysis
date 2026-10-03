import json
import re
from pathlib import Path
from typing import Any

from mgz.model import Match, parse_match, serialize

diretorio_projeto = Path(__file__).resolve().parent.parent
diretorio_origem = diretorio_projeto / "data" / "raw" / "aoe2rec"
diretorio_destino = diretorio_projeto / "data" / "processed" / "aoe2rec"


def find_replays(source_directory: Path = diretorio_origem) -> list[Path]:
    replays = sorted(source_directory.glob("*.aoe2record"))
    if not replays:
        raise FileNotFoundError(
            f"Nenhum arquivo .aoe2record encontrado em: {source_directory}"
        )
    return replays


def parse_replay(replay_path: Path) -> Match:
    with replay_path.open("rb") as replay:
        match = parse_match(replay)
    return match


def serialize_match(match: Match) -> Any:
    return serialize(match)


def save_json(match_data: Any, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as json_file:
        json.dump(match_data, json_file, indent=2)


def main() -> None:
    for replay_path in find_replays():
        codigo_partida = re.search(r"(\d+)$", replay_path.stem)
        if codigo_partida is None:
            raise ValueError(
                "Não foi possível extrair o código da partida do nome: "
                f"{replay_path.name}"
            )

        match = parse_replay(replay_path)
        match_data = serialize_match(match)
        output_path = diretorio_destino / f"match_data_{codigo_partida.group(1)}.json"
        save_json(match_data, output_path)
        print(f"Arquivo salvo com sucesso em: {output_path}")


if __name__ == "__main__":
    main()
