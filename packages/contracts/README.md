# API contracts

The backend Pydantic models in `apps/api/app/schemas.py`, `digital_schemas.py`,
`verification_contracts.py`, and `api_contracts.py` define the API contracts.
Physical and digital responses add the same `WorkflowVerification` decision
envelope, preserving the original modality-specific result fields. Export the
current OpenAPI representation from the repository root:

```sh
npm run contracts
```

This writes `packages/contracts/openapi.json` using a temporary local store. The
frontend maintains its TypeScript interfaces in `apps/web/src/types/index.ts`;
they are not automatically generated. Review both sides when changing an API
contract. The running API also serves `/openapi.json` and `/docs`.
