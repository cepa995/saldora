# Infrastructure Notes

Things to configure manually when deploying to production.

## S3/R2 Versioning (#160)

Enable object versioning on the `saldora-documents` bucket to protect against accidental PDF deletion.

**Local (MinIO):**
```bash
docker exec saldora-minio mc version enable local/saldora-documents
```

**Production (Cloudflare R2):**
1. Go to Cloudflare Dashboard → R2 → saldora-documents → Settings
2. Enable "Object versioning"
3. Add lifecycle rule: delete non-current versions after 90 days

**Recovery procedure:** If a document is accidentally deleted, use `mc ls --versions` to find the previous version and restore it.

## Domain Verification

- **saldora.rs** — verified in Resend for email delivery
- **saldora.ai** — buy and verify when ready for production launch
- Update `_LOGO_URL` in `apps/api/app/services/email.py` once logo is hosted

## Database Backups (#159)

TODO: Implement Celery Beat task for daily pg_dump → R2.
- Key format: `backups/db/saldora_{YYYY-MM-DD}.sql.gz`
- Retention: 30 days, auto-delete older
- Alert on failure via Sentry
- Estimated cost: ~$0 on R2 free tier
