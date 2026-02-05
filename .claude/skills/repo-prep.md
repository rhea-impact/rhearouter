---
name: repo-prep
description: Prepare a repository before pushing to GitHub or making it public
triggers:
  - prepare repo
  - prep repo
  - push to github
  - make public
  - first commit
  - repo checklist
  - before pushing
---

# Repository Preparation Checklist

Essential checks and setup before pushing a repository to GitHub or making it public.

## Pre-Push Checklist

### 1. Secrets and Credentials

```bash
# Check for common secret patterns
grep -r "api_key" . --exclude-dir=venv --exclude-dir=.git
grep -r "password" . --exclude-dir=venv --exclude-dir=.git
grep -r "token" . --exclude-dir=venv --exclude-dir=.git
grep -r "secret" . --exclude-dir=venv --exclude-dir=.git

# Check for AWS credentials
grep -r "AKIA" . --exclude-dir=venv --exclude-dir=.git
grep -r "aws_access_key" . --exclude-dir=venv --exclude-dir=.git

# Check for database connection strings
grep -r "postgresql://" . --exclude-dir=venv --exclude-dir=.git
grep -r "mongodb://" . --exclude-dir=venv --exclude-dir=.git
grep -r "mysql://" . --exclude-dir=venv --exclude-dir=.git

# Check for private IPs and hostnames
grep -r "192.168." . --exclude-dir=venv --exclude-dir=.git
grep -r "10.0." . --exclude-dir=venv --exclude-dir=.git
```

**Fix:** Move all secrets to `.env` and ensure `.env` is in `.gitignore`

### 2. .gitignore Setup

Ensure `.gitignore` includes:

```gitignore
# Environment and secrets
.env
.env.local
.env.*.local
*.key
*.pem
secrets/
credentials/

# Python
venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
dist/
build/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
.Trash-*/

# Logs and databases
*.log
*.sql
*.sqlite
*.db

# Temporary files
tmp/
temp/
*.tmp
```

### 3. Environment Template

Create `.env.example` with safe defaults:

```bash
# Copy .env to .env.example
cp .env .env.example

# Remove all actual secrets/values from .env.example
# Replace with placeholder values like:
API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
```

### 4. License File

Ensure `LICENSE` file exists:

```bash
# For MIT License (most permissive)
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 Your Name or Organization

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
```

### 5. README.md Quality Check

Ensure README includes:
- [ ] Clear project description
- [ ] Installation instructions
- [ ] Usage examples
- [ ] Configuration documentation
- [ ] License information
- [ ] Contributing guidelines
- [ ] Link to organization (e.g., Rhea Impact)
- [ ] Badges (license, tests, Python version)

### 6. Git History Cleanup

```bash
# Check git history for sensitive data
git log --all --full-history --source --find-object=<path-to-sensitive-file>

# If sensitive data is in history, use git-filter-repo or BFG
# https://github.com/newren/git-filter-repo

# Check for large files that shouldn't be committed
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print $3, $4}' | \
  sort -rn | \
  head -20
```

### 7. Documentation Files

Ensure these exist and are up-to-date:
- [ ] `README.md` - Main documentation
- [ ] `LICENSE` - License file
- [ ] `CONTRIBUTING.md` - How to contribute
- [ ] `.env.example` - Environment template
- [ ] API documentation (if applicable)
- [ ] Architecture documentation (if complex)

### 8. Test Suite

```bash
# Run all tests before pushing
pytest src/tests/ -v

# Ensure tests pass
# Fix any failing tests before pushing
```

### 9. Code Quality

```bash
# Check for TODO/FIXME comments that should be addressed
grep -r "TODO" . --exclude-dir=venv --exclude-dir=.git
grep -r "FIXME" . --exclude-dir=venv --exclude-dir=.git
grep -r "HACK" . --exclude-dir=venv --exclude-dir=.git

# Check for debug statements that should be removed
grep -r "console.log" . --exclude-dir=node_modules --exclude-dir=.git
grep -r "print(" . --exclude-dir=venv --exclude-dir=.git | grep -v "# print"
grep -r "debugger" . --exclude-dir=node_modules --exclude-dir=.git
```

### 10. Dependencies

```bash
# Generate/update requirements.txt (Python)
pip freeze > requirements.txt

# Or use pip-compile for better dependency management
pip-compile requirements.in > requirements.txt

# Review requirements for:
# - Unused dependencies
# - Pinned versions vs flexible versions
# - Security vulnerabilities
```

### 11. GitHub Repository Settings

After creating the repo on GitHub:

```bash
# Set repository topics (helps with discoverability)
gh repo edit --add-topic python --add-topic fastapi --add-topic ai-agent

# Add description
gh repo edit --description "Your clear, concise description"

# Set default branch to main (if not already)
gh repo edit --default-branch main
```

### 12. GitHub Community Files

Create in `.github/` directory:

```bash
mkdir -p .github

# Pull request template
cat > .github/PULL_REQUEST_TEMPLATE.md << 'EOF'
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
EOF

# Issue templates
mkdir -p .github/ISSUE_TEMPLATE
cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOF'
---
name: Bug Report
about: Report a bug or unexpected behavior
title: "[BUG] "
labels: bug
assignees: ''
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1.
2.
3.

**Expected behavior**
What you expected to happen.

**Environment:**
- OS:
- Python version:
- Package version:

**Additional context**
Any other relevant information.
EOF

cat > .github/ISSUE_TEMPLATE/feature_request.md << 'EOF'
---
name: Feature Request
about: Suggest a new feature or enhancement
title: "[FEATURE] "
labels: enhancement
assignees: ''
---

**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How you envision this working.

**Alternatives Considered**
Other approaches you've thought about.
EOF
```

### 13. CI/CD Setup (Optional but Recommended)

```bash
# GitHub Actions workflow for tests
mkdir -p .github/workflows
cat > .github/workflows/tests.yml << 'EOF'
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest src/tests/ -v
EOF
```

## Quick Pre-Push Command

```bash
# Run all checks at once
echo "=== Checking for secrets ==="
grep -r "api_key\|password\|token\|secret" . --exclude-dir=venv --exclude-dir=.git --exclude-dir=.claude | grep -v ".env.example" || echo "✓ No secrets found"

echo "=== Checking .gitignore ==="
test -f .gitignore && echo "✓ .gitignore exists" || echo "✗ Missing .gitignore"

echo "=== Checking .env.example ==="
test -f .env.example && echo "✓ .env.example exists" || echo "✗ Missing .env.example"

echo "=== Checking LICENSE ==="
test -f LICENSE && echo "✓ LICENSE exists" || echo "✗ Missing LICENSE"

echo "=== Running tests ==="
pytest src/tests/ -v

echo "=== Checking for debug statements ==="
grep -r "print(" . --exclude-dir=venv --exclude-dir=.git | grep -v "# print" || echo "✓ No debug print statements"

echo "=== Git status ==="
git status
```

## Common Mistakes to Avoid

1. **Committing .env files** - Always gitignore them
2. **Hardcoded credentials** - Use environment variables
3. **Large binary files** - Use Git LFS or external storage
4. **Sensitive data in git history** - Use git-filter-repo to clean
5. **Missing LICENSE** - Required for open source
6. **Poor README** - First impression matters
7. **Failing tests** - Never push with failing tests
8. **Debug code** - Remove print/console.log statements
9. **TODO comments** - Address or create issues for them
10. **Absolute paths** - Use relative paths or environment variables

## After Pushing

1. **Verify the repo looks good on GitHub** - Check all files rendered correctly
2. **Test clone and setup** - Ensure new users can get started
3. **Add to organization** - If part of rhea-impact org
4. **Set up branch protection** - Require PR reviews for main
5. **Enable issues and discussions** - Community engagement
6. **Add topics/tags** - Improve discoverability
7. **Share with team** - Get feedback

## Emergency: Pushed Sensitive Data

If you accidentally pushed secrets:

1. **Rotate the secrets immediately** - Assume they're compromised
2. **Remove from git history** - Use git-filter-repo
3. **Force push** - `git push --force` (if no one has pulled yet)
4. **Contact GitHub Support** - If it's a serious leak
5. **Document the incident** - Learn from it

```bash
# Remove file from entire git history
git filter-repo --path path/to/secret/file --invert-paths
git push --force
```

## Resources

- [GitHub's Guide to Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [git-filter-repo](https://github.com/newren/git-filter-repo)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security/getting-started/securing-your-repository)
