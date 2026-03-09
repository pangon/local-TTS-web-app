# REQ-USA-simple-setup: Simple Setup and Startup

**Type**: Usability

**Status**: Draft

**Priority**: Should-have

**Source**: [US-deploy-app](../user-stories/US-deploy-app.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The application shall be runnable with 5 or fewer terminal commands from a fresh clone, work out of the box without editing config files, and display the UI URL upon startup. Required dependencies and their versions shall be documented.

## Acceptance Criteria

- Given a fresh clone of the repository, when the user follows the setup instructions, then the app is running in 5 or fewer terminal commands
- Given default configuration, when the user starts the app, then it works without editing any config files
- Given the app finishes initializing, then it displays the URL where the UI is accessible
- Given the project documentation, then a clear list of all required dependencies and their versions is available

## Related Constraints

- [CON-cross-platform](../constraints/CON-cross-platform.md) — setup must work on Linux and Windows
- [CON-solo-developer](../constraints/CON-solo-developer.md) — simplicity is favored due to solo maintenance
