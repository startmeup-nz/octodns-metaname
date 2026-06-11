# Functional Requirements

What octodns-metaname does.

## Core Functionality

### FR-1: OctoDNS Provider Interface
The module SHALL implement the OctoDNS Provider interface, enabling zone synchronization with Metaname DNS.

### FR-2: Record Type Support
The module SHALL support all DNS record types available in the Metaname API.

### FR-3: Zone Management
The module SHALL support creating, reading, updating, and deleting DNS zones.

### FR-4: Secret Management
The module SHALL support environment variable-based authentication (API key and account reference).

### FR-5: 1Password Integration
The module SHALL optionally integrate with op-opsdevnz for 1Password-based secret resolution.

## Testing

### FR-6: Test Coverage
The module SHALL maintain 100% test coverage to ensure reliability across two upstream dependencies.

### FR-7: Network Isolation
Tests SHALL use pytest-network to disable real network calls, with vcrpy for recorded API responses.

## Documentation

### FR-8: User Documentation
The module SHALL provide comprehensive documentation including installation, configuration, and usage examples.

### FR-9: API Documentation
The module SHALL document all public APIs and configuration options.

## Related

- [Non-Functional Requirements](NFR.md)
- [Design Decisions](../design/)
- [Getting Started](../index.md)
