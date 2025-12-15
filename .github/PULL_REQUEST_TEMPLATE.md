## Description

<!-- What does this PR do? Why is it needed? -->

## Type of Change

<!-- Mark with [x] -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test coverage improvement
- [ ] New validator/visitor (extensibility)

## Related Issues

<!-- Link related issues: Fixes #123, Closes #456 -->

## Checklist

### Required
- [ ] My code follows the project's style guidelines
- [ ] I have run `make check` and all checks pass
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass with `make test`

### If adding domain types
- [ ] frozen dataclass with `__post_init__` FAIL-FIRST validation
- [ ] Added to `domain/model/__init__.py` re-exports

### If adding validator/visitor
- [ ] Implements Protocol (ValidatorProtocol/VisitorProtocol)
- [ ] Added to registry tuple in `_registry.py`
- [ ] Has `from_config()` that returns `None` if disabled

### If adding config field
- [ ] Added to `ArchitectureConfig` with `| None` (disabled by default)
- [ ] Added validation in `__post_init__`

### Documentation
- [ ] I have updated documentation if needed
- [ ] I have updated CHANGELOG.md (if applicable)

## Testing

<!-- How has this been tested? -->

## Screenshots (if applicable)

<!-- Add screenshots for UI changes -->
