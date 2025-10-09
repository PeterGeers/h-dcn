# H-DCN Dashboard

A comprehensive full-stack web application for H-DCN (Harley-Davidson Club Nederland) providing club management, e-commerce, and member administration with mobile-responsive design.

## 🚀 Project Overview

The H-DCN Dashboard is a modern web application built with React frontend and AWS serverless backend, designed to manage all aspects of the Harley-Davidson Club Nederland operations.

### Key Features
- **Mobile-First Responsive Design** - Optimized for all devices
- **Role-Based Access Control** - Granular permissions system
- **E-commerce Integration** - Webshop with Stripe payments
- **Member Management** - Complete CRUD operations
- **Event Management** - Club events and participation tracking
- **AWS Cognito Authentication** - Secure user management
- **Serverless Architecture** - Scalable and cost-effective

## 🏗️ Architecture

### Frontend (React)
- **Framework**: React 18 with Chakra UI
- **Authentication**: AWS Cognito integration
- **State Management**: React Context
- **Routing**: React Router v6
- **Forms**: Formik + Yup validation
- **Payments**: Stripe integration
- **PDF Generation**: jsPDF + html2canvas

### Backend (AWS Serverless)
- **API**: 51 Lambda functions with API Gateway
- **Database**: DynamoDB for all data storage
- **Authentication**: Cognito User Pools
- **File Storage**: S3 buckets
- **Configuration**: Parameter Store
- **Infrastructure**: AWS SAM templates

## 📋 Functionality by User Role

### All Users
- **Membership Registration** - Dynamic form for new members

### Members (hdcnLeden)
- **Webshop** - Product ordering with payment processing
- **Profile Management** - Personal data updates

### Regional Administrators (hdcnRegio_*)
- **Regional Member Administration** - Read-only access to regional members

### Administrators (hdcnAdmins)
- **Complete Member Administration** - User and group management
- **Event Management** - Create and manage club events
- **Product Management** - Webshop inventory control
- **Parameter Management** - System configuration
- **Cognito Administration** - User pool management

## 🔐 Access Control System

### Cognito Groups
| Group | Access Level |
|-------|-------------|
| No groups | Membership registration only |
| hdcnLeden | Webshop + Profile |
| hdcnAdmins | All modules |
| hdcnRegio_* | Regional members (read-only) |

### Function-Level Permissions
Advanced permission system via `function_permissions` parameter:
- **Read**: View-only access
- **Write**: View and modify access
- **Wildcards**: `hdcnRegio_*` for all regions

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- AWS CLI configured
- SAM CLI installed
- Docker (for local development)

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
# Configure AWS Cognito settings in .env
npm start
```

### Backend Deployment
```bash
cd backend
sam build --use-container
sam deploy --guided
```

### Environment Configuration
Create `.env` in frontend directory:
```env
REACT_APP_AWS_REGION=eu-west-1
REACT_APP_USER_POOL_ID=your-user-pool-id
REACT_APP_USER_POOL_WEB_CLIENT_ID=your-client-id
REACT_APP_API_BASE_URL=your-api-url
```

## 📱 Mobile Responsiveness

The application features comprehensive mobile optimization:
- **Responsive Tables** - Horizontal scroll with sticky action columns
- **Compact Filters** - Collapsible dropdown filters
- **Touch-Friendly UI** - Minimum 44px touch targets
- **Progressive Disclosure** - Hide non-essential columns on mobile
- **Mobile Navigation** - Optimized button layouts and spacing

## 🛠️ Development Tools

### Available Scripts
```bash
# Frontend
npm start              # Development server
npm run build          # Production build
npm test              # Run tests

# Backend
sam build             # Build Lambda functions
sam deploy            # Deploy to AWS
sam logs -n FunctionName --tail  # View logs

# Deployment
.\deploy.ps1          # Frontend deployment to S3
.\git-upload.ps1      # Git workflow automation
```

### Project Structure
```
h-dcn/
├── frontend/         # React application
│   ├── src/
│   │   ├── components/    # Reusable components
│   │   ├── modules/       # Feature modules
│   │   ├── pages/         # Main pages
│   │   └── utils/         # Services and utilities
│   └── public/
├── backend/          # AWS SAM application
│   ├── handler/      # Lambda function handlers (51 functions)
│   ├── template.yaml # SAM infrastructure template
│   └── tests/        # Backend tests
└── documentation/    # Project documentation
```

## 🔧 API Endpoints

The backend provides 51 REST API endpoints organized by functionality:
- **Products** - E-commerce product management
- **Members** - Club member CRUD operations
- **Payments** - Payment tracking and history
- **Events** - Event management and participation
- **Memberships** - Membership type management
- **Carts & Orders** - Shopping cart and order processing
- **Parameters** - System configuration
- **Cognito** - User pool administration

## 🧪 Testing

### Frontend Testing
```bash
cd frontend
npm test
```

### Backend Testing
```bash
cd backend
pip install -r tests/requirements.txt
python -m pytest tests/unit -v
AWS_SAM_STACK_NAME=<stack-name> python -m pytest tests/integration -v
```

## 🚀 Deployment

### Frontend (S3 Static Website)
```bash
cd frontend
.\deploy.ps1
```

### Backend (AWS SAM)
```bash
cd backend
sam deploy
```

### Git Workflow
```bash
# Initial upload
.\git-upload.ps1 -Initial

# Regular updates
.\git-upload.ps1 -Message "Description of changes"

# Quick update
.\git-upload.ps1
```

## 📊 Monitoring

- **CloudWatch Logs** - Lambda function logging
- **X-Ray Tracing** - Performance monitoring
- **DynamoDB Metrics** - Database performance
- **API Gateway Metrics** - API usage statistics

## 🔒 Security Features

- **XSS Protection** - Input sanitization and HTML escaping
- **CORS Configuration** - Proper cross-origin resource sharing
- **Environment Variables** - No hardcoded credentials
- **IAM Roles** - Least-privilege access principles
- **Cognito Integration** - Secure authentication and authorization

## 📚 Documentation

- [Git Scripts Manual](Git-Scripts-Manual.html) - PowerShell automation guide
- [User Manual](documentation/user-manual.html) - End-user guide
- [Technical Documentation](documentation/technical-design-manual.html) - Developer guide
- [API Documentation](backend/api.md) - Complete API reference

## 🐛 Troubleshooting

### Common Issues

**Access Denied**
- Check Cognito group membership
- Verify function permissions in Parameter Management

**Modules Not Visible**
- Check `function_permissions` configuration
- Ensure proper group assignments

**API Errors**
- Verify `.env` configuration
- Check AWS credentials and region settings

**Build/Deployment Issues**
- Run `.\fix-build.ps1` for frontend issues
- Check SAM template syntax for backend issues

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary to H-DCN organization.

## 📞 Support

For technical support or access rights questions, contact the H-DCN administrators.

---

**Version**: 1.0.0  
**Last Updated**: October 2025  
**Repository**: https://github.com/PeterGeers/h-dcn