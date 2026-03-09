# US-deploy-app: Deploy the Application Locally

**As a** self-hoster, **I want** to install and run the application with minimal commands and configuration, **so that** I can get started quickly without deep technical expertise.

**Status**: Approved

**Priority**: Should-have

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

**Related goal**: [GOAL-easy-deployment](../goals/GOAL-easy-deployment.md)

## Acceptance Criteria

- Given I have cloned the repository, when I follow the setup instructions, then the app is running in 5 or fewer terminal commands
- Given default configuration, when I start the app, then it works out of the box without editing config files
- Given I start the app, when it finishes initializing, then it displays the URL where the UI is accessible
- Given I follow the setup instructions on Linux or Windows, when I complete all steps, then the app runs successfully on both platforms
- Given I check the project documentation, then I find a clear list of all required dependencies and their versions

## Derived Requirements

- [REQ-USA-simple-setup](../requirements/REQ-USA-simple-setup.md) — Simple setup and startup
- [REQ-PORT-linux-windows](../requirements/REQ-PORT-linux-windows.md) — Linux and Windows runtime portability
