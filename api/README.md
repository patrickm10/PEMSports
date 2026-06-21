# Legacy Vercel serverless API (removed)

`api/index.py` was deleted because it caused `FUNCTION_INVOCATION_FAILED` (HTTP 500) on
https://pemsports.com when Vercel invoked the Python serverless handler instead of serving
the Vite static build.

Production API runs on Render: https://nflstats-api.onrender.com

Frontend is a static Vite SPA deployed via root `vercel.json` + `.vercelignore`.
