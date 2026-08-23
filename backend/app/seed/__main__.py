"""Entry point: python -m app.seed [--project-count N]"""

import argparse
import asyncio

from app.seed.runner import run_seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed business domain data")
    parser.add_argument(
        "--project-count",
        type=int,
        default=10,
        choices=range(8, 13),
        metavar="[8-12]",
        help="Number of projects to generate (default: 10, range: 8-12)",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(project_count=args.project_count))


if __name__ == "__main__":
    main()
