"""Validation des entrées de la Lambda API : réexport de backend.common.validation.

La logique vit dans backend/common pour être partagée avec la Lambda agents
(outil propose_mandate), dont le zip ne contient pas backend/api.
"""

from backend.common.validation import *  # noqa: F401,F403
from backend.common.validation import (  # noqa: F401  (noms privés réutilisés par les routes)
    MANDATE_FIELDS,
    parse_json_body,
    parse_pagination,
    path_parameter,
    session_id,
    validate_conversation_create,
    validate_conversation_update,
    validate_holdings,
    validate_investor_profile,
    validate_mandate_create,
)
