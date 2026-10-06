import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent.parent
API_DATA_DIRECTORY = PROJECT_DIR / "data" / "raw" / "api"
DEFAULT_PAYLOAD_DIRECTORY = API_DATA_DIRECTORY / "payload"
DEFAULT_MATCH_IDS_DIRECTORY = API_DATA_DIRECTORY / "matchIDs"
DEFAULT_PROFILE_ID = 612334
API_URL = (
    "https://aoe-api.worldsedgelink.com/community/leaderboard/"
    "getRecentMatchHistory"
)


def request_match_history(profile_id: int, timeout: float) -> dict[str, Any]:
    query = urlencode(
        {
            "title": "age2",
            "profile_ids": json.dumps([profile_id]),
        }
    )
    request = Request(
        f"{API_URL}?{query}",
        headers={"User-Agent": "aoe2-personal-analysis"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise RuntimeError(
            f"A API de histórico respondeu com HTTP {error.code}: {error.reason}."
        ) from error
    except URLError as error:
        raise RuntimeError(f"Não foi possível consultar a API: {error.reason}.") from error
    except json.JSONDecodeError as error:
        raise RuntimeError("A API retornou uma resposta que não é JSON válido.") from error

    if not isinstance(payload, dict):
        raise ValueError("A resposta da API precisa ser um objeto JSON.")
    return payload


def extract_match_ids(payload: dict[str, Any], profile_id: int) -> list[int]:
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("code") != 0:
        message = result.get("message") if isinstance(result, dict) else None
        raise RuntimeError(f"A API não confirmou sucesso na consulta: {message!r}.")

    matches = payload.get("matchHistoryStats")
    if not isinstance(matches, list):
        raise ValueError("A resposta da API não contém uma lista matchHistoryStats.")

    match_ids = []
    seen_ids = set()
    for index, match in enumerate(matches):
        if not isinstance(match, dict):
            raise ValueError(f"A partida na posição {index} não é um objeto JSON.")

        participants = match.get("matchhistoryreportresults")
        if not isinstance(participants, list):
            raise ValueError(
                f"A partida na posição {index} não contém "
                "uma lista matchhistoryreportresults."
            )

        if not any(
            isinstance(participant, dict)
            and participant.get("profile_id") == profile_id
            for participant in participants
        ):
            continue

        match_id = match.get("id")
        if not isinstance(match_id, int) or isinstance(match_id, bool):
            raise ValueError(
                f"A partida do perfil {profile_id} na posição {index} "
                f"tem um ID inválido: {match_id!r}."
            )
        if match_id not in seen_ids:
            seen_ids.add(match_id)
            match_ids.append(match_id)

    return match_ids


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def fetch_and_save(
    profile_id: int,
    payload_directory: Path = DEFAULT_PAYLOAD_DIRECTORY,
    match_ids_directory: Path = DEFAULT_MATCH_IDS_DIRECTORY,
    timeout: float = 30,
) -> tuple[Path, Path, list[int]]:
    requested_at = datetime.now(timezone.utc)
    timestamp = requested_at.strftime("%Y%m%dT%H%M%S%fZ")
    payload = request_match_history(profile_id, timeout)

    payload_path = payload_directory / f"payload_match_history_{timestamp}.json"
    ids_path = match_ids_directory / f"matchIDs_match_history_{timestamp}.json"
    save_json(payload_path, payload)

    match_ids = extract_match_ids(payload, profile_id)
    save_json(
        ids_path,
        {
            "profile_id": profile_id,
            "requested_at": requested_at.isoformat(),
            "match_ids": match_ids,
        },
    )
    return payload_path, ids_path, match_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consulta o histórico recente do perfil e salva a resposta "
            "e os IDs das partidas em JSON."
        )
    )
    parser.add_argument(
        "--profile-id",
        type=int,
        default=DEFAULT_PROFILE_ID,
        help=f"ID do jogador na API (padrão: {DEFAULT_PROFILE_ID}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Tempo limite da requisição, em segundos.",
    )
    args = parser.parse_args()
    if args.profile_id <= 0:
        parser.error("--profile-id precisa ser maior que zero.")
    if args.timeout <= 0:
        parser.error("--timeout precisa ser maior que zero.")
    return args


def main() -> None:
    args = parse_args()
    payload_path, ids_path, match_ids = fetch_and_save(
        profile_id=args.profile_id,
        timeout=args.timeout,
    )
    print(f"Payload da API salvo em: {payload_path}")
    print(f"IDs das partidas salvos em: {ids_path}")
    print(f"Partidas encontradas: {len(match_ids)}")


if __name__ == "__main__":
    main()
