"""CLI entry point for LegacyLens."""

import argparse
import asyncio
import sys


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="legacylens",
        description="RAG system for legacy Fortran scientific codebases",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a corpus")
    ingest_parser.add_argument(
        "--repo-url",
        required=True,
        help="Repository URL to clone",
    )
    ingest_parser.add_argument(
        "--tag",
        help="Git tag to checkout",
    )
    ingest_parser.add_argument(
        "--commit",
        help="Git commit SHA to checkout",
    )

    # Query command
    query_parser = subparsers.add_parser("query", help="Run a query")
    query_parser.add_argument("query", help="Query string")
    query_parser.add_argument(
        "--corpus-id",
        type=int,
        help="Corpus ID to query",
    )
    query_parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results to return",
    )

    # Eval command
    eval_parser = subparsers.add_parser("eval", help="Run evaluation")
    eval_parser.add_argument(
        "--gold-file",
        default="eval/gold.json",
        help="Path to gold queries file",
    )

    # Server command
    server_parser = subparsers.add_parser("server", help="Start the API server")
    server_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to",
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "ingest":
        print(f"Ingesting repository: {args.repo_url}")
        print("TODO: Implement ingestion")
        return 0

    if args.command == "query":
        print(f"Querying: {args.query}")
        print("TODO: Implement query")
        return 0

    if args.command == "eval":
        print(f"Running evaluation with: {args.gold_file}")
        print("TODO: Implement evaluation")
        return 0

    if args.command == "server":
        import uvicorn

        from legacylens.api.main import app

        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
