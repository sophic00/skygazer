#!/bin/bash

# --- Colors for better output ---
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_NC='\033[0m' # No Color

# --- Helper Functions ---
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${COLOR_RED}Error: Command '$1' not found. Please install it first.${COLOR_NC}"
        exit 1
    fi
}

check_git_clean() {
    if ! git diff-index --quiet HEAD --; then
        echo -e "${COLOR_RED}Error: Your Git working directory is not clean.${COLOR_NC}"
        echo "Please commit or stash your changes before running this script."
        exit 1
    fi
}

# --- Main Logic Functions ---

update_dependencies() {
    echo -e "${COLOR_BLUE}--- Starting Dependency Update ---${COLOR_NC}"
    check_git_clean
    check_command ncu

    local original_branch=$(git rev-parse --abbrev-ref HEAD)
    # FIX: Add timestamp to branch name to avoid collisions
    local dep_branch="update/deps-$(date +%Y-%m-%d-%H%M%S)"

    # FIX: Auto-detect the correct lock file
    local lock_file=""
    if [ -f "pnpm-lock.yaml" ]; then
        lock_file="pnpm-lock.yaml"
    elif [ -f "package-lock.json" ]; then
        lock_file="package-lock.json"
    elif [ -f "yarn.lock" ]; then
        lock_file="yarn.lock"
    fi

    echo "Creating a new temporary branch named '${dep_branch}'..."
    if ! git checkout -b "$dep_branch"; then
        echo -e "${COLOR_RED}Failed to create branch. Exiting.${COLOR_NC}"
        exit 1
    fi

    echo -e "\n${COLOR_YELLOW}Step 1: Updating PATCH versions...${COLOR_NC}"
    if ncu --target patch -u && pnpm install; then
        echo "Staging patch updates..."
        git add package.json ${lock_file}
        git commit -m "chore(deps): update patch dependencies"
        echo -e "${COLOR_GREEN}Patch dependencies updated and committed.${COLOR_NC}"
    else
        echo "No patch updates to apply or install failed."
    fi


    echo -e "\n${COLOR_YELLOW}Step 2: Checking for MINOR updates...${COLOR_NC}"
    if ncu --target minor | grep -q 'dependencies'; then
        read -p "Minor updates found. Do you want to apply them now? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if ncu --target minor -u && pnpm install; then
                echo "Please test your site now (e.g., 'pnpm run dev') to ensure nothing broke."
                read -p "Press [Enter] to commit the minor updates..."
                git add package.json ${lock_file}
                git commit -m "chore(deps): update minor dependencies"
                echo -e "${COLOR_GREEN}Minor dependencies updated and committed.${COLOR_NC}"
            else
                echo -e "${COLOR_RED}Minor update or install failed.${COLOR_NC}"
            fi
        else
            echo "Skipping minor updates. You can review them manually with 'ncu --target minor'."
        fi
    else
        echo "No minor updates to apply."
    fi

    # FEATURE: Automatically merge back and clean up the branch
    echo -e "\n${COLOR_BLUE}Merging changes back to '${original_branch}' and cleaning up...${COLOR_NC}"
    git checkout "$original_branch"
    if git merge --no-ff "$dep_branch"; then
        git branch -d "$dep_branch"
        echo -e "${COLOR_GREEN}Automated updates merged successfully and temporary branch deleted.${COLOR_NC}"
    else
        echo -e "${COLOR_RED}Merge failed! Please resolve conflicts manually on branch '${original_branch}'.${COLOR_NC}"
        echo -e "${COLOR_YELLOW}The temporary branch '${dep_branch}' has been kept for inspection.${COLOR_NC}"
    fi


    echo -e "\n${COLOR_YELLOW}Step 3: Checking for MAJOR updates...${COLOR_NC}"
    echo "Major updates require careful manual review and migration."
    echo "The following major updates are available:"
    ncu --target latest --format group
    echo -e "\n${COLOR_YELLOW}ACTION REQUIRED:${COLOR_NC} Please update major versions one by one in a new branch, read the changelogs, and test thoroughly."

    echo -e "\n${COLOR_GREEN}Dependency check complete.${COLOR_NC}"
}

update_template() {
    echo -e "${COLOR_BLUE}--- Starting AstroPaper Template Update ---${COLOR_NC}"
    check_git_clean

    local remote_name="astro-paper"
    local remote_url="https://github.com/satnaing/astro-paper.git"

    if ! git remote -v | grep -q "^${remote_name}"; then
        echo "Adding '${remote_name}' as a Git remote..."
        git remote add "$remote_name" "$remote_url"
    fi

    echo "Fetching the latest changes from the AstroPaper template..."
    git fetch "$remote_name"

    local original_branch=$(git rev-parse --abbrev-ref HEAD)
    # FIX: Add timestamp to branch name to avoid collisions
    local template_branch="update/astro-paper-template-$(date +%Y-%m-%d-%H%M%S)"

    echo "Creating a new branch named '${template_branch}'..."
    git checkout -b "$template_branch"

    echo -e "\n${COLOR_RED}IMPORTANT: Merging the template can cause significant conflicts, especially with heavy customizations.${COLOR_NC}"
    read -p "Are you sure you want to proceed with merging 'astro-paper/main'? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting template merge."
        git checkout "$original_branch"
        git branch -D "$template_branch"
        exit 0
    fi

    echo "Attempting to merge from '${remote_name}/main'..."
    if ! git merge --no-commit "${remote_name}/main" --allow-unrelated-histories; then
        echo -e "\n${COLOR_YELLOW}MERGE CONFLICTS DETECTED!${COLOR_NC}"
        echo "Your project has diverged from the template, which is expected."
        echo -e "\n${COLOR_YELLOW}ACTION REQUIRED:${COLOR_NC}"
        echo "1. Open your editor and resolve all merge conflicts (check 'git status')."
        echo "2. After resolving, stage and commit the changes."
        echo "3. Test your site thoroughly ('pnpm run dev', 'pnpm run build')."
        # FEATURE: Improved instructions for cleanup
        echo -e "\n${COLOR_BLUE}Once you have committed the resolved conflicts on this branch, run these commands to finish:${COLOR_NC}"
        echo -e "  git checkout ${original_branch}"
        echo -e "  git merge --no-ff ${template_branch}"
        echo -e "  git branch -d ${template_branch}"

    else
        echo -e "${COLOR_GREEN}Merge was successful with no conflicts.${COLOR_NC}"
        echo "Please commit the result now and test your site thoroughly."
        echo -e "\n${COLOR_BLUE}After committing on this branch, run these commands to finish:${COLOR_NC}"
        echo -e "  git checkout ${original_branch}"
        echo -e "  git merge --no-ff ${template_branch}"
        echo -e "  git branch -d ${template_branch}"
    fi

    echo -e "\nUpdate process paused. You are on branch '${template_branch}'."
}

# --- Script Entry Point ---
check_command git
check_command pnpm

echo "Select the update process to run:"
echo "  1) Update Dependencies"
echo "  2) Update AstroPaper Template"
read -p "Enter choice [1-2]: " choice

case $choice in
    1)
        update_dependencies
        ;;
    2)
        update_template
        ;;
    *)
        echo -e "${COLOR_RED}Invalid choice. Exiting.${COLOR_NC}"
        exit 1
        ;;
esac
