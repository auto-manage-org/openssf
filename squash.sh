#!/bin/bash

# squash_commits.sh
# This script automates squashing the latest N Git commits into a single one.
# It automatically keeps the oldest commit's message and pushes the result.
# It uses `git rebase -i` and automates the interactive part using GIT_SEQUENCE_EDITOR.

# Usage:
# sh squash_commits.sh $number_of_commits_to_squash


echo "Starting Git Commit Squasher Script..."
echo $(git status)
# Check for a clean working directory
if [[ -n $(git status --porcelain) ]]; then
  echo "Error: Your working directory is not clean."
  echo "Please commit or stash your changes before attempting to squash commits."
  exit 1
fi

# Determine the rebase range and ensure it's always 'fixup' type
SQUASH_TYPE="fixup" # Always keep only the oldest commit message
REBASE_RANGE=""
NUM_COMMITS_TO_SQUASH=0 # Used for validation

# Parse command line arguments - expecting only one numeric argument
if [[ $# -ne 1 ]]; then
  echo "Error: Incorrect number of arguments."
  usage
fi

if ! [[ "$1" =~ ^[0-9]+$ ]]; then
  echo "Error: Argument must be a positive integer representing the number of commits."
fi

NUM_COMMITS_TO_SQUASH=$1

if [[ $NUM_COMMITS_TO_SQUASH -le 1 ]]; then
  echo "Nothing to squash. You need at least 2 commits to perform a squash operation."
  exit 0
fi

REBASE_RANGE="HEAD~$NUM_COMMITS_TO_SQUASH"

echo "Attempting to rebase using range: $REBASE_RANGE"
echo "Commits will be combined using '$SQUASH_TYPE' mode (keeping oldest commit message)."

# Set GIT_SEQUENCE_EDITOR to automate the interactive rebase process.
# This sed command works as follows:
# 1. `1s/^pick/pick/g`: On the first line (the oldest commit in the range), ensure it's 'pick'.
#    This effectively makes no change but ensures the first commit is picked as the base.
# 2. `2,\$s/^pick/'$SQUASH_TYPE'/g`: From the second line to the last line,
#    replace 'pick' with the chosen SQUASH_TYPE ('fixup' in this simplified script).
#    This changes all subsequent commits in the sequence to be fixed up into the first.
# `.bak` creates a backup file of the rebase-todo list, which can be useful for debugging.
export GIT_SEQUENCE_EDITOR="sed -i.bak '1s/^pick/pick/g; 2,\$s/^pick/$SQUASH_TYPE/g'"

# Execute the interactive rebase
echo "Running git rebase -i $REBASE_RANGE..."
git rebase -i "$REBASE_RANGE"

# Store the exit status of the rebase command
REBASE_STATUS=$?

# Check the exit status of the git rebase command
if [[] $REBASE_STATUS -ne 0 ]]; then
  echo ""
  echo "---------------------------------------------------------"
  echo "Git rebase failed. This often means there were conflicts."
  echo "Please resolve the conflicts manually by editing the conflicted files,"
  echo "then run 'git add .' and 'git rebase --continue'."
  echo "To abort the rebase and return to the previous state, run 'git rebase --abort'."
  echo "---------------------------------------------------------"
  exit 1
else
  echo ""
  echo "---------------------------------------------------------"
  echo "Successfully squashed commits into a single commit."
  echo "The new commit is: $(git log -1 --oneline)"
  echo ""

  echo "Attempting to push changes to remote..."
  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  # Get upstream remote and branch if it exists, otherwise default to 'origin' and current branch
  UPSTREAM_INFO=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null)
  if [ -n "$UPSTREAM_INFO" ]; then
    UPSTREAM_REMOTE="${UPSTREAM_INFO%%/*}"
    UPSTREAM_BRANCH="${UPSTREAM_INFO#*/}"
  else
    UPSTREAM_REMOTE="origin"
    UPSTREAM_BRANCH="$CURRENT_BRANCH"
  fi

  echo "Pushing to $UPSTREAM_REMOTE/$UPSTREAM_BRANCH..."
  git push "$UPSTREAM_REMOTE" "$CURRENT_BRANCH" --force-with-lease

  if [[ $? -ne 0 ]]; then
    echo "Error: Git push failed. Please check your permissions and connectivity."
    echo "You may need to run 'git push --force-with-lease' manually."
  else
    echo "Successfully pushed squashed commits to remote."
  fi
  echo "---------------------------------------------------------"
fi

# Clean up the backup file created by sed (optional)
rm -f "$(git rev-parse --git-dir)/rebase-merge/git-rebase-todo.bak"

echo "Squash script finished."