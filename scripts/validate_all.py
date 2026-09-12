"""
Master validation script - runs all validation checks
Use this after any script that modifies Python files
"""
import subprocess
import sys

def run_check(name, command):
    """Run a validation check and return success status"""
    print(f"\n{'='*60}")
    print(f"🔍 {name}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True)
    
    if result.returncode != 0:
        print(f"\n❌ {name} FAILED!")
        return False
    else:
        print(f"\n✅ {name} PASSED!")
        return True

def main():
    """Run all validation checks"""
    print("🔍 Running all validation checks...")
    print("="*60)
    
    checks = [
        ("Python Syntax Validation", "python scripts/validate_python_syntax.py"),
        ("Handler Integrity Check", "python scripts/check_handler_integrity.py"),
    ]
    
    results = []
    for name, command in checks:
        success = run_check(name, command)
        results.append((name, success))
    
    # Summary
    print("\n" + "="*60)
    print("📊 VALIDATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")
        if not success:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n✅ All validation checks passed!")
        sys.exit(0)
    else:
        print("\n❌ Some validation checks failed!")
        print("🔧 Fix the issues above before deploying")
        sys.exit(1)

if __name__ == '__main__':
    main()
