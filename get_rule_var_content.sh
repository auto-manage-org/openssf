# Set variables for convenience
PR_NUMBER=63
OWNER="auto-manage-org"
REPO="openssf"

# Get the commit SHAs
SHAS=$(gh pr view $PR_NUMBER --repo "$OWNER/$REPO" --json baseRefOid,headRefOid)
BASE_SHA=$(echo $SHAS | jq -r '.baseRefOid')
HEAD_SHA=$(echo $SHAS | jq -r '.headRefOid')

echo "Base SHA (Before): $BASE_SHA"
echo "Head SHA (After):  $HEAD_SHA"

# Set the path to your YAML file
FILE_PATH="rule.yml"

# Fetch the 'before' content (from the base branch)
BEFORE_CONTENT=$(gh api "/repos/$OWNER/$REPO/contents/$FILE_PATH?ref=$BASE_SHA" --jq '.content' | base64 --decode)

# Fetch the 'after' content (from the PR's head branch)
AFTER_CONTENT=$(gh api "/repos/$OWNER/$REPO/contents/$FILE_PATH?ref=$HEAD_SHA" --jq '.content' | base64 --decode)

echo "$BEFORE_CONTENT" > file1.yml
echo "$AFTER_CONTENT" > file2.yml


