# Production readiness checklist

This repository is a runnable starter, not a certified medical device or a fully production-ready hosted service. Complete and verify every item before onboarding real patients.

## Infrastructure and secrets
- [ ] Use managed PostgreSQL with automated encrypted backups, point-in-time recovery, restricted network access, and tested restore drills.
- [ ] Use managed Redis/queue with authentication and private networking.
- [ ] Store uploads in private object storage (S3-compatible/GCS/Azure Blob) with encryption, retention, malware scanning, and signed access; the local file store here is for development only.
- [ ] Set a long random `JWT_SECRET` from a secrets manager. Rotate credentials; never commit `.env` or expose server API keys to the browser.
- [ ] Set `APP_ENV=production`, exact CORS origins, HTTPS, secure headers, rate limits, request-size limits, and structured redacted logs.
- [ ] Run schema migrations as a separate release step. Do not rely on `create_all` in production.
- [ ] Add monitoring, alerts, uptime checks, error reporting, audit-log retention, and incident response.

## Prescription understanding safety
- [ ] The current OCR extracts text only; it does not reliably recognize all medicine names, strengths, dosage forms, or handwritten instructions.
- [ ] Add a reviewed drug-reference source / licensed pharmacy workflow if you want verified generic names, indications, administration advice, interactions, or availability. Never invent missing instructions from general model knowledge.
- [ ] Display the original text beside extracted fields and require a human to confirm each medicine, strength, frequency, route, duration, and any food-related instructions.
- [ ] Route unreadable, conflicting, or unusual prescriptions to a clinician/pharmacist; do not auto-create reminders until the patient confirms the schedule.
- [ ] Do not recommend changing, stopping, doubling, or substituting medication. Do not infer “with food”, route, dose, or duration when absent.
- [ ] Clearly distinguish information copied from the prescription from external reference data and AI-generated drafts.
- [ ] Obtain consent for processing health information; implement access controls, data export/deletion, consent withdrawal, retention limits, and a documented breach process.

## WhatsApp, voice and calls
- [ ] Set up Meta Business Portfolio, WhatsApp Business Account, registered sender number, approved templates, webhook verification, webhook signature validation, opt-in and opt-out handling.
- [ ] Add idempotent processing and reconciliation for inbound/outbound delivery statuses. The included webhook records message IDs but intentionally does not automatically match replies to users yet.
- [ ] The current adapter sends text only. Voice notes require a media upload/send implementation and audio generation/approval workflow.
- [ ] Calling is a stub/provider interface. Confirm country/account eligibility, recipient consent, pricing, quiet hours and local rules before enabling calls.
- [ ] Add per-user/provider rate limits, retries with backoff, dead-letter handling and a cost ledger.

## Authentication and privacy
- [ ] Add email/phone verification, password reset, refresh-token strategy, session revocation, login throttling and abuse monitoring.
- [ ] Add caregiver invitations and explicit per-person/per-channel permissions before sharing any health details.
- [ ] Confirm applicable Indian data protection, health, consumer, telemarketing and pharmacy rules with qualified counsel and pharmacy partners.
- [ ] Do not use real patient records in development or tests.

## Billing and operations
- [ ] Payment adapter is disabled. Integrate a payment provider and verify server-side webhooks before accepting subscriptions.
- [ ] Load-test API, queue, OCR, database and webhook paths; test duplicate/delayed webhooks, timezone boundaries, revoked consent, provider outage and late check-ins.
- [ ] Create backups and test restore, deployment rollback and key rotation procedures.
