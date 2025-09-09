#!/usr/bin/env python3
import sys
import subprocess
import json
import base64
import argparse
import io
from ruamel.yaml import YAML
from typing import Optional, Tuple
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

def get_section_from_content(content: str, section: str) -> Optional[str]:
    """
    Extracts a section's value from a string containing the file content.
    """
    if not content:
        return None

    lines = content.splitlines()
    found_ranges = find_section_lines(lines, section)
 
    if found_ranges:
        start, end = found_ranges[0]
        section_content = lines[start : end + 1]
        return '\n'.join(section_content)

    return None

def get_pr_shas(owner: str, repo: str, pr_number: int) -> Tuple[str, str]:
    """
    Fetches the base and head commit SHAs for a PR.
    """
    gh_pr_command = [
        "gh", "pr", "view", str(pr_number),
        "--repo", f"{owner}/{repo}",
        "--json", "baseRefOid,headRefOid"
    ]
    returncode, stdout, stderr = run_command(gh_pr_command)

    if returncode != 0:
        raise RuntimeError(f"Failed to get PR details. GitHub CLI stderr: {stderr.strip()}")

    try:
        shas = json.loads(stdout)
        base_sha = shas['baseRefOid']
        head_sha = shas['headRefOid']
        return base_sha, head_sha
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Could not parse commit SHAs from API response. Error: {e}") from e

def get_value_from_commit(owner: str, repo: str, file_path: str, key: str, sha: str) -> Optional[str]:
    """
    Fetches a file from a specific commit and extracts the value of a given key.

    Args:
        owner: The repository owner.
        repo: The repository name.
        file_path: The path to the file within the repository.
        key: The key/section to extract from the file's content.
        sha: The commit SHA from which to retrieve the file.

    Returns:
        The extracted value as a string, or None if the file or key is not found.
    """
    # 1. Fetch the file's content for the given commit SHA.
    content = get_file_content_from_pr(owner, repo, sha, file_path)

    # 2. Parse the content to get the desired value.
    value = get_section_from_content(content, key)

    return value



def main():
    """Main function to fetch PR files, parse them, and compare keys."""
    parser = argparse.ArgumentParser(
        description="Compare specific keys in a YAML file between a PR's base and head branches."
    )
    parser.add_argument("--owner", required=True, help="The owner of the repository.")
    parser.add_argument("--repo", required=True, help="The name of the repository.")
    parser.add_argument("pr_number", type=int, help="The Pull Request number.")
    parser.add_argument("file_path", type=str, help="The file path within the repository.")
    parser.add_argument("key", type=str, help="The key will be checked.")

    args = parser.parse_args()

    print(f"--- Analyzing '{args.file_path}' in PR #{args.pr_number} for key: {args.key} ---")
    print(f"Repository: {args.owner}/{args.repo}")

    # 1. Get the base and head commit SHAs.
    base_sha, head_sha = get_pr_shas(args.owner, args.repo, args.pr_number)

    # 2. Fetch and parse the values of the key from the base and head commits.
    before_value = get_value_from_commit(
    args.owner, args.repo, args.file_path, args.key, base_sha
    )
    after_value = get_value_from_commit(
    args.owner, args.repo, args.file_path, args.key, head_sha
    )

    # 3. Compare the results and print the final output.
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
