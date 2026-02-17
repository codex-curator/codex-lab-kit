# Contributing to Codex Lab Kit

Thank you for your interest in contributing to the Golden Codex Lab Validation Kit!

## How to Contribute

### Reporting Issues
- Use GitHub Issues to report bugs or request features
- Include your Python version, OS, and steps to reproduce

### Running Experiments
The most valuable contribution is running the validation protocol on your hardware:

1. Install the kit: `pip install codex-lab-kit`
2. Run the calibration wizard for your setup
3. Execute the experiment protocol
4. Share your anonymized results

### Submitting Code
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests: `python3 -m pytest tests/ -v`
5. Submit a Pull Request

### Code Style
- Follow PEP 8
- Add type hints to public APIs
- Include docstrings for public classes and methods

### Adding Dataset Support
We welcome contributions that extend the framework to new object datasets beyond YCB:
- Implement a loader following the pattern in `codex_lab_kit/`
- Include ground-truth physical properties where available
- Document the dataset source and license

## Code of Conduct
Be respectful, constructive, and collaborative. We're building this together.

## Questions?
- Open a GitHub Discussion
- Visit [iaeternum.ai/robotics](https://iaeternum.ai/robotics)
- Email: research@iaeternum.ai
