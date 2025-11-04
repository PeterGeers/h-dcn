# H-DCN VSCode Troubleshooting Guide

## 🔧 Common Issues & Solutions

### VSCode Configuration Issues

#### Extensions Not Installing
**Problem**: Recommended extensions don't install automatically

**Solutions**:
```bash
# 1. Reload VSCode
Ctrl+Shift+P → "Developer: Reload Window"

# 2. Manual installation
Ctrl+Shift+X → Search extension ID → Install

# 3. Check internet connection
# 4. Clear extension cache
```

#### Settings Not Applied
**Problem**: Team settings not working

**Solutions**:
```bash
# 1. Check file exists
ls .vscode/settings.json

# 2. Validate JSON syntax
# Use VSCode JSON validation

# 3. Reload workspace
File → Close Workspace → Reopen

# 4. Check settings precedence
Ctrl+Shift+P → "Preferences: Open Settings (JSON)"
```

### Development Environment Issues

#### Node.js/NPM Problems
**Problem**: Frontend tasks fail

**Solutions**:
```bash
# 1. Check Node version
node --version  # Should be 18+

# 2. Clear npm cache
npm cache clean --force

# 3. Delete node_modules
rm -rf frontend/node_modules
cd frontend && npm install

# 4. Check npm registry
npm config get registry
```

#### Python/SAM Issues
**Problem**: Backend tasks fail

**Solutions**:
```bash
# 1. Check Python version
python --version  # Should be 3.9+

# 2. Check SAM installation
sam --version

# 3. Reinstall SAM CLI
# Follow AWS SAM installation guide

# 4. Check Docker
docker --version
docker ps
```

#### AWS Configuration Problems
**Problem**: AWS tasks fail with permission errors

**Solutions**:
```bash
# 1. Test AWS connection
aws sts get-caller-identity

# 2. Check credentials
aws configure list

# 3. Verify profile
aws configure list-profiles

# 4. Check region
aws configure get region

# 5. Update credentials
aws configure
```

### Task & Debug Issues

#### Tasks Not Running
**Problem**: VSCode tasks fail to execute

**Solutions**:
```bash
# 1. Check task definition
# Open .vscode/tasks.json
# Verify paths and commands

# 2. Test command manually
# Run the exact command in terminal

# 3. Check working directory
# Ensure cwd path exists

# 4. Verify shell
# Check if PowerShell/bash is available
```

#### Debug Configuration Fails
**Problem**: Debug sessions won't start

**Solutions**:
```bash
# 1. Check ports availability
netstat -ano | findstr :3000
netstat -ano | findstr :3001

# 2. Kill conflicting processes
taskkill /PID <process_id> /F

# 3. Verify launch.json
# Check paths and configurations

# 4. Test without debugging
# Use Ctrl+F5 instead of F5
```

### Code Quality Issues

#### ESLint Not Working
**Problem**: No linting errors shown

**Solutions**:
```bash
# 1. Check ESLint extension
# Ensure ms-vscode.eslint is installed

# 2. Verify working directory
# Check eslint.workingDirectories in settings

# 3. Check ESLint config
cd frontend
npx eslint --print-config src/App.tsx

# 4. Restart ESLint server
Ctrl+Shift+P → "ESLint: Restart ESLint Server"
```

#### Prettier Not Formatting
**Problem**: Code doesn't format on save

**Solutions**:
```bash
# 1. Check Prettier extension
# Ensure esbenp.prettier-vscode is installed

# 2. Verify default formatter
# Check editor.defaultFormatter setting

# 3. Check format on save
# Ensure editor.formatOnSave is true

# 4. Manual format
Shift+Alt+F
```

#### TypeScript Errors
**Problem**: TypeScript showing incorrect errors

**Solutions**:
```bash
# 1. Restart TypeScript server
Ctrl+Shift+P → "TypeScript: Restart TS Server"

# 2. Check TypeScript version
# Ensure using workspace version

# 3. Clear TypeScript cache
# Delete .tsbuildinfo files

# 4. Reload workspace
File → Close Workspace → Reopen
```

### Performance Issues

#### VSCode Running Slow
**Problem**: VSCode is sluggish or unresponsive

**Solutions**:
```bash
# 1. Disable unnecessary extensions
# Keep only H-DCN required extensions

# 2. Increase memory limit
# Add to settings.json:
"typescript.preferences.includePackageJsonAutoImports": "off"

# 3. Exclude large directories
# Update files.exclude in settings

# 4. Close unused tabs
# Use workbench.editor.limit setting
```

#### High CPU Usage
**Problem**: VSCode using too much CPU

**Solutions**:
```bash
# 1. Check running processes
Ctrl+Shift+P → "Developer: Show Running Extensions"

# 2. Disable file watching
# Add to settings.json:
"files.watcherExclude": {
  "**/node_modules/**": true,
  "**/.aws-sam/**": true
}

# 3. Reduce TypeScript checking
"typescript.preferences.includePackageJsonAutoImports": "off"
```

### Git Integration Issues

#### Source Control Not Working
**Problem**: Git panel shows no changes

**Solutions**:
```bash
# 1. Check Git installation
git --version

# 2. Verify repository
git status

# 3. Reload Git
Ctrl+Shift+P → "Git: Refresh"

# 4. Check Git settings
git config --list
```

#### Merge Conflicts
**Problem**: Git merge conflicts in VSCode

**Solutions**:
```bash
# 1. Use VSCode merge editor
# Click "Resolve in Merge Editor"

# 2. Manual resolution
# Edit files directly
# Remove conflict markers

# 3. Use Git commands
git status
git add .
git commit -m "Resolve conflicts"
```

### Network & Connectivity Issues

#### Cannot Connect to AWS
**Problem**: AWS operations timeout

**Solutions**:
```bash
# 1. Check internet connection
ping aws.amazon.com

# 2. Check VPN/Proxy settings
# Verify corporate network access

# 3. Check AWS service status
# Visit AWS Service Health Dashboard

# 4. Try different region
aws configure set region us-east-1
```

#### NPM Install Fails
**Problem**: Cannot download packages

**Solutions**:
```bash
# 1. Check npm registry
npm config get registry

# 2. Use different registry
npm config set registry https://registry.npmjs.org/

# 3. Clear SSL issues
npm config set strict-ssl false

# 4. Use corporate proxy
npm config set proxy http://proxy:port
```

## 🆘 Getting Help

### Self-Help Resources
1. **Amazon Q Developer** - Ask in VSCode chat panel
2. **Command Palette** - `Ctrl+Shift+P` for all commands
3. **Developer Tools** - `Help → Toggle Developer Tools`
4. **Extension Logs** - Check Output panel for extension logs

### Team Support
1. **H-DCN Team** - Contact development team
2. **Documentation** - Check project README and docs
3. **Git Issues** - Create issue in repository
4. **Slack/Teams** - Use team communication channels

### External Resources
1. **VSCode Issues** - [GitHub VSCode Issues](https://github.com/microsoft/vscode/issues)
2. **AWS Support** - AWS documentation and forums
3. **Stack Overflow** - Search for specific error messages
4. **Extension Issues** - Check individual extension repositories

## 📋 Diagnostic Commands

### System Information
```bash
# VSCode version
code --version

# System info
systeminfo  # Windows
uname -a     # Linux/Mac

# Node/NPM versions
node --version
npm --version

# Python version
python --version

# AWS CLI version
aws --version

# SAM CLI version
sam --version

# Git version
git --version

# Docker version
docker --version
```

### VSCode Diagnostics
```bash
# Show running extensions
Ctrl+Shift+P → "Developer: Show Running Extensions"

# Show extension host log
Ctrl+Shift+P → "Developer: Show Logs..." → "Extension Host"

# Show workspace info
Ctrl+Shift+P → "Developer: Show Workspace Info"

# Reload window
Ctrl+Shift+P → "Developer: Reload Window"
```

### Project Diagnostics
```bash
# Check project structure
tree -L 2  # or ls -la

# Check Git status
git status
git log --oneline -5

# Check dependencies
cd frontend && npm list --depth=0
cd backend && pip list

# Check ports
netstat -ano | findstr :3000
netstat -ano | findstr :3001
```

---

**Still having issues?** Contact the H-DCN development team with:
1. Error messages (exact text)
2. Steps to reproduce
3. System information
4. Screenshots if applicable