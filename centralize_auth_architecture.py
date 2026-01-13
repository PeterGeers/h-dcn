#!/usr/bin/env python3
"""
Centralize Authentication Architecture Script

This script identifies and fixes the scattered JWT/CORS/auth implementations
across the H-DCN codebase to create a single source of truth.

Usage: python centralize_auth_architecture.py --analyze
       python centralize_auth_architecture.py --fix-backend
       python centralize_auth_architecture.py --fix-frontend
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple

class AuthArchitectureCentralizer:
    def __init__(self):
        self.backend_path = Path("backend")
        self.frontend_path = Path("frontend")
        self.issues_found = []
        
    def analyze_current_state(self) -> Dict:
        """Analyze current authentication architecture and identify issues"""
        print("🔍 Analyzing Current Authentication Architecture")
        print("=" * 60)
        
        analysis = {
            'backend_auth_files': self.find_backend_auth_files(),
            'frontend_auth_files': self.find_frontend_auth_files(),
            'cors_implementations': self.find_cors_implementations(),
            'jwt_handlers': self.find_jwt_handlers(),
            'issues': []
        }
        
        # Analyze issues
        self.analyze_backend_duplication(analysis)
        self.analyze_frontend_duplication(analysis)
        self.analyze_cors_consistency(analysis)
        
        return analysis
    
    def find_backend_auth_files(self) -> List[Dict]:
        """Find all backend authentication-related files"""
        auth_files = []
        
        # Find auth_fallback.py files (these should be removed)
        for auth_file in self.backend_path.rglob("auth_fallback.py"):
            auth_files.append({
                'path': str(auth_file),
                'type': 'auth_fallback',
                'status': 'SHOULD_REMOVE',
                'reason': 'Duplicates shared auth logic'
            })
        
        # Find handlers using shared auth (these are good)
        for handler_file in self.backend_path.rglob("app.py"):
            if self.uses_shared_auth(handler_file):
                auth_files.append({
                    'path': str(handler_file),
                    'type': 'shared_auth_user',
                    'status': 'GOOD',
                    'reason': 'Uses centralized shared auth'
                })
            else:
                auth_files.append({
                    'path': str(handler_file),
                    'type': 'no_shared_auth',
                    'status': 'NEEDS_UPDATE',
                    'reason': 'Should use shared auth utils'
                })
        
        return auth_files
    
    def find_frontend_auth_files(self) -> List[Dict]:
        """Find all frontend authentication-related files"""
        auth_files = []
        
        # Find createAuthConfig implementations (duplicates)
        for ts_file in self.frontend_path.rglob("*.ts"):
            if self.has_create_auth_config(ts_file):
                auth_files.append({
                    'path': str(ts_file),
                    'type': 'create_auth_config',
                    'status': 'SHOULD_REMOVE',
                    'reason': 'Duplicates main ApiService auth'
                })
        
        # Find getAuthHeaders implementations
        for ts_file in self.frontend_path.rglob("*.ts"):
            if self.has_get_auth_headers(ts_file):
                if 'utils/authHeaders.ts' in str(ts_file):
                    auth_files.append({
                        'path': str(ts_file),
                        'type': 'main_auth_headers',
                        'status': 'GOOD',
                        'reason': 'Main auth headers implementation'
                    })
                else:
                    auth_files.append({
                        'path': str(ts_file),
                        'type': 'duplicate_auth_headers',
                        'status': 'SHOULD_REMOVE',
                        'reason': 'Duplicates main auth headers'
                    })
        
        return auth_files
    
    def find_cors_implementations(self) -> List[Dict]:
        """Find CORS implementations across the codebase"""
        cors_implementations = []
        
        # Backend CORS in individual handlers
        for py_file in self.backend_path.rglob("*.py"):
            cors_headers = self.extract_cors_headers(py_file)
            if cors_headers:
                cors_implementations.append({
                    'path': str(py_file),
                    'type': 'individual_cors',
                    'headers': cors_headers,
                    'status': 'CHECK_CONSISTENCY'
                })
        
        return cors_implementations
    
    def find_jwt_handlers(self) -> List[Dict]:
        """Find JWT handling implementations"""
        jwt_handlers = []
        
        # Backend JWT handlers
        for py_file in self.backend_path.rglob("*.py"):
            if self.has_jwt_handling(py_file):
                jwt_handlers.append({
                    'path': str(py_file),
                    'type': 'backend_jwt',
                    'implementation': self.get_jwt_implementation_type(py_file)
                })
        
        # Frontend JWT handlers
        for ts_file in self.frontend_path.rglob("*.ts"):
            if self.has_jwt_handling_frontend(ts_file):
                jwt_handlers.append({
                    'path': str(ts_file),
                    'type': 'frontend_jwt',
                    'implementation': self.get_jwt_implementation_type_frontend(ts_file)
                })
        
        return jwt_handlers
    
    def uses_shared_auth(self, file_path: Path) -> bool:
        """Check if a handler uses shared auth utils"""
        try:
            content = file_path.read_text()
            return 'from shared.auth_utils import' in content
        except:
            return False
    
    def has_create_auth_config(self, file_path: Path) -> bool:
        """Check if file has createAuthConfig function"""
        try:
            content = file_path.read_text()
            return 'createAuthConfig' in content and 'const createAuthConfig' in content
        except:
            return False
    
    def has_get_auth_headers(self, file_path: Path) -> bool:
        """Check if file has getAuthHeaders function"""
        try:
            content = file_path.read_text()
            return 'getAuthHeaders' in content and ('export const getAuthHeaders' in content or 'const getAuthHeaders' in content)
        except:
            return False
    
    def extract_cors_headers(self, file_path: Path) -> Dict:
        """Extract CORS headers from a file"""
        try:
            content = file_path.read_text()
            if 'cors_headers' in content or 'Access-Control-Allow' in content:
                # Extract CORS configuration
                cors_match = re.search(r'Access-Control-Allow-Origin.*?["\']([^"\']+)["\']', content)
                if cors_match:
                    return {'origin': cors_match.group(1)}
            return {}
        except:
            return {}
    
    def has_jwt_handling(self, file_path: Path) -> bool:
        """Check if file handles JWT tokens"""
        try:
            content = file_path.read_text()
            jwt_indicators = ['jwt_token', 'Bearer ', 'Authorization', 'base64.urlsafe_b64decode']
            return any(indicator in content for indicator in jwt_indicators)
        except:
            return False
    
    def has_jwt_handling_frontend(self, file_path: Path) -> bool:
        """Check if frontend file handles JWT tokens"""
        try:
            content = file_path.read_text()
            jwt_indicators = ['jwtToken', 'Bearer', 'Authorization', 'atob(']
            return any(indicator in content for indicator in jwt_indicators)
        except:
            return False
    
    def get_jwt_implementation_type(self, file_path: Path) -> str:
        """Determine JWT implementation type in backend file"""
        try:
            content = file_path.read_text()
            if 'extract_user_credentials' in content:
                return 'shared_auth'
            elif 'base64.urlsafe_b64decode' in content:
                return 'manual_jwt'
            else:
                return 'unknown'
        except:
            return 'error'
    
    def get_jwt_implementation_type_frontend(self, file_path: Path) -> str:
        """Determine JWT implementation type in frontend file"""
        try:
            content = file_path.read_text()
            if 'getAuthHeaders' in content:
                return 'auth_headers_service'
            elif 'createAuthConfig' in content:
                return 'create_auth_config'
            else:
                return 'manual_jwt'
        except:
            return 'error'
    
    def analyze_backend_duplication(self, analysis: Dict):
        """Analyze backend authentication duplication"""
        auth_fallback_files = [f for f in analysis['backend_auth_files'] if f['type'] == 'auth_fallback']
        no_shared_auth_files = [f for f in analysis['backend_auth_files'] if f['type'] == 'no_shared_auth']
        
        if auth_fallback_files:
            analysis['issues'].append({
                'type': 'backend_duplication',
                'severity': 'HIGH',
                'description': f'Found {len(auth_fallback_files)} auth_fallback.py files that duplicate shared auth logic',
                'files': [f['path'] for f in auth_fallback_files],
                'solution': 'Remove auth_fallback.py files and ensure handlers use shared auth'
            })
        
        if no_shared_auth_files:
            analysis['issues'].append({
                'type': 'backend_inconsistency',
                'severity': 'MEDIUM',
                'description': f'Found {len(no_shared_auth_files)} handlers not using shared auth',
                'files': [f['path'] for f in no_shared_auth_files],
                'solution': 'Update handlers to import and use shared auth utils'
            })
    
    def analyze_frontend_duplication(self, analysis: Dict):
        """Analyze frontend authentication duplication"""
        create_auth_files = [f for f in analysis['frontend_auth_files'] if f['type'] == 'create_auth_config']
        duplicate_auth_files = [f for f in analysis['frontend_auth_files'] if f['type'] == 'duplicate_auth_headers']
        
        if create_auth_files:
            analysis['issues'].append({
                'type': 'frontend_duplication',
                'severity': 'HIGH',
                'description': f'Found {len(create_auth_files)} createAuthConfig implementations',
                'files': [f['path'] for f in create_auth_files],
                'solution': 'Replace createAuthConfig with main ApiService calls'
            })
        
        if duplicate_auth_files:
            analysis['issues'].append({
                'type': 'frontend_auth_duplication',
                'severity': 'MEDIUM',
                'description': f'Found {len(duplicate_auth_files)} duplicate getAuthHeaders implementations',
                'files': [f['path'] for f in duplicate_auth_files],
                'solution': 'Remove duplicate implementations, use main authHeaders.ts'
            })
    
    def analyze_cors_consistency(self, analysis: Dict):
        """Analyze CORS consistency across implementations"""
        cors_implementations = analysis['cors_implementations']
        if len(cors_implementations) > 1:
            # Check for inconsistencies
            origins = set()
            for impl in cors_implementations:
                if 'origin' in impl['headers']:
                    origins.add(impl['headers']['origin'])
            
            if len(origins) > 1:
                analysis['issues'].append({
                    'type': 'cors_inconsistency',
                    'severity': 'MEDIUM',
                    'description': f'Found inconsistent CORS origins: {list(origins)}',
                    'files': [impl['path'] for impl in cors_implementations],
                    'solution': 'Use global CORS configuration in template.yaml'
                })
    
    def print_analysis_report(self, analysis: Dict):
        """Print detailed analysis report"""
        print("\n📊 AUTHENTICATION ARCHITECTURE ANALYSIS REPORT")
        print("=" * 60)
        
        # Summary
        total_issues = len(analysis['issues'])
        high_severity = len([i for i in analysis['issues'] if i['severity'] == 'HIGH'])
        medium_severity = len([i for i in analysis['issues'] if i['severity'] == 'MEDIUM'])
        
        print(f"\n🎯 SUMMARY:")
        print(f"   Total Issues Found: {total_issues}")
        print(f"   High Severity: {high_severity}")
        print(f"   Medium Severity: {medium_severity}")
        
        # Backend files
        print(f"\n🔧 BACKEND AUTH FILES:")
        for file_info in analysis['backend_auth_files']:
            status_emoji = "✅" if file_info['status'] == 'GOOD' else "❌" if file_info['status'] == 'SHOULD_REMOVE' else "⚠️"
            print(f"   {status_emoji} {file_info['path']} - {file_info['reason']}")
        
        # Frontend files
        print(f"\n🌐 FRONTEND AUTH FILES:")
        for file_info in analysis['frontend_auth_files']:
            status_emoji = "✅" if file_info['status'] == 'GOOD' else "❌" if file_info['status'] == 'SHOULD_REMOVE' else "⚠️"
            print(f"   {status_emoji} {file_info['path']} - {file_info['reason']}")
        
        # Issues
        print(f"\n🚨 ISSUES FOUND:")
        for i, issue in enumerate(analysis['issues'], 1):
            severity_emoji = "🔴" if issue['severity'] == 'HIGH' else "🟡"
            print(f"\n   {severity_emoji} Issue {i}: {issue['type'].upper()}")
            print(f"      Description: {issue['description']}")
            print(f"      Solution: {issue['solution']}")
            if len(issue['files']) <= 3:
                for file_path in issue['files']:
                    print(f"      - {file_path}")
            else:
                for file_path in issue['files'][:3]:
                    print(f"      - {file_path}")
                print(f"      ... and {len(issue['files']) - 3} more files")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Remove {len([f for f in analysis['backend_auth_files'] if f['status'] == 'SHOULD_REMOVE'])} duplicate backend auth files")
        print(f"   2. Remove {len([f for f in analysis['frontend_auth_files'] if f['status'] == 'SHOULD_REMOVE'])} duplicate frontend auth files")
        print(f"   3. Standardize all handlers to use shared auth utils")
        print(f"   4. Use single ApiService for all frontend API calls")
        print(f"   5. Rely on global CORS configuration in template.yaml")
        
        return analysis

def main():
    import sys
    
    centralizer = AuthArchitectureCentralizer()
    
    if len(sys.argv) < 2:
        print("Usage: python centralize_auth_architecture.py --analyze")
        return
    
    command = sys.argv[1]
    
    if command == "--analyze":
        analysis = centralizer.analyze_current_state()
        centralizer.print_analysis_report(analysis)
        
        # Save analysis to file
        with open('auth_architecture_analysis.json', 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"\n💾 Analysis saved to: auth_architecture_analysis.json")
        
    else:
        print("Available commands: --analyze")

if __name__ == "__main__":
    main()