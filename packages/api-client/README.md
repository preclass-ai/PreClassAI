# @preclass/api-client

Typed client for the PreClass API. Types are generated from `apps/api/openapi/openapi.json`; CI fails if
`src/schema.d.ts` is out of date.

```bash
cd packages/api-client
npm ci            # install
npm run gen:api   # regenerate src/schema.d.ts after the OpenAPI file changes
npm run typecheck
```

## Use

```ts
import { createApiClient, isProblem } from "@preclass/api-client";

const api = createApiClient();            // same origin; cookie + X-PreClass-CSRF are sent for you

const { data: me, error } = await api.POST("/v1/auth/login", {
  body: { identifier: "gv.dia@preclass.local", password: "preclass-demo" },
});
if (error) console.log(error.code);       // "INVALID_CREDENTIALS"

const { data } = await api.GET("/v1/classes");
```

## Errors (RFC 9457)

`error` is a `Problem` (`{type, title, status, detail, code, errors?}`). **Branch on `code`:**

```ts
const res = await api.POST("/v1/blocks/{block_id}/reviews", {
  params: { path: { block_id } },
  body: { action: "APPROVE", contentHash },
});
if (isProblem(res.error)) {
  switch (res.error.code) {
    case "STALE_REVIEW": /* reload the block, show the new hash */ break;
    case "VERSION_CONFLICT": /* reload, retry the edit */ break;
    case "PUBLISH_BLOCKED": /* open the publish checklist */ break;
    case "UNAUTHENTICATED": /* go to login */ break;
  }
}
```

Full list of codes: `docs/api/API_GUIDE.md`. While a route still answers `501 NOT_IMPLEMENTED`, use the Prism mock.
