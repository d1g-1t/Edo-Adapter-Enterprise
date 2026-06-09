from __future__ import annotations

import base64
import hashlib
import hmac
from enum import StrEnum


class SignatureStyle(StrEnum):
    HEX = "hex"
    BASE64 = "base64"


def verify_hmac(
    body: bytes,
    secret: str,
    provided_signature: str,
    style: SignatureStyle = SignatureStyle.HEX,
) -> bool:
    raw_mac = hmac.new(
        key=secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    ).digest()

    if style == SignatureStyle.BASE64:
        expected = base64.b64encode(raw_mac).decode()
    else:
        expected = raw_mac.hex()

    return hmac.compare_digest(expected, provided_signature)
