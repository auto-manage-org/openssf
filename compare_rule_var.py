#!/usr/bin/env python3
import sys
import subprocess
import json
import base64
import argparse
import io
from ruamel.yaml import YAML
from typing import Optional
from collections import namedtuple


def run_command(command: list[str]) -> tuple[int, str, str]:
    """Runs a shell command and returns its exit code, stdout, and stderr."""
    res = subprocess.run(command, capture_output=True, text=True, check=False)
    return res.returncode, res.stdout, res.stderr


def get_file_content_from_pr(owner: str, repo: str, sha: str, file_path: str) -> str:
    """Fetches file content for a given commit SHA using the GitHub API.
    The base64 encoding and decoding step is necessary because of how the
    GitHub API is designed to transmit file content.
    """
    api_path = f"/repos/{owner}/{repo}/contents/{file_path}?ref={sha}"
    print(f"-> Fetching file content for '{file_path}' from commit {sha[:7]}...")
    returncode, stdout, stderr = run_command(["gh", "api", api_path])

    if returncode != 0:
        print(f"Exception: Could not fetch file. It may be new or deleted. "
              f"(stderr: {stderr.strip()})")
        return ""

    try:
        content_json = json.loads(stdout)
        encoded_content = content_json.get('content', '')
        if not encoded_content:
            return ""

        return base64.b64decode(encoded_content).decode('utf-8')
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Exception: Could not parse or decode content. Error: {e}", file=sys.stderr)
        return ""

def find_section_lines(file_contents, sec):
    """
    Parses the given file_contents as YAML to find the section with the given identifier.

    Note that this does not call into the yaml library and thus correctly handles Jinja macros at
    the expense of not being a strictly valid yaml parsing.

    Args:
        file_contents (list of str): The contents of the file, split into lines.
        sec (str): The identifier of the section to find.

    Returns:
        list of namedtuple: A list of namedtuples (start, end) representing the lines where the
                            section exists.
    """
    # Hack to find a global key ("section"/sec) in a YAML-like file.
    # All indented lines until the next global key are included in the range.
    # For example:
    #
    # 0: not_it:
    # 1:     - value
    # 2: this_one:
    # 3:      - 2
    # 4:      - 5
    # 5:
    # 6: nor_this:
    #
    # for the section "this_one", the result [(2, 5)] will be returned.
    # Note that multiple sections may exist in a file and each will be
    # identified and returned.
    section = namedtuple('section', ['start', 'end'])

    sec_ranges = []
    sec_id = sec + ":"
    sec_len = len(sec_id)
    end_num = len(file_contents)
    line_num = 0

    while line_num < end_num:
        if len(file_contents[line_num]) >= sec_len:
            if file_contents[line_num][0:sec_len] == sec_id:
                begin = line_num
                line_num += 1
                while line_num < end_num:
                    nonempty_line = file_contents[line_num]
                    if nonempty_line and file_contents[line_num][0] != ' ':
                        break
                    line_num += 1

                end = line_num - 1
                sec_ranges.append(section(begin, end))
        line_num += 1

    return sec_ranges

def get_section_value(yml_file: str, keys_to_find: list[str]) -> Optional[str]:
    sections_value = {}
    try:
        with open(yml_file, 'r') as f:
            lines = [line.rstrip() for line in f.readlines()]
        for section in keys_to_find:
            found_ranges = find_section_lines(lines, section)
            for start, end in found_ranges:
                print(f"\nFound a section from line {start} to {end}:")
                # Slice the list to get the content. Add 1 to `end` because Python slicing is exclusive.
                section_content = lines[start : end + 1]
                value = '\n'.join(section_content)
                sections_value[section] = value
        string_stream = io.StringIO()
        yaml.dump(sections_value, string_stream)
        return string_stream.getvalue().strip()

    except FileNotFoundError:
        print(f"ERROR: The file '{yml_file}' was not found.", file=sys.stderr)
        sys.exit(0)

def main():
    """Main function to fetch PR files, parse them, and compare keys."""
    parser = argparse.ArgumentParser(
        description="Compare specific keys in a YAML file between a PR's base and head branches."
    )
    parser.add_argument("--owner", required=True, help="The owner of the repository.")
    parser.add_argument("--repo", required=True, help="The name of the repository.")
    parser.add_argument("pr_number", type=int, help="The Pull Request number.")
    parser.add_argument("file_path", type=str, help="The file path within the repository.")
    parser.add_argument(
        "keys",
        nargs='+',
        help="One or more keys to check in order "
             "(e.g., description options)."
    )

    args = parser.parse_args()

    print(f"--- Analyzing '{args.file_path}' in PR #{args.pr_number} for keys: {args.keys} ---")
    print(f"Repository: {args.owner}/{args.repo}")

    # 1. Get the base and head commit SHAs.
    gh_pr_command = [
        "gh", "pr", "view", str(args.pr_number),
        "--repo", f"{args.owner}/{args.repo}",
        "--json", "baseRefOid,headRefOid"
    ]
    returncode, stdout, stderr = run_command(gh_pr_command)

    if returncode != 0:
        print(
            f"\nException: Failed to get PR details. "
            f"gh stderr: {stderr.strip()}",
            file=sys.stderr
        )

        sys.exit(0)
    try:
        shas = json.loads(stdout)
        base_sha = shas['baseRefOid']
        head_sha = shas['headRefOid']
        print(f"Base SHA (Before): {base_sha}")
        print(f"Head SHA (After):  {head_sha}\n")
    except (json.JSONDecodeError, KeyError) as e:
        print(
            f"\nException: Could not parse commit SHAs. "
            f"Error: {e}",
            file=sys.stderr
        )

        sys.exit(0)

    # 2. Fetch file content for both commits.
    before_content = get_file_content_from_pr(
        args.owner, args.repo, base_sha, args.file_path
    )
    print(before_content)
    after_content = get_file_content_from_pr(
        args.owner, args.repo, head_sha, args.file_path
    )
    print(after_content)

    # 3. Parse the content in memory to get the desired values.
    before_value = get_section_value(before_content, args.keys)
    after_value = get_section_value(after_content, args.keys)
    print(before_value)
    print(after_value)

    # 4. Compare the results and print the final output.
    print("\n--- Comparison Result ---")
    print(f"Value(s) in base branch:\n---\n{before_value}\n---")
    print(f"Value(s) in PR branch:\n---\n{after_value}\n---")

    if before_value == after_value:
        print("\nNo changes detected for the specified keys.")
        sys.exit(0)
    else:
        print("\nChange detected for one of the specified keys!")
        print("\nCHANGE_FOUND=true")
        sys.exit(1)


if __name__ == "__main__":
    main()
