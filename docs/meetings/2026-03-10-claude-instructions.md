# Claude Instructions (from Pi)

Implement arigato-gateway with these constraints:
- Internal network only, no external exposure.
- No authentication for now.
- Scraping execution is NOT built-in browser automation in this service; instead, OpenClaw Browser Relay (Pi) performs scraping and posts normalized results to this gateway.
- Gateway responsibilities: ingestion API, source/job management, run history, record storage, health endpoints, and stylish admin UI with high information density.
- Must be extensible for future scraping targets beyond Bookmeter/Filmarks.
- Include docker-compose, backend, frontend, docs, and sample data flow.
- Keep PII/secrets out of repository; .env.example only.
- Save discussion artifacts: summary minutes and full transcript.
