# CON-cross-platform: Cross-Platform Support

**Category**: Technical

**Status**: Active

**Source stakeholder**: [STK-self-hoster](../stakeholders.md)

## Description

The application must run on Linux and Windows. macOS is out of scope for the initial version.

## Rationale

Self-hosters use a variety of operating systems. Supporting Linux and Windows covers the vast majority of NVIDIA GPU setups, aligning with CON-nvidia-gpu and the easy-deployment goal. macOS is excluded because Apple dropped NVIDIA GPU support, making it incompatible with the CUDA-only inference constraint.

## Impact

- Dependencies must be available on both Linux and Windows (or have platform-specific alternatives).
- Installation and startup scripts must work on both platforms or provide OS-specific variants.
- File paths, process management, and system calls must avoid OS-specific assumptions between Linux and Windows.

## Related Artifacts

- [REQ-PORT-linux-windows](../requirements/REQ-PORT-linux-windows.md) — runtime portability across Linux and Windows
- [REQ-USA-simple-setup](../requirements/REQ-USA-simple-setup.md) — setup process works on both platforms
