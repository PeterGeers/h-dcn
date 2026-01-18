# GitLens Setup for H-DCN Project

This document explains the GitLens configuration for the H-DCN project, specifically designed to prevent sync issues and track critical changes.

## 🎯 Purpose

After experiencing the AuthLayer sync issue where `backend/shared/auth_utils.py` and `backend/layers/auth-layer/python/shared/auth_utils.py` got out of sync, this setup ensures:

1. **Visual tracking** of critical file changes
2. **Automatic synchronization** of duplicate files
3. **Enhanced blame and history** for authentication and deployment code
4. **Pre-commit validation** to prevent sync issues

## 📁 Configuration Files

### `.vscode/settings.json`

- Core GitLens settings optimized for the project
- File watchers for critical directories
- Enhanced diff and blame visualization

### `.vscode/gitlens.json`

- Detailed GitLens configuration
- Custom blame formats and hover information
- Repository view settings

### `.vscode/tasks.json`

- **Check AuthLayer Sync**: Verify files are synchronized
- **Sync AuthLayer Files**: Manually sync the files
- **Git Status with Critical Files**: Check status of important files
- **Show Recent Changes**: View recent commits to critical files

### `.git/hooks/pre-commit`

- Automatically syncs AuthLayer files before commit
- Alerts about critical file changes
- Prevents deployment with out-of-sync files

## 🚀 How to Use

### Daily Workflow

1. **Before making changes**: Run `Ctrl+Shift+P` → "Tasks: Run Task" → "Check AuthLayer Sync"

2. **While coding**: GitLens will show:

   - Blame information inline
   - Recent changes in the gutter
   - File history in the sidebar

3. **Before committing**: The pre-commit hook automatically checks and syncs files

### Key GitLens Features Enabled

#### 1. **Inline Blame**

- Shows who changed each line and when
- Formatted as: `Author • Date • Message`

#### 2. **Code Lens**

- Shows recent changes and authors above functions
- Click to see commit details

#### 3. **File History**

- Right-click any file → "Open File History"
- See all changes to critical files like `auth_utils.py`

#### 4. **Repository View**

- GitLens sidebar shows:
  - Recent commits
  - File changes
  - Contributors
  - Branch comparison

#### 5. **Hover Information**

- Hover over any line to see:
  - Last change details
  - Commit message
  - Author information

## 🔍 Critical Files Being Tracked

### Authentication Layer

- `backend/shared/auth_utils.py` (main)
- `backend/layers/auth-layer/python/shared/auth_utils.py` (layer copy)

### Configuration

- `backend/template.yaml` (SAM template)
- `backend/samconfig.toml` (deployment config)
- `frontend/.env` (environment variables)

### Deployment Scripts

- `scripts/deployment/backend-build-and-deploy-fast.ps1`
- `scripts/deployment/frontend-build-and-deploy-fast.ps1`

## ⚡ Quick Commands

### VS Code Command Palette (`Ctrl+Shift+P`)

- `GitLens: Toggle File Blame` - Show/hide blame for current file
- `GitLens: Open File History` - View file's complete history
- `GitLens: Compare File with Previous` - See what changed
- `GitLens: Show Commit Graph` - Visual commit history

### Custom Tasks (`Ctrl+Shift+P` → "Tasks: Run Task")

- `Check AuthLayer Sync` - Verify files are synchronized
- `Sync AuthLayer Files` - Force synchronization
- `Git Status with Critical Files` - Check critical file status
- `Show Recent Changes to Critical Files` - View recent commits

## 🛡️ Preventing Future Issues

### The AuthLayer Sync Problem

The issue we encountered was:

1. `backend/shared/auth_utils.py` was updated with new functions
2. `backend/layers/auth-layer/python/shared/auth_utils.py` wasn't updated
3. Lambda functions using the layer couldn't find the new functions
4. Result: "Authentication not available" errors

### How This Setup Prevents It

1. **Pre-commit hook** automatically syncs files
2. **Visual indicators** show when files are different
3. **Tasks** make it easy to check and sync manually
4. **GitLens blame** shows who last changed each file

## 🔧 Customization

### Adding More Critical Files

Edit `.vscode/tasks.json` and add files to the git commands:

```json
"args": [
  "status",
  "--porcelain",
  "your/new/critical/file.py"
]
```

### Changing Blame Format

Edit `.vscode/gitlens.json`:

```json
"blame": {
  "format": "${author|20} ${date|16-} ${message|60?}"
}
```

## 📊 Benefits

1. **Immediate visibility** into who changed what and when
2. **Automatic prevention** of sync issues
3. **Enhanced debugging** with full file history
4. **Better collaboration** with clear change attribution
5. **Deployment safety** with pre-commit validation

## 🆘 Troubleshooting

### GitLens not showing information

1. Ensure you're in a Git repository
2. Check that GitLens extension is enabled
3. Try `GitLens: Reset Avatar Cache`

### Pre-commit hook not working

1. Ensure the hook file is executable: `chmod +x .git/hooks/pre-commit`
2. Check that Git is configured properly
3. Verify the file paths in the hook script

### Files still getting out of sync

1. Run "Check AuthLayer Sync" task manually
2. Use "Sync AuthLayer Files" task to force sync
3. Check if the pre-commit hook is being bypassed

## 📝 Notes

- This setup is specifically tailored for the H-DCN project structure
- The configuration prioritizes authentication and deployment file tracking
- All settings are workspace-specific and won't affect other projects
- The pre-commit hook only runs when committing changes

---

**Remember**: GitLens is now your early warning system for code changes. Use it to understand the impact of modifications before they cause deployment issues!
