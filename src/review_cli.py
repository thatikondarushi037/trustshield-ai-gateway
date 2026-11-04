
import argparse

from src.review_queue import (
    list_reviews,
    resolve_review,
)


def main():
    parser = argparse.ArgumentParser(
        description="TrustShield local review manager"
    )

    parser.add_argument(
        "action",
        choices=["list", "reject", "rewrite"]
    )

    parser.add_argument(
        "--id",
        help="Review ticket ID"
    )

    args = parser.parse_args()

    if args.action == "list":
        reviews = list_reviews()

        if not reviews:
            print("No pending reviews.")

        for review in reviews:
            print(
                f"ID: {review['id']} | "
                f"Status: {review['status']} | "
                f"Created: {review['created_at']}"
            )

    else:
        if not args.id:
            parser.error("--id is required")

        outcome = (
            "REJECTED"
            if args.action == "reject"
            else "REWRITE_REQUESTED"
        )

        success = resolve_review(
            args.id,
            outcome
        )

        if success:
            print(f"Review resolved: {outcome}")
        else:
            print("Review not found or already resolved.")


if __name__ == "__main__":
    main()
