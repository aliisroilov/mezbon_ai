# Mezbon AI - Version Control Setup

## 📋 Initial Git Setup

### 1. Initialize Git Repository

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception

# Initialize git
git init

# Verify .gitignore exists
ls -la .gitignore
```

### 2. Create .env from Example

```bash
# Backend
cd backend
cp .env.example .env
nano .env  # Fill in your actual values

# NEVER commit the actual .env file!
```

### 3. First Commit

```bash
cd /Users/aliisroilov/Desktop/AI\ Reception

# Add all files
git add .

# Verify what will be committed
git status

# Make sure .env is NOT in the list!
# If .env appears, it means .gitignore is not working

# Commit
git commit -m "Initial commit: Mezbon AI Reception System"
```

### 4. Connect to GitHub/GitLab

```bash
# Create a new repository on GitHub/GitLab first
# Then connect:

git remote add origin https://github.com/yourusername/mezbon-ai.git

# Or using SSH:
git remote add origin git@github.com:yourusername/mezbon-ai.git

# Push to remote
git branch -M main
git push -u origin main
```

---

## ⚠️ CRITICAL: Verify Before Pushing

**Always check these before pushing:**

```bash
# Check what files are staged
git status

# Check that sensitive files are ignored
git ls-files | grep -E '\.env$|\.key$|\.pem$|credentials\.json$'
# Should return NOTHING

# Check .gitignore is working
git check-ignore backend/.env
# Should output: backend/.env
```

---

## 🚫 Files That Should NEVER Be Committed

- ❌ `.env` files
- ❌ `google-credentials.json`
- ❌ Any `*.key` or `*.pem` files
- ❌ Database dumps (`.sql`, `.dump`)
- ❌ `node_modules/`
- ❌ `venv/` or `.venv/`
- ❌ `__pycache__/`
- ❌ User uploads
- ❌ Log files
- ❌ API keys or passwords

---

## ✅ Files That SHOULD Be Committed

- ✅ `.gitignore`
- ✅ `.env.example`
- ✅ `README.md`
- ✅ `requirements.txt`
- ✅ `package.json`
- ✅ Source code (`.py`, `.ts`, `.tsx`)
- ✅ Configuration files
- ✅ Documentation
- ✅ Database migrations

---

## 📝 Useful Git Commands

### Daily Workflow

```bash
# Check status
git status

# Add changes
git add .

# Commit
git commit -m "Description of changes"

# Push
git push
```

### Branching

```bash
# Create feature branch
git checkout -b feature/voice-improvements

# Switch branches
git checkout main

# Merge branch
git merge feature/voice-improvements

# Delete branch
git branch -d feature/voice-improvements
```

### If You Accidentally Committed .env

```bash
# Remove from git but keep local file
git rm --cached backend/.env

# Commit the removal
git commit -m "Remove .env from git"

# Force push (ONLY if you haven't shared this commit yet)
git push --force
```

### View History

```bash
# View commits
git log --oneline

# View changes
git diff

# View specific file history
git log --follow backend/app/main.py
```

---

## 🔒 Security Best Practices

1. **Never commit secrets**
   - Use `.env.example` for templates
   - Keep actual `.env` files local only

2. **Use environment-specific files**
   - `.env.development`
   - `.env.production`
   - All ignored by git

3. **Rotate secrets if exposed**
   - If you accidentally commit a secret, assume it's compromised
   - Immediately rotate all keys/passwords
   - Use `git filter-branch` to remove from history

4. **Use `.gitignore` properly**
   - Review before each commit
   - Keep it updated
   - Test with `git status`

---

## 📁 Recommended Repository Structure

```
mezbon-ai/
├── .gitignore           ✅ Committed
├── README.md            ✅ Committed
├── backend/
│   ├── .env.example     ✅ Committed
│   ├── .env             ❌ Ignored
│   ├── requirements.txt ✅ Committed
│   └── app/             ✅ Committed
├── kiosk-ui/
│   ├── .env.example     ✅ Committed
│   ├── .env             ❌ Ignored
│   ├── package.json     ✅ Committed
│   └── src/             ✅ Committed
└── docs/                ✅ Committed
```

---

## 🚀 Deployment Workflow

### Development → Staging → Production

```bash
# Development
git checkout develop
git pull
# Make changes
git add .
git commit -m "Feature: Add new greeting"
git push

# Staging
git checkout staging
git merge develop
git push

# Production (after testing)
git checkout main
git merge staging
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin main --tags
```

---

## 🆘 Emergency: Leaked Secrets

If you accidentally commit secrets:

```bash
# 1. Immediately rotate ALL credentials
# 2. Remove from git history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

# 3. Force push (WARNING: Only if repository is private)
git push origin --force --all

# 4. Notify team members to re-clone
```

---

## 📚 Additional Resources

- [Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Ignore Generator](https://www.toptal.com/developers/gitignore)

---

## ✉️ Support

For questions about version control setup:
- Check existing issues in the repository
- Contact the development team
- Review this README

---

**Remember:** When in doubt, DON'T commit! Ask first. 🛡️
