# Global community chat design note

The community room uses bounded HTTP polling instead of an always-open SSE or
WebSocket connection. The course project is deployed as a small synchronous
Django application and has no channel layer or connection coordinator. A
short-lived request every two seconds is easier to authenticate, rate-limit,
cache-control, test, and operate in that environment.

The trade-off is up to roughly two seconds of delivery latency. Polling stops
while the page is hidden, backs off after network failures, and cannot overlap
itself. The JSON endpoint returns at most 100 records with a signed incremental
cursor and is limited to 40 requests per user per minute. A production
multi-worker deployment must replace `LocMemCache` with a shared atomic cache
such as Redis so the rate limit is process-independent.

The browser appends only genuinely new nodes to the `aria-live` log, so earlier
messages are not repeatedly announced. It retains at most 200 rendered message
nodes, which bounds memory use in a tab left open for a long time.

Messages are append-only through the public application surface. The sender is
derived from the authenticated request, message bodies are limited to 1,000
characters before form validation, and a per-user send reservation is consumed
before the `ModelForm` is validated. No update/delete route exists. Django Admin exposes messages
to users with the view permission, but disables add, change, delete, and bulk
delete so chat evidence cannot be edited through the management UI.

Messages from either side of a `UserBlock` relationship are excluded. Suspended
accounts are already rejected by the configured authentication backend because
suspension also forces `is_active=False`.
