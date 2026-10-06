import json
import re
import sys
from pathlib import Path
from typing import Any

from mgz.model import Match, parse_match, serialize

diretorio_projeto = Path(__file__).resolve().parent.parent
diretorio_origem = diretorio_projeto / "data" / "raw" / "aoe2rec"
diretorio_destino = diretorio_projeto / "data" / "processed" / "aoe2rec"
PADRAO_NOME_REPLAY = re.compile(r"AgeIIDE_Replay_(\d+)\.aoe2record\Z")


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


def is_processed(output_path: Path) -> bool:
    if not output_path.is_file():
        return False

    try:
        with output_path.open(encoding="utf-8") as json_file:
            json.load(json_file)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(
            f"JSON processado inválido; será gerado novamente: "
            f"{output_path} ({error})",
            file=sys.stderr,
        )
        return False
    return True


def convert_replays(
    replay_paths: list[Path],
    destination_directory: Path = diretorio_destino,
) -> tuple[int, int]:
    converted = 0
    skipped = 0

    for replay_path in sorted(replay_paths):
        match_name = PADRAO_NOME_REPLAY.fullmatch(replay_path.name)
        if match_name is None:
            raise ValueError(
                "Nome de replay inesperado; esperado "
                f"'AgeIIDE_Replay_{{MATCH_ID}}.aoe2record': {replay_path.name}"
            )

        match_id = match_name.group(1)
        output_path = destination_directory / f"match_data_{match_id}.json"
        if is_processed(output_path):
            skipped += 1
            print(f"Partida {match_id}: JSON já processado; conversão ignorada.")
            continue

        match_data = serialize_match(parse_replay(replay_path))
        save_json(match_data, output_path)
        converted += 1
        print(f"Partida {match_id}: JSON salvo em {output_path}")

    return converted, skipped


def main() -> None:
    replay_paths = find_replays()
    converted, skipped = convert_replays(replay_paths)
    print(
        f"Resumo: {converted} replay(s) convertido(s), "
        f"{skipped} JSON(s) válido(s) já existiam."
    )


if __name__ == "__main__":
    main()
