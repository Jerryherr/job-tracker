"""
One-time setup: initialize git repo and push to GitHub.
Run this once from the job-tracker directory.

Prerequisites:
  1. Install GitHub CLI:   winget install GitHub.cli
  2. Login to GitHub CLI:  gh auth login
  3. Have ANTHROPIC_API_KEY ready
"""

import subprocess
import sys
import os


def run(cmd, check=True, capture=False):
    print(f"  > {cmd}")
    r = subprocess.run(cmd, shell=True, check=check,
                       capture_output=capture, text=True)
    if capture:
        return r.stdout.strip()
    return r


def main():
    print("=" * 60)
    print("Job Tracker — GitHub Setup")
    print("=" * 60)

    # 1. Check gh CLI
    r = subprocess.run("gh --version", shell=True, capture_output=True)
    if r.returncode != 0:
        print("\nERROR: GitHub CLI not found.")
        print("Install it: winget install GitHub.cli")
        print("Then login:  gh auth login")
        sys.exit(1)

    r = subprocess.run("gh auth status", shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("\nNot logged in to GitHub. Run: gh auth login")
        sys.exit(1)

    # 2. Get GitHub username
    username = run("gh api user --jq .login", capture=True)
    print(f"\nLogged in as: {username}")

    # 3. Repo name
    repo_name = input("\nGitHub repo name [job-tracker]: ").strip() or "job-tracker"
    repo_full = f"{username}/{repo_name}"

    # 4. Init git if needed
    if not os.path.exists(".git"):
        run("git init -b main")

    # 5. Create GitHub repo (public for free GitHub Pages)
    visibility = input("Public or private repo? [public/private] (public recommended for free Pages): ").strip() or "public"
    run(f'gh repo create {repo_name} --{visibility} --source=. --remote=origin --push', check=False)

    # If repo already exists, just set remote and push
    r = subprocess.run("git remote get-url origin", shell=True, capture_output=True)
    if r.returncode != 0:
        run(f"gh repo create {repo_name} --{visibility}")
        run(f"git remote add origin https://github.com/{repo_full}.git")

    # 6. Set ANTHROPIC_API_KEY secret
    api_key = input("\nPaste your ANTHROPIC_API_KEY (or press Enter to skip): ").strip()
    if api_key:
        # Write to temp file to avoid shell escaping issues
        with open(".tmp_key", "w") as f:
            f.write(api_key)
        run(f"gh secret set ANTHROPIC_API_KEY --repo {repo_full} < .tmp_key")
        os.remove(".tmp_key")
        print("  Secret saved.")
    else:
        print("  Skipped. Set it later: gh secret set ANTHROPIC_API_KEY --repo {repo_full}")

    # 7. Initial commit and push
    run("git add -A")
    r = subprocess.run("git diff --staged --quiet", shell=True)
    if r.returncode != 0:
        run('git commit -m "feat: initial job tracker setup"')

    run("git push -u origin main")

    # 8. Enable GitHub Pages on docs/ folder
    print("\nEnabling GitHub Pages (serving from docs/ on main branch)...")
    run(
        f'gh api repos/{repo_full}/pages '
        f'-X POST -H "Accept: application/vnd.github+json" '
        f'-f source[branch]=main -f source[path]=/docs',
        check=False,
    )

    # 9. Trigger first run manually
    trigger = input("\nTrigger the first GitHub Actions run now? [Y/n]: ").strip().lower()
    if trigger != "n":
        run(f"gh workflow run job-tracker.yml --repo {repo_full}")
        print("\nWorkflow triggered! Check progress:")
        print(f"  https://github.com/{repo_full}/actions")

    print("\n" + "=" * 60)
    print("Setup complete!")
    print(f"\n  Repo:   https://github.com/{repo_full}")
    print(f"  Report: https://{username}.github.io/{repo_name}/")
    print(f"  Actions: https://github.com/{repo_full}/actions")
    print("\nThe tracker runs every Monday at 09:00 UTC automatically.")
    print("You can also trigger it manually from the Actions tab.")
    print("=" * 60)


if __name__ == "__main__":
    main()
