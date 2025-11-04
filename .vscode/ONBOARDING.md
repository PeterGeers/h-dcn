# H-DCN Developer Onboarding

## 🎯 Welcome to H-DCN Development!

This guide will get you up and running with the H-DCN project in VSCode.

## ✅ Prerequisites Checklist

### Required Software
- [ ] **VSCode** - Latest version installed
- [ ] **Node.js 18+** - For React frontend
- [ ] **Python 3.9+** - For Lambda backend
- [ ] **Git** - Version control
- [ ] **AWS CLI** - AWS deployment tools
- [ ] **SAM CLI** - Serverless deployment
- [ ] **Docker** - For local Lambda testing

### Installation Commands
```bash
# Verify installations
node --version    # Should be 18+
python --version  # Should be 3.9+
git --version
aws --version
sam --version
docker --version
```

## 🚀 Setup Steps

### 1. Clone Repository
```bash
git clone https://github.com/PeterGeers/h-dcn.git
cd h-dcn
```

### 2. Open in VSCode
```bash
# Option A: Open workspace file
code .vscode/h-dcn.code-workspace

# Option B: Open folder
code .
```

### 3. Install Extensions
VSCode will show a notification to install recommended extensions:
- Click **"Install All"** or **"Show Recommendations"**
- Wait for all extensions to install
- Reload VSCode if prompted

### 4. Configure Personal Settings
```bash
# Copy template
cp .vscode/settings.local.json.example .vscode/settings.local.json

# Edit with your preferences
code .vscode/settings.local.json
```

Example personal configuration:
```json
{
  "aws.profile": "h-dcn-dev",
  "aws.region": "eu-west-1",
  "editor.fontSize": 14,
  "workbench.colorTheme": "Dark+ (default dark)"
}
```

### 5. Setup AWS Credentials
```bash
# Configure AWS CLI
aws configure

# Or use environment variables
export AWS_PROFILE=h-dcn-dev
export AWS_REGION=eu-west-1
```

### 6. Install Dependencies
Use VSCode tasks or terminal:

**Frontend:**
```bash
cd frontend
npm install
```

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

## 🧪 Test Your Setup

### 1. Frontend Test
```bash
# Using VSCode task: Ctrl+Shift+P → "Tasks: Run Task" → "Frontend: Start Dev Server"
# Or terminal:
cd frontend
npm start
```
✅ Should open http://localhost:3000

### 2. Backend Test
```bash
# Using VSCode task: "Backend: SAM Local API"
# Or terminal:
cd backend
sam local start-api --port 3001
```
✅ Should start API on http://localhost:3001

### 3. Debug Test
- Press `F5` in VSCode
- Select "Debug React App"
- ✅ Should start debugging session

## 📋 Development Workflow

### Daily Workflow
1. **Pull latest changes**: `git pull`
2. **Start development servers**: Use VSCode tasks
3. **Make changes**: Edit code with full IntelliSense
4. **Test locally**: Use debug configurations
5. **Commit changes**: Use Source Control panel (`Ctrl+Shift+G`)

### Code Quality
- **Auto-formatting**: Saves with Prettier formatting
- **Linting**: ESLint shows errors/warnings
- **Type checking**: TypeScript provides type safety
- **Code completion**: Amazon Q Developer assists

### Testing
- **Frontend tests**: `npm test` in frontend folder
- **Backend tests**: `pytest` in backend folder
- **Integration tests**: SAM local testing

## 🎨 VSCode Features

### Panels & Views
- **Explorer** (`Ctrl+Shift+E`) - File browser
- **Source Control** (`Ctrl+Shift+G`) - Git operations
- **Debug** (`Ctrl+Shift+D`) - Debugging tools
- **Extensions** (`Ctrl+Shift+X`) - Manage extensions
- **Terminal** (`Ctrl+``) - Integrated terminal

### Productivity Features
- **Command Palette** (`Ctrl+Shift+P`) - All commands
- **Quick Open** (`Ctrl+P`) - Fast file navigation
- **Multi-cursor** (`Alt+Click`) - Edit multiple lines
- **IntelliSense** (`Ctrl+Space`) - Code completion

### H-DCN Specific
- **Code snippets** - Type `rfc`, `lambda`, `interface`
- **Tasks** - Pre-configured build/deploy tasks
- **Debug configs** - Ready-to-use debug setups
- **Amazon Q** - AI coding assistant

## 🔧 Customization

### Personal Preferences
Edit `.vscode/settings.local.json`:
```json
{
  // Theme & Appearance
  "workbench.colorTheme": "Monokai",
  "editor.fontSize": 16,
  "editor.fontFamily": "Fira Code",
  
  // Editor Behavior
  "editor.minimap.enabled": false,
  "editor.wordWrap": "on",
  
  // Terminal
  "terminal.integrated.fontSize": 14
}
```

### Keyboard Shortcuts
- `File → Preferences → Keyboard Shortcuts`
- Search for commands to customize
- Changes are personal (not synced)

## 🆘 Common Issues

### Extensions Not Loading
```bash
# Reload VSCode
Ctrl+Shift+P → "Developer: Reload Window"

# Check extension host
Ctrl+Shift+P → "Developer: Show Running Extensions"
```

### Tasks Failing
```bash
# Check working directory
# Verify tools are installed
# Run commands manually in terminal
```

### AWS Connection Issues
```bash
# Test AWS connection
aws sts get-caller-identity

# Check credentials
aws configure list

# Verify permissions
aws iam get-user
```

### Port Conflicts
```bash
# Check what's using ports
netstat -ano | findstr :3000
netstat -ano | findstr :3001

# Kill processes if needed
taskkill /PID <process_id> /F
```

## 📚 Learning Resources

### H-DCN Specific
- [README.md](../README.md) - Project overview
- [Guardrails](../guardrail.md) - Development principles
- [API Documentation](../backend/api.md) - Backend API reference

### VSCode
- [VSCode Documentation](https://code.visualstudio.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [React Documentation](https://react.dev/)

### AWS
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)
- [Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/)

## 🎉 You're Ready!

Congratulations! You now have a fully configured H-DCN development environment.

### Next Steps:
1. **Explore the codebase** - Start with `frontend/src/App.tsx`
2. **Run the application** - Use the development tasks
3. **Make your first change** - Try editing a component
4. **Ask for help** - Use Amazon Q Developer or contact the team

**Happy coding!** 🚀