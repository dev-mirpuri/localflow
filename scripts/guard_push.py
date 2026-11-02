"""Pre-push guard: refuse any push whose remote ref is main.

Git passes one line per pushed ref on stdin:
    <local ref> <local sha> <remote ref> <remote sha>
"""

import sys

PROTECTED_REF = "refs/heads/main"


def main() -> None:
    for line in sys.stdin:
        fields = line.split()
        if len(fields) == 4 and fields[2] == PROTECTED_REF:
            sys.exit(
                f"guard_push: refusing to push {fields[0]} to {PROTECTED_REF}. "
                "Push to dev or a ticket branch, then open a pull request."
            )


if __name__ == "__main__":
    main()
