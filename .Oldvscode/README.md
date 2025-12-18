# H-DCN VSCode Configuration

## 🚀 Quick Start

### 1. Open Workspace
```bash
# Open the workspace file
code h-dcn.code-workspace
```

### 2. Install Extensions
VSCode will automatically prompt to install recommended extensions:
- Amazon Q Developer
- TypeScript/React tools
- Python/AWS tools
- Code quality tools

### 3. Configure Personal Settings
```bash
# Copy example file
cp .vscode/settings.local.json.example .vscode/settings.local.json

# Edit your personal settings
code .vscode/settings.local.json
```

### 4. Configure AWS
```bash
# Set up AWS CLI
aws configure

# Or use environment variables
export AWS_PROFILE=your-profile
export AWS_REGION=eu-west-1
```

## 📋 Available Tasks

Press `Ctrl+Shift+P` → `Tasks: Run Task`:

### Frontend Tasks
- **Frontend: Install Dependencies** - `npm install`
- **Frontend: Start Dev Server** - `npm start` (port 3000)
- **Frontend: Build Production** - `npm run build`
- **Frontend: Run Tests** - `npm test`

### Backend Tasks
- **Backend: SAM Build** - Build Lambda functions
- **Backend: SAM Deploy** - Deploy to AWS
- **Backend: SAM Local API** - Local API (port 3001)

### Deployment Tasks
- **Deploy Frontend to S3** - Upload to S3 bucket
- **Git Upload** - Automated git workflow

## 🐛 Debug Configurations

Press `F5` or use Debug panel:

- **Debug React App** - Debug frontend on port 3000
- **Debug Lambda Function** - Debug Python Lambda locally
- **SAM Local API** - Debug API Gateway locally

## 📝 Code Snippets

Type these prefixes and press `Tab`:

- `rfc` - React Functional Component with TypeScript
- `lambda` - Lambda handler with error handling
- `interface` - TypeScript interface
- `chakra` - Chakra UI component

## 🔧 Configuration Files

### Synchronized (Git)
- `settings.json` - Team project settings
- `extensions.json` - Recommended extensions
- `tasks.json` - Development tasks
- `launch.json` - Debug configurations
- `snippets.code-snippets` - Code templates
- `h-dcn.code-workspace` - Workspace definition

### Local Only
- `settings.local.json` - Personal preferences
- User-specific extension settings

## 🎨 Theme & Layout

### Team Standard
- **Theme**: Default Dark+
- **Icons**: VS-Seti
- **Layout**: Activity bar left, panel bottom
- **Minimap**: Enabled (right side)

### Personal Override
Edit `settings.local.json`:
```json
{
  "workbench.colorTheme": "Your Theme",
  "editor.minimap.enabled": false
}
```

## 🔍 Troubleshooting

### Extensions Not Installing
1. Check internet connection
2. Reload VSCode: `Ctrl+Shift+P` → `Developer: Reload Window`
3. Manual install: Extensions panel → Search extension ID

### Tasks Not Working
1. Verify working directory in task definition
2. Check if required tools are installed (npm, sam, python)
3. Open terminal and run commands manually

### Debug Not Starting
1. Check launch configuration paths
2. Verify ports are available (3000, 3001)
3. Ensure dependencies are installed

### AWS Issues
1. Verify AWS CLI configuration: `aws sts get-caller-identity`
2. Check AWS credentials and permissions
3. Verify region settings

## 📚 Useful Shortcuts

### General
- `Ctrl+Shift+P` - Command Palette
- `Ctrl+`` - Toggle Terminal
- `Ctrl+Shift+E` - Explorer
- `Ctrl+Shift+D` - Debug Panel

### Development
- `F5` - Start Debugging
- `Ctrl+F5` - Run Without Debugging
- `Ctrl+Shift+` - New Terminal
- `Alt+Click` - Multi-cursor

### Git
- `Ctrl+Shift+G` - Source Control
- `Ctrl+Enter` - Commit
- `Ctrl+Shift+P` → `Git: Push`

## 🆘 Getting Help

1. **Amazon Q Developer** - Ask questions in chat panel
2. **Hover tooltips** - Hover over settings for explanations
3. **Command Palette** - `Ctrl+Shift+P` for all commands
4. **Problems Panel** - `Ctrl+Shift+M` for errors/warnings

## 🔄 Updating Configuration

### For Team Changes
1. Edit `.vscode/settings.json`
2. Commit and push changes
3. Team members pull updates
4. VSCode automatically reloads settings

### For Personal Changes
1. Edit `.vscode/settings.local.json`
2. Changes apply immediately
3. Not committed to Git

---

**Need help?** Contact the H-DCN development team or use Amazon Q Developer chat.