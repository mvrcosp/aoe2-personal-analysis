import argparse
import json
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent.parent
MATCH_IDS_DIRECTORY = PROJECT_DIR / "data" / "raw" / "api" / "matchIDs"
DEFAULT_ZIP_DIRECTORY = PROJECT_DIR / "data" / "raw" / "zip"
PROCESSED_DIRECTORY = PROJECT_DIR / "data" / "processed" / "aoe2rec"
DEFAULT_TIMEOUT = 60
DEFAULT_DELAY_SECONDS = 2.0
DEFAULT_RETRIES = 3
RETRYABLE_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}


class InvalidMatchIdsFileError(ValueError):
    pass


def find_latest_match_ids_file(directory: Path = MATCH_IDS_DIRECTORY) -> Path:
    files = sorted(directory.glob("matchIDs_match_history_*.json"))
    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo matchIDs_match_history_*.json encontrado em {directory}."
        )
    return files[-1]


def load_match_ids(path: Path) -> tuple[int, list[int]]:
    with path.open(encoding="utf-8") as json_file:
        data: Any = json.load(json_file)

    if not isinstance(data, dict):
        raise InvalidMatchIdsFileError("O JSON de IDs precisa ser um objeto.")

    profile_id = data.get("profile_id")
    if not isinstance(profile_id, int) or isinstance(profile_id, bool) or profile_id <= 0:
        raise InvalidMatchIdsFileError(
            "O JSON precisa conter um profile_id inteiro e positivo."
        )

    match_ids = data.get("match_ids")
    if not isinstance(match_ids, list):
        raise InvalidMatchIdsFileError("O JSON precisa conter a lista match_ids.")

    unique_ids = []
    seen_ids = set()
    for index, match_id in enumerate(match_ids):
        if (
            not isinstance(match_id, int)
            or isinstance(match_id, bool)
            or match_id <= 0
        ):
            raise InvalidMatchIdsFileError(
                f"ID de partida inválido na posição {index}: {match_id!r}."
            )
        if match_id not in seen_ids:
            seen_ids.add(match_id)
            unique_ids.append(match_id)

    return profile_id, unique_ids


def is_processed(match_id: int, processed_directory: Path) -> bool:
    json_path = processed_directory / f"match_data_{match_id}.json"
    if not json_path.is_file():
        return False

    try:
        with json_path.open(encoding="utf-8") as json_file:
            json.load(json_file)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        print(
            f"JSON processado inválido para a partida {match_id}; "
            f"o replay será baixado novamente: {error}",
            file=sys.stderr,
        )
        return False
    return True


def validate_replay_zip(zip_path: Path, match_id: int) -> None:
    expected_name = f"AgeIIDE_Replay_{match_id}.aoe2record"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("o ZIP contém um membro com CRC inválido")
            replay_members = [
                member
                for member in archive.infolist()
                if member.filename == expected_name and not member.is_dir()
            ]
            if len(replay_members) != 1:
                raise ValueError(
                    f"o ZIP não contém exatamente um arquivo {expected_name}"
                )
    except zipfile.BadZipFile as error:
        raise ValueError("a resposta recebida não é um ZIP válido") from error


def download_replay_zip(
    match_id: int,
    profile_id: int,
    zip_directory: Path,
    timeout: float,
) -> Path:
    zip_directory.mkdir(parents=True, exist_ok=True)
    zip_path = zip_directory / f"M_{match_id}.zip"
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=zip_directory,
            prefix=f".M_{match_id}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

        query = urlencode(
            {
                "gameId": match_id,
                "profileId": profile_id,
            }
        )
        request = Request(
            f"https://aoe.ms/replay/?{query}",
            headers={"User-Agent": "aoe2-personal-analysis"},
        )
        with urlopen(request, timeout=timeout) as response:
            with temporary_path.open("wb") as output_file:
                shutil.copyfileobj(response, output_file)

        validate_replay_zip(temporary_path, match_id)
        temporary_path.replace(zip_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return zip_path


def download_pending_replays(
    match_ids: list[int],
    profile_id: int,
    zip_directory: Path = DEFAULT_ZIP_DIRECTORY,
    processed_directory: Path = PROCESSED_DIRECTORY,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    retries: int = DEFAULT_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, int, list[int]]:
    downloaded = 0
    skipped = 0
    failed_match_ids = []
    made_request = False

    for match_id in match_ids:
        if is_processed(match_id, processed_directory):
            skipped += 1
            print(f"Partida {match_id}: já processada; download ignorado.")
            continue

        existing_zip = zip_directory / f"M_{match_id}.zip"
        if existing_zip.is_file():
            try:
                validate_replay_zip(existing_zip, match_id)
            except (OSError, ValueError) as error:
                print(
                    f"ZIP existente para a partida {match_id} é inválido "
                    f"e será baixado novamente: {error}",
                    file=sys.stderr,
                )
            else:
                skipped += 1
                print(
                    f"Partida {match_id}: ZIP já existe e é válido; "
                    "download ignorado."
                )
                continue

        for attempt in range(1, retries + 1):
            if made_request:
                wait_seconds = delay_seconds
                if attempt > 1:
                    wait_seconds *= 2 ** (attempt - 2)
                time.sleep(wait_seconds)

            try:
                zip_path = download_replay_zip(
                    match_id=match_id,
                    profile_id=profile_id,
                    zip_directory=zip_directory,
                    timeout=timeout,
                )
            except HTTPError as error:
                made_request = True
                retryable = error.code in RETRYABLE_HTTP_STATUSES
                message = f"HTTP {error.code}: {error.reason}"
                if retryable and attempt < retries:
                    print(
                        f"Partida {match_id}: {message}; nova tentativa "
                        f"{attempt + 1}/{retries}.",
                        file=sys.stderr,
                    )
                    continue
                failed_match_ids.append(match_id)
                print(f"Partida {match_id}: download falhou ({message}).", file=sys.stderr)
                break
            except (URLError, TimeoutError, OSError, ValueError) as error:
                made_request = True
                if attempt < retries:
                    print(
                        f"Partida {match_id}: {error}; nova tentativa "
                        f"{attempt + 1}/{retries}.",
                        file=sys.stderr,
                    )
                    continue
                failed_match_ids.append(match_id)
                print(
                    f"Partida {match_id}: download falhou após {retries} "
                    f"tentativa(s): {error}.",
                    file=sys.stderr,
                )
                break

            made_request = True
            downloaded += 1
            print(f"Partida {match_id}: ZIP salvo em {zip_path}.")
            break

    return downloaded, skipped, failed_match_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa os ZIPs das partidas ainda não processadas listadas "
            "no JSON de matchIDs."
        )
    )
    parser.add_argument(
        "--match-ids",
        type=Path,
        help=(
            "JSON de IDs. Se omitido, usa o arquivo mais recente em "
            f"{MATCH_IDS_DIRECTORY}."
        ),
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Pausa mínima entre requisições (padrão: {DEFAULT_DELAY_SECONDS}).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Número máximo de tentativas por partida (padrão: {DEFAULT_RETRIES}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout da requisição em segundos (padrão: {DEFAULT_TIMEOUT}).",
    )
    args = parser.parse_args()
    if args.delay_seconds < 0:
        parser.error("--delay-seconds não pode ser negativo.")
    if args.retries < 1:
        parser.error("--retries precisa ser pelo menos 1.")
    if args.timeout <= 0:
        parser.error("--timeout precisa ser maior que zero.")
    return args


def main() -> None:
    args = parse_args()
    match_ids_file = args.match_ids or find_latest_match_ids_file()
    profile_id, match_ids = load_match_ids(match_ids_file)
    print(f"IDs carregados de: {match_ids_file}")
    print(f"Partidas encontradas no arquivo: {len(match_ids)}")

    downloaded, skipped, failed_match_ids = download_pending_replays(
        match_ids=match_ids,
        profile_id=profile_id,
        delay_seconds=args.delay_seconds,
        retries=args.retries,
        timeout=args.timeout,
    )
    print(
        f"Resumo: {downloaded} ZIP(s) baixado(s), "
        f"{skipped} partida(s) já processada(s), "
        f"{len(failed_match_ids)} falha(s)."
    )
    if failed_match_ids:
        raise RuntimeError(
            "Falha no download dos match IDs: "
            + ", ".join(str(match_id) for match_id in failed_match_ids)
        )


if __name__ == "__main__":
    main()
