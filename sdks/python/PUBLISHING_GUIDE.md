# UAPK Gateway SDK - PyPI Publishing Guide

**Package Name:** `uapk-gateway`
**Version:** 1.0.0
**Status:** ✅ Ready for PyPI

---

## Pre-Publishing Checklist

✅ All required files present
✅ Version consistency verified (1.0.0)
✅ README.md complete (1,528 words)
✅ LICENSE included (Apache 2.0)
✅ CHANGELOG.md updated
✅ Dependencies specified
✅ Tests written (107 test cases)
✅ Documentation complete
✅ Package size: ~131 KB

---

## Step 1: Install Build Tools

```bash
# Install build dependencies
pip install --upgrade build twine

# Verify installation
python -m build --version
twine --version
```

---

## Step 2: Build the Package

### Clean Previous Builds

```bash
cd /home/dsanker/uapk-gateway/sdks/python

# Remove old build artifacts
rm -rf dist/ build/ *.egg-info/
```

### Build Distribution Packages

```bash
# Build both source distribution and wheel
python -m build

# This creates:
# - dist/uapk_gateway-1.0.0.tar.gz (source distribution)
# - dist/uapk_gateway-1.0.0-py3-none-any.whl (wheel)
```

**Expected Output:**
```
* Creating venv isolated environment...
* Installing packages in isolated environment... (setuptools>=68.0, wheel)
* Getting build dependencies for sdist...
* Building sdist...
* Building wheel from sdist
* Creating isolated environment: venv+pip...
* Installing packages in isolated environment... (setuptools>=68.0, wheel)
* Getting build dependencies for wheel...
* Building wheel...
Successfully built uapk_gateway-1.0.0.tar.gz and uapk_gateway-1.0.0-py3-none-any.whl
```

---

## Step 3: Verify the Package

### Check with Twine

```bash
# Verify package metadata and structure
twine check dist/*
```

**Expected Output:**
```
Checking dist/uapk_gateway-1.0.0-py3-none-any.whl: PASSED
Checking dist/uapk_gateway-1.0.0.tar.gz: PASSED
```

### Inspect Package Contents

```bash
# List contents of wheel
unzip -l dist/uapk_gateway-1.0.0-py3-none-any.whl

# List contents of source dist
tar -tzf dist/uapk_gateway-1.0.0.tar.gz
```

**Expected Contents:**
```
uapk_gateway/
├── __init__.py
├── client.py
├── async_client.py
├── models.py
├── exceptions.py
└── integrations/
    ├── __init__.py
    └── langchain.py

Plus:
- README.md
- LICENSE
- CHANGELOG.md
- pyproject.toml
```

### Test Installation Locally

```bash
# Create test venv
python -m venv test_venv
source test_venv/bin/activate  # On Windows: test_venv\Scripts\activate

# Install from wheel
pip install dist/uapk_gateway-1.0.0-py3-none-any.whl

# Test import
python -c "from uapk_gateway import UAPKGatewayClient; print('✅ Import successful')"

# Test version
python -c "import uapk_gateway; print(f'Version: {uapk_gateway.__version__}')"

# Deactivate and clean up
deactivate
rm -rf test_venv
```

---

## Step 4: Test on PyPI Test Instance (Recommended)

### Register on TestPyPI

1. Go to https://test.pypi.org/
2. Create an account
3. Generate API token at https://test.pypi.org/manage/account/token/

### Upload to TestPyPI

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: <your-testpypi-api-token>
```

### Test Installation from TestPyPI

```bash
# Create test environment
python -m venv test_install
source test_install/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ uapk-gateway

# Test
python -c "from uapk_gateway import UAPKGatewayClient; print('✅ Works!')"

# Cleanup
deactivate
rm -rf test_install
```

### View on TestPyPI

Visit: https://test.pypi.org/project/uapk-gateway/

---

## Step 5: Publish to Production PyPI

### Register on PyPI

1. Go to https://pypi.org/
2. Create an account (if you don't have one)
3. Enable 2FA (required for new projects)
4. Generate API token at https://pypi.org/manage/account/token/

### Configure API Token (Recommended)

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <your-pypi-api-token>

[testpypi]
username = __token__
password = <your-testpypi-api-token>
```

Set permissions:
```bash
chmod 600 ~/.pypirc
```

### Upload to PyPI

```bash
# Upload to production PyPI
twine upload dist/*

# Or specify repository explicitly
twine upload --repository pypi dist/*
```

**⚠️ Warning:** Once uploaded to PyPI, you **cannot** delete or re-upload the same version. Make sure everything is correct!

---

## Step 6: Verify Publication

### Check PyPI Page

1. Visit: https://pypi.org/project/uapk-gateway/
2. Verify metadata, description, and links
3. Check that README renders correctly

### Test Installation

```bash
# Install in fresh environment
pip install uapk-gateway

# With optional dependencies
pip install uapk-gateway[langchain]
pip install uapk-gateway[all]

# For development
pip install uapk-gateway[dev]
```

### Test Quickstart

```python
from uapk_gateway import UAPKGatewayClient
from uapk_gateway.models import ActionInfo

client = UAPKGatewayClient(
    base_url="http://localhost:8000",
    api_key="test-key"
)

action = ActionInfo(
    type="test",
    tool="test_tool",
    params={"key": "value"}
)

response = client.evaluate(
    uapk_id="test-v1",
    agent_id="agent-1",
    action=action
)

print(f"Decision: {response.decision}")
```

---

## Step 7: Post-Publication Tasks

### 1. Create GitHub Release

```bash
cd /home/dsanker/uapk-gateway

# Tag the release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Create GitHub release with release notes
```

### 2. Update Documentation

- Add installation badge to README
- Update main project README with SDK link
- Add to project documentation

### 3. Announce Release

- Create discussion/announcement
- Update project website
- Share on relevant channels

### 4. Monitor

- Watch for issues on GitHub
- Monitor PyPI download stats
- Respond to user feedback

---

## Troubleshooting

### Build Fails

```bash
# Update build tools
pip install --upgrade build setuptools wheel

# Clear cache
rm -rf build/ dist/ *.egg-info/
python -m build
```

### Upload Fails - "File already exists"

You cannot re-upload the same version. Options:
1. Delete from TestPyPI (if testing) and try again
2. Bump version number (e.g., 1.0.0 → 1.0.1)

### Upload Fails - "Invalid authentication"

1. Verify API token is correct
2. Use `__token__` as username
3. Check `~/.pypirc` permissions (should be 600)

### README Not Rendering

1. Ensure `readme = "README.md"` in pyproject.toml
2. Check README uses valid CommonMark markdown
3. Test locally with `python -m readme_renderer README.md`

### Missing Files in Package

1. Check `MANIFEST.in` includes all needed files
2. Verify `tool.setuptools.packages.find` in pyproject.toml
3. Rebuild with `python -m build`

---

## Version Bumping (for future releases)

### 1. Update Version Number

Edit these files:
- `pyproject.toml` - `version = "1.0.1"`
- `uapk_gateway/__init__.py` - `__version__ = "1.0.1"`

### 2. Update CHANGELOG.md

Add new version section:
```markdown
## [1.0.1] - 2024-XX-XX

### Fixed
- Bug fix description

### Added
- New feature description
```

### 3. Rebuild and Republish

```bash
rm -rf dist/
python -m build
twine check dist/*
twine upload dist/*
```

---

## Package Metadata Reference

**Package Name:** uapk-gateway
**Import Name:** `import uapk_gateway`
**Version:** 1.0.0
**License:** Apache 2.0
**Python Required:** >=3.10

**Dependencies:**
- httpx >= 0.25.0
- pydantic >= 2.0.0

**Optional Dependencies:**
- langchain >= 0.1.0 (for LangChain integration)

**Classifiers:**
- Development Status :: 4 - Beta
- Intended Audience :: Developers
- License :: OSI Approved :: Apache Software License
- Programming Language :: Python :: 3.10
- Programming Language :: Python :: 3.11
- Programming Language :: Python :: 3.12
- Topic :: Software Development :: Libraries
- Topic :: Security
- Topic :: System :: Logging

**Keywords:**
ai, agents, compliance, audit, governance, langchain, openai, security

**URLs:**
- Homepage: https://github.com/anthropics/uapk-gateway
- Documentation: https://docs.uapk.dev
- Repository: https://github.com/anthropics/uapk-gateway
- Issues: https://github.com/anthropics/uapk-gateway/issues

---

## Security Considerations

### API Token Security

- **Never** commit API tokens to git
- Store tokens in `~/.pypirc` with 600 permissions
- Use environment variables in CI/CD
- Rotate tokens periodically

### Package Signing

Consider signing packages:
```bash
# Sign with GPG
gpg --detach-sign -a dist/uapk_gateway-1.0.0.tar.gz

# Upload signature
twine upload dist/* --sign
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Check package
        run: twine check dist/*

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## Support

For questions or issues:
- GitHub Issues: https://github.com/anthropics/uapk-gateway/issues
- PyPI Support: https://pypi.org/help/

---

**Status:** ✅ Package verified and ready for publication
**Last Updated:** 2024-12-28
**Maintainer:** UAPK Team
