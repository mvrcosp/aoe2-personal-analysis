import argparse
import sys
from pathlib import Path

from parser.convert_replays_to_json import convert_replays, is_processed
from parser.download_match_replays import (
    DEFAULT_DELAY_SECONDS,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_ZIP_DIRECTORY,
    PROCESSED_DIRECTORY,
    download_pending_replays,
)
from parser.extract_replay_zips import (
    DEFAULT_REPLAY_DIRECTORY,
    extract_zip_directory,
)
from parser.fetch_recent_match_history import DEFAULT_PROFILE_ID, fetch_and_save


def run_ingestion(
    profile_id: int = DEFAULT_PROFILE_ID,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    retries: int = DEFAULT_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[int, int, list[int]]:
    payload_path, match_ids_path, match_ids = fetch_and_save(
        profile_id=profile_id,
        timeout=timeout,
    )
    print(f"Payload salvo em: {payload_path}")
    print(f"IDs salvos em: {match_ids_path}")

    downloaded, download_skipped, download_failures = download_pending_replays(
        match_ids=match_ids,
        profile_id=profile_id,
        delay_seconds=delay_seconds,
        retries=retries,
        timeout=timeout,
    )

    zip_paths = [
        DEFAULT_ZIP_DIRECTORY / f"M_{match_id}.zip"
        for match_id in match_ids
        if (DEFAULT_ZIP_DIRECTORY / f"M_{match_id}.zip").is_file()
    ]
    extracted, extraction_skipped, extraction_failures = extract_zip_directory(
        zip_paths=zip_paths,
        replay_directory=DEFAULT_REPLAY_DIRECTORY,
    )

    replay_paths = [
        DEFAULT_REPLAY_DIRECTORY / f"AgeIIDE_Replay_{match_id}.aoe2record"
        for match_id in match_ids
        if (
            DEFAULT_REPLAY_DIRECTORY / f"AgeIIDE_Replay_{match_id}.aoe2record"
        ).is_file()
    ]
    converted, conversion_skipped = convert_replays(
        replay_paths,
        destination_directory=PROCESSED_DIRECTORY,
    )

    incomplete_ids = [
        match_id
        for match_id in match_ids
        if not is_processed(
            PROCESSED_DIRECTORY / f"match_data_{match_id}.json"
        )
    ]

    print(
        "Resumo da ingestão: "
        f"{len(match_ids)} partidas consultadas; "
        f"{downloaded} ZIP(s) baixado(s), "
        f"{download_skipped} download(s) ignorado(s); "
        f"{len(download_failures)} falha(s) de download; "
        f"{extracted} replay(s) extraído(s), "
        f"{extraction_skipped} extração(ões) ignorada(s); "
        f"{len(extraction_failures)} falha(s) de extração; "
        f"{converted} JSON(s) convertido(s), "
        f"{conversion_skipped} conversão(ões) ignorada(s); "
        f"{len(incomplete_ids)} partida(s) ainda incompleta(s)."
    )

    if download_failures:
        print(
            "Falhas de download: "
            + ", ".join(str(match_id) for match_id in download_failures),
            file=sys.stderr,
        )
    if extraction_failures:
        print(
            "Falhas de extração: "
            + ", ".join(path.name for path in extraction_failures),
            file=sys.stderr,
        )
    if incomplete_ids:
        print(
            "Partidas sem JSON processado: "
            + ", ".join(str(match_id) for match_id in incomplete_ids),
            file=sys.stderr,
        )

    return len(match_ids), len(incomplete_ids), incomplete_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa a ingestão: consulta o histórico, baixa os ZIPs "
            "pendentes, extrai os replays e gera os JSONs."
        )
    )
    parser.add_argument(
        "--profile-id",
        type=int,
        default=DEFAULT_PROFILE_ID,
        help=f"ID do perfil na API (padrão: {DEFAULT_PROFILE_ID}).",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Pausa entre downloads (padrão: {DEFAULT_DELAY_SECONDS}).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Tentativas por download (padrão: {DEFAULT_RETRIES}).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout HTTP em segundos (padrão: {DEFAULT_TIMEOUT}).",
    )
    args = parser.parse_args()
    if args.profile_id <= 0:
        parser.error("--profile-id precisa ser maior que zero.")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds não pode ser negativo.")
    if args.retries < 1:
        parser.error("--retries precisa ser pelo menos 1.")
    if args.timeout <= 0:
        parser.error("--timeout precisa ser maior que zero.")
    return args


def main() -> None:
    args = parse_args()
    _, _, incomplete_ids = run_ingestion(
        profile_id=args.profile_id,
        delay_seconds=args.delay_seconds,
        retries=args.retries,
        timeout=args.timeout,
    )
    if incomplete_ids:
        raise RuntimeError(
            "A ingestão terminou com partidas pendentes: "
            + ", ".join(str(match_id) for match_id in incomplete_ids)
        )


if __name__ == "__main__":
    main()
