import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto import (NONCE_SIZE, decrypt_field, encrypt_field, iban_index, mask_iban,
                        mask_phone, mask_tc)


def test_roundtrip():
    for value in ["TR000000000000000000000001", "01234567890", "0555 000 00 11", "ğüşıöç"]:
        assert decrypt_field(encrypt_field(value)) == value


def test_same_plaintext_gives_different_ciphertext():
    a, b = encrypt_field("01234567890"), encrypt_field("01234567890")
    assert a != b
    assert base64.b64decode(a)[:NONCE_SIZE] != base64.b64decode(b)[:NONCE_SIZE]


def test_format_is_nonce_ciphertext_tag():
    blob = base64.b64decode(encrypt_field("abc"))
    assert len(blob) == NONCE_SIZE + 3 + 16


def test_ciphertext_does_not_contain_plaintext():
    token = encrypt_field("01234567890")
    assert "01234567890" not in token
    assert b"01234567890" not in base64.b64decode(token)


def test_tampering_is_detected():
    blob = bytearray(base64.b64decode(encrypt_field("01234567890")))
    blob[-1] ^= 1
    with pytest.raises(InvalidTag):
        decrypt_field(base64.b64encode(bytes(blob)).decode())


def test_wrong_key_fails():
    token = encrypt_field("secret")
    with pytest.raises(InvalidTag):
        decrypt_field(token, key=os.urandom(32))


def test_iban_index_is_stable_and_normalized():
    assert iban_index("TR00 0000 0000 0000 0000 0000 01") == iban_index("tr000000000000000000000001")
    assert iban_index("TR000000000000000000000001") != iban_index("TR000000000000000000000002")


def test_masks():
    assert mask_iban("TR000000000000000000001234") == "TR** **** **** **** **** 1234"
    assert mask_tc("01234567890") == "01*******90"
    assert mask_phone("0555 000 00 11") == "*** *** ** 11"
