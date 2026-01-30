# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

### Added
- Added `AGENTS.md` with guidance on LaTeX in Python f-strings and a checklist for adding experiments.
- Added developer notes to `README.md` covering LaTeX brace escaping and key code locations.

### Fixed
- Escaped LaTeX braces in the natural-convection explanation f-string to prevent a runtime
  `NameError: name 'exp' is not defined`.

