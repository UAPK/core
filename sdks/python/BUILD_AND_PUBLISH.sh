#!/bin/bash
# Complete build and publish workflow for UAPK Gateway SDK

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "======================================================================"
echo "UAPK Gateway Python SDK - Build and Publish"
echo "======================================================================"
echo ""

# Function to print colored output
print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Parse command line arguments
MODE="check"  # Default mode
if [ $# -gt 0 ]; then
    MODE="$1"
fi

case "$MODE" in
    check)
        echo "Mode: Verification Only (no build)"
        ;;
    build)
        echo "Mode: Build Only (no upload)"
        ;;
    testpypi)
        echo "Mode: Build and Upload to TestPyPI"
        ;;
    pypi)
        echo "Mode: Build and Upload to Production PyPI"
        print_warning "This will publish to PRODUCTION PyPI!"
        read -p "Are you sure? (yes/no) " -n 3 -r
        echo
        if [[ ! $REPLY =~ ^yes$ ]]; then
            echo "Cancelled."
            exit 0
        fi
        ;;
    *)
        echo "Usage: $0 [check|build|testpypi|pypi]"
        echo ""
        echo "Modes:"
        echo "  check     - Verify package is ready (default)"
        echo "  build     - Build distribution packages"
        echo "  testpypi  - Build and upload to TestPyPI"
        echo "  pypi      - Build and upload to Production PyPI"
        exit 1
        ;;
esac

echo ""

# Step 1: Verify package structure
print_step "Step 1: Verifying package structure..."
if python3 verify_package.py > /tmp/verify_output.txt 2>&1; then
    print_success "Package structure verified"
    cat /tmp/verify_output.txt | grep "Summary" -A 10
else
    print_error "Package verification failed"
    cat /tmp/verify_output.txt
    exit 1
fi

echo ""

# Step 2: Run tests (if pytest available)
print_step "Step 2: Running tests..."
if command -v pytest &> /dev/null; then
    if pytest -q 2>&1; then
        print_success "All tests passed"
    else
        print_error "Tests failed"
        exit 1
    fi
else
    print_warning "pytest not available, skipping tests"
    echo "   Install with: pip install -e \".[dev]\""
fi

echo ""

# Exit if only checking
if [ "$MODE" = "check" ]; then
    print_success "Verification complete! Package is ready."
    echo ""
    echo "Next steps:"
    echo "  Build:         $0 build"
    echo "  Test upload:   $0 testpypi"
    echo "  Prod upload:   $0 pypi"
    exit 0
fi

# Step 3: Clean previous builds
print_step "Step 3: Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/
print_success "Build directories cleaned"

echo ""

# Step 4: Build packages
print_step "Step 4: Building distribution packages..."

if ! command -v python3 -m build &> /dev/null; then
    print_error "build module not available"
    echo "Install with: pip install build"
    exit 1
fi

if python3 -m build; then
    print_success "Build complete"
    echo ""
    echo "Packages created:"
    ls -lh dist/
else
    print_error "Build failed"
    exit 1
fi

echo ""

# Step 5: Check packages with twine
print_step "Step 5: Checking packages with twine..."

if ! command -v twine &> /dev/null; then
    print_warning "twine not available"
    echo "Install with: pip install twine"
    echo "Skipping package check"
else
    if twine check dist/*; then
        print_success "Package check passed"
    else
        print_error "Package check failed"
        exit 1
    fi
fi

echo ""

# Exit if only building
if [ "$MODE" = "build" ]; then
    print_success "Build complete!"
    echo ""
    echo "Distribution packages:"
    ls -1 dist/
    echo ""
    echo "Next steps:"
    echo "  Check:         twine check dist/*"
    echo "  Test upload:   $0 testpypi"
    echo "  Prod upload:   $0 pypi"
    exit 0
fi

# Step 6: Upload to PyPI
print_step "Step 6: Uploading to PyPI..."

if ! command -v twine &> /dev/null; then
    print_error "twine not available"
    echo "Install with: pip install twine"
    exit 1
fi

if [ "$MODE" = "testpypi" ]; then
    echo "Uploading to TestPyPI..."
    if twine upload --repository testpypi dist/*; then
        print_success "Upload to TestPyPI successful!"
        echo ""
        echo "View at: https://test.pypi.org/project/uapk-gateway/"
        echo ""
        echo "Test installation:"
        echo "  pip install --index-url https://test.pypi.org/simple/ \\"
        echo "    --extra-index-url https://pypi.org/simple/ uapk-gateway"
    else
        print_error "Upload to TestPyPI failed"
        exit 1
    fi
elif [ "$MODE" = "pypi" ]; then
    echo "Uploading to Production PyPI..."
    if twine upload dist/*; then
        print_success "Upload to PyPI successful!"
        echo ""
        echo "🎉 Package published!"
        echo ""
        echo "View at: https://pypi.org/project/uapk-gateway/"
        echo ""
        echo "Install:"
        echo "  pip install uapk-gateway"
        echo ""
        echo "Next steps:"
        echo "  1. Create GitHub release (git tag v1.0.0)"
        echo "  2. Update documentation"
        echo "  3. Announce release"
    else
        print_error "Upload to PyPI failed"
        exit 1
    fi
fi

echo ""
echo "======================================================================"
print_success "Complete!"
echo "======================================================================"
echo ""
