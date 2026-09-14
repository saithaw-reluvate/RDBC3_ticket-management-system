from rest_framework.throttling import AnonRateThrottle


class TicketCreateThrottle(AnonRateThrottle):
    scope = "ticket_create"


class TokenLookupThrottle(AnonRateThrottle):
    scope = "token_lookup"


class ResendLinkThrottle(AnonRateThrottle):
    scope = "resend_link"
