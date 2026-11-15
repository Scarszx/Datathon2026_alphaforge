"""Tests de backend/common/ids.py : sessionId UUID v4, messageId ULID triable."""

import re
import uuid

from ulid import ULID

from backend.common import ids

FORMAT_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")  # alphabet Crockford base32


def test_session_id_est_uuid_v4():
    session_id = ids.new_session_id()
    assert uuid.UUID(session_id).version == 4
    assert ids.new_session_id() != session_id


def test_message_id_est_un_ulid():
    message_id = ids.new_message_id()
    assert len(message_id) == 26
    assert FORMAT_ULID.match(message_id)
    # reparable : le parseur retrouve la valeur d'origine
    assert str(ULID.parse(message_id)) == message_id


def test_message_ids_triables_par_ordre_chronologique():
    premier = ids.new_message_id()
    second = ids.new_message_id()
    # même milliseconde possible : le temps ne recule jamais
    assert ULID.parse(second).timestamp >= ULID.parse(premier).timestamp
    # et deux horodatages différents donnent un ordre lexicographique cohérent
    anterieur = str(ULID.from_timestamp(ULID.parse(premier).timestamp - 1))
    assert anterieur < premier


def test_run_id_est_un_ulid():
    run_id = ids.new_run_id()
    assert FORMAT_ULID.match(run_id)
    assert str(ULID.parse(run_id)) == run_id
    assert ids.new_run_id() != run_id
