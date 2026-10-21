"""Signing-container parsing is intentionally independent of APK signature validity."""

import datetime
import hashlib
import io
import struct
import zipfile
from dataclasses import replace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


@pytest.fixture(scope="module")
def certificates():
    rows = []
    for name in ("First synthetic signer", "Second synthetic signer"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256())
        )
        rows.append((key, cert))
    return rows


def unsigned(entries=()):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("assets/data", b"original payload")
        for name, data in entries:
            archive.writestr(name, data)
    return stream.getvalue()


def lp(data):
    return struct.pack("<I", len(data)) + data


def scheme_value(certificates, v3=False, signed_suffix=b""):
    rows = []
    sdk = struct.pack("<II", 28, 0x7FFFFFFF) if v3 else b""
    for _, cert in certificates:
        signed = (
            lp(b"")
            + lp(lp(cert.public_bytes(serialization.Encoding.DER)))
            + sdk
            + lp(b"")
            + signed_suffix
        )
        # Empty signatures deliberately establish that inventory is not verification.
        rows.append(lp(lp(signed) + sdk + lp(b"") + lp(b"")))
    return lp(b"".join(rows))


def with_block(data, pairs):
    central = struct.unpack_from("<I", data, len(data) - 6)[0]
    encoded = b"".join(
        struct.pack("<QI", len(value) + 4, identifier) + value for identifier, value in pairs
    )
    size = len(encoded) + 24
    block = struct.pack("<Q", size) + encoded + struct.pack("<Q", size) + b"APK Sig Block 42"
    result = bytearray(data[:central] + block + data[central:])
    struct.pack_into("<I", result, len(result) - 6, central + len(block))
    return bytes(result)


@pytest.fixture
def signing_service(tmp_path):
    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(tmp_path,), timeout_seconds=30)
    )
    try:
        yield service
    finally:
        service.close()


def inspect(service, tmp_path, data):
    path = tmp_path / "signatures.apk"
    path.write_bytes(data)
    result = service.query_archive(str(path), operation="signing_inventory")
    assert result["apk_sha256"] == hashlib.sha256(data).hexdigest()
    assert path.read_bytes() == data
    return result


def test_unsigned_and_v1_certificate_bag(signing_service, tmp_path, certificates):
    result = inspect(signing_service, tmp_path, unsigned())
    assert result["status"] == "ok" and all(
        not row["container_present"] for row in result["schemes"]
    )
    key, cert = certificates[0]
    blob = (
        pkcs7.PKCS7SignatureBuilder()
        .set_data(b"synthetic SF data")
        .add_signer(cert, key, hashes.SHA256())
        .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
    )
    result = inspect(signing_service, tmp_path, unsigned([("META-INF/TEST.RSA", blob)]))
    v1 = result["schemes"][0]
    assert (
        v1["container_present"]
        and v1["containers"][0]["certificates"][0]["sha256"]
        == cert.fingerprint(hashes.SHA256()).hex()
    )
    assert v1["certificate_role"] == "pkcs7_certificate_bag_not_resolved_signer_identity"
    assert result["cryptographic_verification"] == "not_performed"
    assert result["certificate_trust"] == "not_evaluated"


@pytest.mark.parametrize("scheme,identifier", [("v2", 0x7109871A), ("v3", 0xF05368C0)])
def test_scheme_multisigner_metadata_is_unverified(
    signing_service, tmp_path, certificates, scheme, identifier
):
    data = with_block(unsigned(), [(identifier, scheme_value(certificates, v3=scheme == "v3"))])
    result = inspect(signing_service, tmp_path, data)
    assert result["status"] == "ok", result
    row = next(row for row in result["schemes"] if row["scheme"] == scheme)
    assert len(row["signers"]) == 2
    assert [r["certificates"][0]["sha256"] for r in row["signers"]] == [
        cert.fingerprint(hashes.SHA256()).hex() for _, cert in certificates
    ]
    assert result["apk_content_integrity"] == "not_verified"
    tampered = data.replace(b"original payload", b"modified payload")
    again = inspect(signing_service, tmp_path, tampered)
    assert again["schemes"] == result["schemes"] and again["apk_sha256"] != result["apk_sha256"]


@pytest.mark.parametrize(
    "pairs",
    [
        [(0x7109871A, b"\x01")],
        [(0x7109871A, lp(b""))],
        [(0x7109871A, b""), (0x7109871A, b"")],
        [(0x1B93AD61, b"unsupported")],
    ],
)
def test_malformed_or_unsupported_is_partial_not_unsigned(signing_service, tmp_path, pairs):
    result = inspect(signing_service, tmp_path, with_block(unsigned(), pairs))
    assert result["status"] == "partial" and result["diagnostics"]
    assert result["cryptographic_verification"] == "not_performed"


def test_invalid_v1_and_unknown_signing_pair(signing_service, tmp_path):
    result = inspect(signing_service, tmp_path, unsigned([("META-INF/BROKEN.RSA", b"invalid")]))
    assert result["status"] == "partial" and result["schemes"][0]["container_present"]
    result = inspect(signing_service, tmp_path, with_block(unsigned(), [(0x42726577, b"padding")]))
    assert result["status"] == "ok" and result["unknown_signing_block_ids"] == ["0x42726577"]


@pytest.mark.parametrize(
    "v3,suffix,expected",
    [
        (False, lp(b""), "ok"),
        (False, lp(b"unexpected"), "partial"),
        (False, b"\x00", "partial"),
        (False, lp(b"") + lp(b""), "partial"),
        (True, lp(b""), "partial"),
    ],
)
def test_apksig_v2_empty_extension_is_not_arbitrary_trailing_data(
    signing_service, tmp_path, certificates, v3, suffix, expected
):
    identifier = 0xF05368C0 if v3 else 0x7109871A
    data = with_block(
        unsigned(), [(identifier, scheme_value(certificates, v3=v3, signed_suffix=suffix))]
    )
    result = inspect(signing_service, tmp_path, data)
    assert result["status"] == expected, result
    row = next(row for row in result["schemes"] if row["scheme"] == ("v3" if v3 else "v2"))
    assert row["container_present"]
    if expected == "ok":
        assert len(row["signers"]) == len(certificates)
    else:
        assert row["certificate_extraction"] == "error"
