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

## Domain Lifecycle

### FR-6: Domain Availability Check
The module SHALL provide a `check_domain()` method that queries Metaname's `check_domain_name` RPC to determine domain availability.

### FR-7: Domain Registration
The module SHALL provide a `register_domain()` method that registers a domain via Metaname's `register_domain_name` RPC. Registration SHALL require an explicit `confirm=True` guardrail to prevent accidental registrations from automation workflows.

### FR-8: Domain Listing
The module SHALL provide a `list_domains()` method that lists all domains registered under the authenticated Metaname account.

## Testing

### FR-9: Test Coverage
The module SHALL maintain 100% test coverage to ensure reliability across two upstream dependencies.

### FR-10: Network Isolation
Tests SHALL use pytest-network to disable real network calls, with vcrpy for recorded API responses.

## Documentation

### FR-11: User Documentation
The module SHALL provide comprehensive documentation including installation, configuration, and usage examples.

### FR-12: API Documentation
The module SHALL document all public APIs and configuration options.

## Related

- [Non-Functional Requirements](NFR.md)
- [Design Decisions](../design/)
- [Getting Started](../index.md)
