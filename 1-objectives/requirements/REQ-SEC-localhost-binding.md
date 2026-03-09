# REQ-SEC-localhost-binding: Localhost-Only Network Binding

**Type**: Security

**Status**: Approved

**Priority**: Must-have

**Source**: [CON-single-user](../constraints/CON-single-user.md)

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The web server shall bind to `127.0.0.1` (localhost) by default. The application shall not be accessible from other devices on the network unless the user explicitly overrides the bind address.

## Acceptance Criteria

- Given default configuration, when the app starts, then the web server listens on `127.0.0.1` only
- Given another device on the same network, when it attempts to access the app's port, then the connection is refused
- Given the user explicitly sets a different bind address (e.g., `0.0.0.0`), when the app starts, then it binds to the specified address

## Related Constraints

- [CON-single-user](../constraints/CON-single-user.md) — single-user deployment means the app should not be exposed to the network by default
