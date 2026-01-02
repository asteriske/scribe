# Contributing to Scribe

Thank you for your interest in contributing to Scribe! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check existing issues to avoid duplicates
2. Verify the bug on the latest version
3. Collect relevant information (logs, environment, steps to reproduce)

Create a bug report with:
- Clear, descriptive title
- Detailed description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or screenshots

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
1. Check if the feature has already been suggested
2. Provide a clear use case
3. Explain how it benefits users
4. Consider implementation complexity

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/scribe.git
   cd scribe
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set up development environment**
   ```bash
   # See docs/SETUP.md and docs/DEVELOPMENT.md
   cd transcriber && python -m venv venv && source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

4. **Make your changes**
   - Write clean, documented code
   - Follow existing code style (PEP 8, Black formatting)
   - Add tests for new functionality
   - Update documentation as needed

5. **Test your changes**
   ```bash
   # Run tests
   pytest

   # Check code style
   black .
   flake8 .

   # Type checking
   mypy .
   ```

6. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: your feature description"
   ```

   Commit message guidelines:
   - Use present tense ("Add feature" not "Added feature")
   - Use imperative mood ("Move cursor to..." not "Moves cursor to...")
   - First line: concise summary (50 chars or less)
   - Blank line, then detailed description if needed

7. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**
   - Provide a clear title and description
   - Reference any related issues
   - Describe what changed and why
   - Include screenshots for UI changes

## Development Guidelines

### Code Style

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Maximum line length: 100 characters
- Use type hints
- Write docstrings (Google style)

### Testing

- Write tests for new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use meaningful test names

### Documentation

Update documentation when:
- Adding new features
- Changing APIs
- Modifying configuration
- Changing setup/deployment

Documentation locations:
- `README.md` - Overview and quick start
- `docs/ARCHITECTURE.md` - System design
- `docs/API.md` - API specifications
- `docs/DATABASE.md` - Database schema
- `docs/SETUP.md` - Setup instructions
- `docs/DEVELOPMENT.md` - Development guide
- Code comments - Complex logic only

### Commit Guidelines

Good commit messages:
```
Add YouTube playlist batch processing

- Implement playlist URL parsing
- Add batch job queue
- Update UI with batch progress indicator
- Add tests for playlist functionality

Closes #123
```

Bad commit messages:
```
fix stuff
```

### Areas for Contribution

**High Priority:**
- Full-text search implementation
- Batch processing support
- Error handling improvements
- Test coverage expansion
- Performance optimizations

**Medium Priority:**
- Additional export formats
- UI/UX improvements
- Better progress indicators
- Documentation improvements

**Low Priority:**
- Analytics dashboard
- User authentication
- Advanced features (RAG, summarization)

### Getting Help

- Read `docs/DEVELOPMENT.md` for development setup
- Check existing issues and PRs
- Ask questions in issue comments
- Be patient - this is a volunteer project

## Review Process

1. **Automated checks**
   - Tests must pass
   - Code style must be clean
   - No type errors

2. **Manual review**
   - Code quality and clarity
   - Test coverage
   - Documentation completeness
   - Adherence to project architecture

3. **Feedback**
   - Address review comments
   - Update PR as needed
   - Discuss design decisions

4. **Merge**
   - Approved PRs will be merged
   - Squash or rebase as appropriate
   - Credit given in CHANGELOG

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue with the `question` label.

Thank you for contributing!
