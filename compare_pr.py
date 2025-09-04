import sys
import subprocess
import json
import base64
import argparse
import io
from ruamel.yaml import YAML
from typing import Optional

def run_command(command: list[str]) -> tuple[int, str, str]:
    """Runs a shell command and returns its exit code, stdout, and stderr."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr

def get_file_content_from_pr(owner: str, repo: str, sha: str, file_path: str) -> str:
    """Fetches file content for a given commit SHA using the GitHub API."""
    api_path = f"/repos/{owner}/{repo}/contents/{file_path}?ref={sha}"
    print(f"-> Fetching file content for '{file_path}' from commit {sha[:7]}...")
    
    returncode, stdout, stderr = run_command(["gh", "api", api_path])
    
    if returncode != 0:
        print(f"   - Warning: Could not fetch file. It may be new or deleted. (stderr: {stderr.strip()})")
        return ""
        
    try:
        content_json = json.loads(stdout)
        encoded_content = content_json.get('content', '')
        if not encoded_content:
            return ""
        
        return base64.b64decode(encoded_content).decode('utf-8')
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"   - Warning: Could not parse or decode content. Error: {e}", file=sys.stderr)
        return ""

def parse_yaml_and_get_keys(content: str, keys_to_find: list[str]) -> Optional[str]:
    """
    Parses a YAML content string, cleans it, and finds the value of the first
    matching key from the provided list.
    """
    yaml = YAML(typ='safe')
    
    # Pre-process content to remove invalid lines (e.g., '{{{...}}}')
    lines = content.splitlines()
    clean_lines = [line for line in lines if not line.strip().startswith('{{{')]
    cleaned_content = "\n".join(clean_lines)
    
    if not cleaned_content.strip():
        return None
            
    try:
        data = yaml.load(cleaned_content)
        if not isinstance(data, dict):
            return None
    except Exception as e:
        print(f"   - Warning: Could not parse YAML content. Error: {e}", file=sys.stderr)
        return None

    found_value = None
    for key in keys_to_find:
        if key in data:
            found_value = data.get(key)
            break
    
    if found_value is None:
        return None

    # For consistent comparison, convert complex types (lists/dicts) back to a YAML string
    if isinstance(found_value, (dict, list)):
        string_stream = io.StringIO()
        yaml.dump(found_value, string_stream)
        return string_stream.getvalue().strip()
    
    return str(found_value)

def main():
    """Main function to fetch PR files, parse them, and compare keys."""
    parser = argparse.ArgumentParser(
        description="Compare specific keys in a YAML file between a PR's base and head branches."
    )
    parser.add_argument("--owner", required=True, help="The owner of the repository (organization or user).")
    parser.add_argument("--repo", required=True, help="The name of the repository.")
    parser.add_argument("pr_number", type=int, help="The Pull Request number.")
    parser.add_argument("file_path", type=str, help="The full path to the file within the repository.")
    parser.add_argument("keys", nargs='+', help="One or more keys to check in order (e.g., description options).")
    args = parser.parse_args()

    print(f"--- Analyzing '{args.file_path}' in PR #{args.pr_number} for keys: {args.keys} ---")
    print(f"Repository: {args.owner}/{args.repo}")


    # 1. Get the base and head commit SHAs.
    gh_pr_command = [
        "gh", "pr", "view", str(args.pr_number), "--repo", f"{args.owner}/{args.repo}", "--json", "baseRefOid,headRefOid"
    ]
    returncode, stdout, stderr = run_command(gh_pr_command)

    if returncode != 0:
        print(f"\nError: Failed to get PR details. gh stderr: {stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    try:
        shas = json.loads(stdout)
        base_sha = shas['baseRefOid']
        head_sha = shas['headRefOid']
        print(f"Base SHA (Before): {base_sha}")
        print(f"Head SHA (After):  {head_sha}\n")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"\nError: Could not parse commit SHAs. Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Fetch file content for both commits.
    before_content = get_file_content_from_pr(args.owner, args.repo, base_sha, args.file_path)
    after_content = get_file_content_from_pr(args.owner, args.repo, head_sha, args.file_path)

    # 3. Parse the content in memory to get the desired values.
    before_value = parse_yaml_and_get_keys(before_content, args.keys)
    after_value = parse_yaml_and_get_keys(after_content, args.keys)

    # 4. Compare the results and print the final output.
    print("\n--- Comparison Result ---")
    print(f"Value in base branch:  {before_value}")
    print(f"Value in PR branch:    {after_value}")

    if before_value == after_value:
        print("\n✅ No changes detected for the specified keys.")
        print("\nrule_updated=false")
    else:
        print("\n❗️ Change detected for one of the specified keys!")
        # This output can be redirected to GITHUB_ENV in a GitHub Action
        print("\nrule_updated=true")

if __name__ == "__main__":
    main()
