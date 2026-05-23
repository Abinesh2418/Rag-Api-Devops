#!/usr/bin/env python3
"""AI repair agent — reads CI test failures and writes a corrected app.py."""

import os
import sys

from openai import AzureOpenAI


def strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text


def main():
    if not os.path.exists("test_failures.txt"):
        print("No test_failures.txt found — nothing to repair.")
        sys.exit(0)

    with open("test_failures.txt") as f:
        raw = f.read()

    # Trim to the most relevant tail — the actual failure output
    failure_log = raw[-3000:] if len(raw) > 3000 else raw

    if (
        "passed" in failure_log
        and "failed" not in failure_log
        and "error" not in failure_log.lower()
    ):
        print("Tests appear to be passing — no repair needed.")
        sys.exit(0)

    with open("backend/app.py") as f:
        app_code = f.read()

    test_code = ""
    if os.path.exists("tests/test_app.py"):
        with open("tests/test_app.py") as f:
            test_code = f.read()

    conftest_code = ""
    if os.path.exists("tests/conftest.py"):
        with open("tests/conftest.py") as f:
            conftest_code = f.read()

    client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    )

    prompt = f"""You are an AI DevOps engineer performing automated CI/CD repair.

A pytest run on the main application has failed. Your task is to fix backend/app.py so all tests pass.

## Test failure output (last 3000 chars):
{failure_log}

## Current backend/app.py (the file you must fix):
{app_code}

## tests/conftest.py (read-only — understand the mocks):
{conftest_code}

## tests/test_app.py (read-only — understand what is expected):
{test_code}

Instructions:
1. Identify the exact cause of each test failure from the output above.
2. Fix ONLY the lines in backend/app.py that are causing failures.
3. Do not restructure, rename, or refactor anything unrelated to the failure.
4. Do not touch or output the test files.
5. Output the complete corrected app.py — nothing else. No markdown. No explanation."""

    print("Calling Azure OpenAI to diagnose and generate fix...")
    response = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_MODEL", "gpt-4o"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI DevOps repair agent. "
                    "Output only the complete corrected app.py file content. "
                    "No markdown code fences. No commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        timeout=60,
    )

    fixed_code = strip_code_fences(response.choices[0].message.content)

    with open("backend/app.py", "w") as f:
        f.write(fixed_code)

    print("AI fix written to backend/app.py successfully.")


if __name__ == "__main__":
    main()
