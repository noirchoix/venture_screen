# Security and Data Handling

This service can receive confidential founder material and source repositories.

Production deployments should add:

1. authentication and tenant isolation;
2. encrypted object storage for uploaded artifacts;
3. explicit retention / deletion controls;
4. per-tenant rate and upload quotas;
5. malware scanning for uploads before longer-term storage;
6. redaction rules before sending any evidence to an optional external LLM;
7. audit logs for document access and screening runs.

Repository ZIPs are treated as data only. They are never executed by Venture Screening Intelligence.
