import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aocref


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "raw" / "api" / "api_match_history_612334_2.json"
DEFAULT_OUTPUT = (
    PROJECT_DIR
    / "data"
    / "processed"
    / "api"
    / "match_history_612334_2026-10-02_2026-10-04.csv"
)
DEFAULT_PROFILE_ID = 612334
DEFAULT_START_DATE = date(2026, 10, 2)
DEFAULT_END_DATE = date(2026, 10, 4)
CSV_COLUMNS = [
    "match_id",
    "data_hora",
    "mapa",
    "resultado",
    "civilizacao",
    "rating_antes",
    "rating_depois",
    "url_replay",
]


def load_civilizations() -> dict[int, str]:
    aocref_dir = Path(aocref.__file__).resolve().parent
    dataset_path = aocref_dir / "data" / "datasets" / "100.json"
    with dataset_path.open(encoding="utf-8") as dataset_file:
        dataset = json.load(dataset_file)
    return {
        civilization["id"]: civilization["name"]
        for civilization in dataset["civilizations"].values()
    }


def clean_map_name(map_name: str) -> str:
    suffix = Path(map_name).suffix.lower()
    if suffix in {".rms", ".rms2"}:
        return Path(map_name).stem
    return map_name


def extract_matches(
    payload: dict[str, Any],
    profile_id: int,
    start_date: date,
    end_date: date,
    timezone: ZoneInfo,
    civilizations: dict[int, str],
) -> list[tuple[datetime, dict[str, Any]]]:
    exported_matches = []

    for match in payload["matchHistoryStats"]:
        result = next(
            (
                row
                for row in match["matchhistoryreportresults"]
                if row["profile_id"] == profile_id
            ),
            None,
        )
        if result is None:
            continue

        played_at = datetime.fromtimestamp(match["startgametime"], timezone)
        if not start_date <= played_at.date() <= end_date:
            continue

        member = next(
            (
                row
                for row in match["matchhistorymember"]
                if row["profile_id"] == profile_id
            ),
            None,
        )
        if member is None:
            raise ValueError(
                f"A partida {match['id']} não tem dados de rating "
                f"para o perfil {profile_id}."
            )

        civilization_id = result["civilization_id"]
        if civilization_id not in civilizations:
            raise ValueError(
                f"ID de civilização desconhecido na partida {match['id']}: "
                f"{civilization_id}."
            )

        outcome = member["outcome"]
        if outcome not in {0, 1}:
            raise ValueError(
                f"Resultado desconhecido na partida {match['id']}: {outcome}."
            )

        replay_url = next(
            (
                replay["url"]
                for replay in match.get("matchurls", [])
                if replay.get("profile_id") == profile_id
            ),
            "",
        )
        exported_matches.append(
            (
                played_at,
                {
                    "match_id": match["id"],
                    "data_hora": played_at.isoformat(timespec="seconds"),
                    "mapa": clean_map_name(match["mapname"]),
                    "resultado": "Vitória" if outcome == 1 else "Derrota",
                    "civilizacao": civilizations[civilization_id],
                    "rating_antes": member["oldrating"],
                    "rating_depois": member["newrating"],
                    "url_replay": replay_url,
                },
            )
        )

    return sorted(exported_matches, key=lambda entry: entry[0])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta para CSV as partidas de um perfil em um intervalo de datas."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile-id", type=int, default=DEFAULT_PROFILE_ID)
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=DEFAULT_START_DATE,
        help="Data inicial inclusiva (AAAA-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=DEFAULT_END_DATE,
        help="Data final inclusiva (AAAA-MM-DD).",
    )
    parser.add_argument(
        "--timezone",
        default="America/Sao_Paulo",
        help="Fuso horário usado para filtrar e exibir data/hora.",
    )
    args = parser.parse_args()
    if args.start_date > args.end_date:
        parser.error("--start-date não pode ser posterior a --end-date.")
    return args


def main() -> None:
    args = parse_args()
    timezone = ZoneInfo(args.timezone)
    with args.input.open(encoding="utf-8") as json_file:
        payload = json.load(json_file)

    matches = extract_matches(
        payload,
        args.profile_id,
        args.start_date,
        args.end_date,
        timezone,
        load_civilizations(),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(row for _, row in matches)

    if matches:
        print(f"{len(matches)} partida(s) exportada(s) para: {args.output}")
    else:
        print(
            f"Nenhuma partida do perfil {args.profile_id} encontrada entre "
            f"{args.start_date} e {args.end_date} ({args.timezone}). "
            f"CSV com cabeçalho salvo em: {args.output}"
        )


if __name__ == "__main__":
    main()
