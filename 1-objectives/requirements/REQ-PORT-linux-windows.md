# REQ-PORT-linux-windows: Linux and Windows Runtime Portability

**Type**: Portability

**Status**: Approved

**Priority**: Must-have

**Source**: [GOAL-easy-deployment](../goals/GOAL-easy-deployment.md), [US-deploy-app](../user-stories/US-deploy-app.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The application shall run on both Linux and Windows without platform-specific workarounds from the user. File paths, process management, system calls, and dependencies must be handled in a cross-platform manner or provide transparent OS-specific alternatives.

## Acceptance Criteria

- Given the application is installed on Linux, when the user starts it, then it runs correctly without OS-specific manual steps beyond documented setup
- Given the application is installed on Windows, when the user starts it, then it runs correctly without OS-specific manual steps beyond documented setup
- Given the codebase, then no hardcoded OS-specific file paths, shell commands, or assumptions exist that would break on the other supported platform

## Related Constraints

- [CON-cross-platform](../constraints/CON-cross-platform.md) — must run on Linux and Windows; macOS out of scope
