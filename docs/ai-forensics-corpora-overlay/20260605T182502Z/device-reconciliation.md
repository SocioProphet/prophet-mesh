# Device Reconciliation Notes v0.2

## Rule

Do not collapse device lanes unless at least two of the following match:
- Serial number
- Hardware model identifier
- Hostname
- OS/build timeline
- Purchase/activation record
- Primary artifact path
- AppleCare/support case identifier

## Known reconciliation issue

The AI Forensics Corpora Device Registry currently has a HellBook-Brick lane described as a MacBook Air M2 2022 / Mac14,2 in active 2026 investigation context.

The retained Apple timeline also has a 2025 MacBook Air M3 / Mac16,12 purchased May 11 2025, initially macOS 15.3 and later 15.6.

These must not be silently merged. Add either:
1. a separate 2025 M3 Mac device row, or
2. a correction note proving the retained M3 lane maps to an existing corpus device.

Until resolved, evidence referencing these machines should use device_id UNKNOWN or a provisional device ID.
