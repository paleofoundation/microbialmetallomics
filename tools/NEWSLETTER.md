# Newsletter operations

The public signup page is [microbialmetallomics.com/newsletter](https://microbialmetallomics.com/newsletter). It uses Resend through the same-origin `POST /api/newsletter` endpoint. This repository does not schedule or send digest editions automatically. As of 30 September 2026, no digest edition has been sent or scheduled.

## Account and audience

Open the [Resend dashboard through the Vercel integration](https://vercel.com/d/dashboard/integrations/resend/icfg_8lPnTDz1Gc5hRSdRdry04CXw/resources/ir_AH6xSmVaSBTVxlaV).

| Setting | Value |
| --- | --- |
| Verified sender | `Microbial Metallomics <hello@newsletter.microbialmetallomics.com>` |
| Segment | Microbial Metallomics — `e0a2e069-6331-4ade-887a-0cc02748007e` |
| Topic | Microbial Metallomics research digest — `2a293289-895e-41a3-9ae8-41cb64318fec` |
| Topic default | `opt_out`; only explicit confirmation opts a contact in |
| Open tracking | Disabled for the sending domain |
| Click tracking | Disabled for the sending domain |

The Resend account is shared. Existing contacts and opt-outs may belong to other mailing lists. Do not send to all account contacts or change another list’s settings.

## Prepare and send an edition

1. Draft and review the edition in Resend Broadcasts. A useful format is one important paper, one critical commentary, and one method or researcher, each linking to the relevant site page. The public site aims for a monthly digest; delivery remains an editorial decision.
2. Select the verified sender above. Target **both the Microbial Metallomics segment and the Microbial Metallomics research digest topic**. Segment membership alone is not proof that the reader is still subscribed to this topic.
3. Include Resend’s native `{{{RESEND_UNSUBSCRIBE_URL}}}` in a clearly labeled unsubscribe link. Use the native variable in every edition so recipients can manage their subscription; do not replace it with a generic contact or homepage link.
4. Check the final audience count, subject, preview text, article links, and unsubscribe link. Preview the message on desktop and mobile. Any test email should go only to an address the operator is authorized to use.
5. Check account-wide sending and contact usage before sending. Keep open and click tracking disabled. Review the complete message and audience, then send the edition manually. No schedule is created by this site.

## Signup and confirmation

- The form requires explicit consent and submits an email address to the backend. Successful signup means a confirmation email was requested, not that the person is already subscribed.
- The confirmation link expires after 24 hours. Opening it displays a separate confirmation button; subscription is activated only after the reader selects that button. This prevents email-link scanners from confirming a subscription merely by opening the URL.
- Confirmation adds the contact to the site’s segment and opts the contact into the digest topic. Pending contacts must not receive broadcasts.
- Confirmation links are signed and tied to the stored contact request. Repeated requests are deduplicated. A consumed or expired link requires a new signup request.
- A private Vercel Blob store claims each confirmation once across servers. It stores only an expiry time and a keyed digest of the request, with no email address or raw confirmation token. Keep these small claim records through token expiry; never remove one to retry a failed activation. A new signup request rotates an already-claimed request, including after an interrupted provider update. Expired records may be removed during routine maintenance.
- Account-wide opt-outs covering unrelated mailing lists are preserved. A reader encountering that restriction should use the contribution/contact route for individual assistance; do not bulk-reactivate contacts.
- RSS remains available at `/feeds` without an email address or account.

## Quotas and monitoring

The private confirmation store uses standard Vercel Blob usage billing. Each confirmed request writes a one-byte claim; keep it private and monitor its usage with the rest of the Vercel project.

The free Resend account limits observed on 30 September 2026 are **100 emails per day, 3,000 emails per month, and 1,000 contacts**. These are shared account limits, not a dedicated budget for this site. Confirmation messages and other applications’ email use consume the same sending allowance; pending contacts may also use contact capacity. Check the dashboard for current usage and limits before each edition.

Review delivery failures and complaints in Resend. Keep bounced, complained, or unsubscribed contacts suppressed. Do not import or add people to the confirmed audience solely because their professional email appears in the site’s researcher directory.

## Deployment configuration

These environment variable names are configured in Vercel. Keep their values out of this repository, client JavaScript, screenshots, and logs.

| Variable | Purpose |
| --- | --- |
| `RESEND_API_KEY` | Server-only Resend API access |
| `RESEND_EMAIL_DOMAIN` | Verified sending domain used by the backend |
| `NEWSLETTER_SEGMENT_ID` | Site-specific segment for confirmed contacts |
| `NEWSLETTER_TOPIC_ID` | Digest topic requiring explicit opt-in |
| `NEWSLETTER_SECRET` | Server-only secret for signing confirmation tokens; at least 32 characters |
| `BLOB_READ_WRITE_TOKEN` | Server-only access to the private confirmation-claim store |
| `VERCEL_ENV` | Vercel-provided deployment environment; production limits origins to the public site |

The backend is in `lib/newsletter.cjs`, with the Vercel entry point in `api/newsletter.js`. The form and confirmation interface are in `newsletter.html` and `assets/newsletter.js`. Run `npm test` for the backend’s local tests. After changing public assets or page copy, run `python3 tools/refresh_site.py` to refresh content hashes and search metadata.

For a temporary provider failure, the interface displays an error and keeps RSS available; it does not report the reader as confirmed. Check the deployment’s environment configuration, domain verification, provider status, and shared quotas. Avoid logging email addresses, confirmation tokens, or upstream response bodies while investigating.
