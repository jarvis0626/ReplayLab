# API contracts

The backend Pydantic models in `apps/api/app/schemas.py` and `api_contracts.py` define the API contracts. Export their current OpenAPI representation from the repository root:

```sh
npm run contracts
```

This writes `packages/contracts/openapi.json` using a temporary local store. The frontend currently maintains its TypeScript interfaces in `apps/web/src/types.ts`; they are not automatically generated. Review both sides when changing an API contract. The running API also serves `/openapi.json` and `/docs`.
