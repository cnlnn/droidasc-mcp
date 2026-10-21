"""Bounded signature-container inventory; no cryptographic verification."""

from __future__ import annotations

import struct

from cryptography.exceptions import UnsupportedAlgorithm

from .archive_errors import ArchiveError
from .archive_worker import _read

MAX_BLOCK = 8 * 1024**2
MAX_CERTIFICATES = 64
SCHEMES = {0x7109871A: "v2", 0xF05368C0: "v3", 0x1B93AD61: "v3.1"}


class Cursor:
    def __init__(self, data):
        self.data = memoryview(data)
        self.offset = 0

    def take(self, size):
        if size < 0 or size > len(self.data) - self.offset:
            raise ArchiveError(
                "invalid_signing_block", "Length-prefixed signing field is truncated"
            )
        start = self.offset
        self.offset += size
        return self.data[start : self.offset]

    def integer(self, width=4):
        return int.from_bytes(self.take(width), "little")

    def field(self):
        return self.take(self.integer())

    def done(self):
        if self.offset != len(self.data):
            raise ArchiveError("invalid_signing_block", "Signing structure has trailing bytes")

    def fields(self):
        count = 0
        while self.offset < len(self.data):
            count += 1
            if count > 1024:
                raise ArchiveError("signing_limit", "Signing structure exceeds the record budget")
            yield self.field()


def certificate_row(certificate):
    from cryptography.hazmat.primitives import hashes, serialization

    key = certificate.public_key()
    public = key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    digest = hashes.Hash(hashes.SHA256())
    digest.update(public)
    return {
        "sha256": certificate.fingerprint(hashes.SHA256()).hex(),
        "sha1": certificate.fingerprint(hashes.SHA1()).hex(),
        "subject": certificate.subject.rfc4514_string(),
        "issuer": certificate.issuer.rfc4514_string(),
        "serial_hex": format(certificate.serial_number, "x"),
        "not_before_utc": certificate.not_valid_before_utc.isoformat(),
        "not_after_utc": certificate.not_valid_after_utc.isoformat(),
        "public_key_algorithm": certificate.public_key_algorithm_oid.dotted_string,
        "public_key_bits": getattr(key, "key_size", None),
        "public_key_sha256": digest.finalize().hex(),
        "certificate_signature_oid": certificate.signature_algorithm_oid.dotted_string,
    }


def signing_pairs(handle, central):
    if central < 24:
        return None
    handle.seek(central - 24)
    footer = handle.read(24)
    if footer[8:] != b"APK Sig Block 42":
        return None
    size = struct.unpack_from("<Q", footer)[0]
    if size < 24 or size + 8 > central:
        raise ArchiveError("invalid_signing_block", "APK signing block size is invalid")
    if size + 8 > MAX_BLOCK:
        raise ArchiveError("signing_limit", "APK signing block exceeds 8 MiB")
    handle.seek(central - size - 8)
    block = Cursor(handle.read(size + 8))
    if block.integer(8) != size:
        raise ArchiveError("invalid_signing_block", "APK signing block sizes disagree")
    pairs = Cursor(block.take(size - 24))
    values = {}
    while pairs.offset < len(pairs.data):
        length = pairs.integer(8)
        if length < 4 or len(values) >= 1024:
            raise ArchiveError("invalid_signing_block", "Invalid signing pair length or count")
        pair = Cursor(pairs.take(length))
        identifier = pair.integer()
        if identifier in values:
            raise ArchiveError("invalid_signing_block", "Duplicate signing block ID")
        values[identifier] = pair.take(length - 4)
    return values


def scheme_signers(value, scheme):
    from cryptography import x509

    envelope = Cursor(value)
    sequence = Cursor(envelope.field())
    envelope.done()
    rows = []
    for signer_index, raw_signer in enumerate(sequence.fields()):
        if signer_index >= 32:
            raise ArchiveError("signing_limit", "Signer count exceeds 32")
        signer = Cursor(raw_signer)
        signed = Cursor(signer.field())
        signed.field()  # Digest records are inventoried only through their enclosing scheme.
        certs = Cursor(signed.field())
        certificates = []
        for raw in certs.fields():
            if len(certificates) >= MAX_CERTIFICATES:
                raise ArchiveError("signing_limit", "Certificate chain exceeds 64 records")
            certificates.append(certificate_row(x509.load_der_x509_certificate(bytes(raw))))
        if not certificates:
            raise ArchiveError("invalid_signing_block", "Signer has no certificate")
        sdk = {}
        if scheme == "v3":
            sdk = {"min_sdk": signed.integer(), "max_sdk": signed.integer()}
            if sdk != {"min_sdk": signer.integer(), "max_sdk": signer.integer()}:
                raise ArchiveError("invalid_signing_block", "Signer SDK ranges disagree")
        attrs = Cursor(signed.field())
        identifiers = []
        for raw in attrs.fields():
            attribute = Cursor(raw)
            identifiers.append(f"0x{attribute.integer():08x}")
        # AOSP apksig also emits a fourth, empty length-prefixed v2 signed-data field.
        if scheme == "v2" and signed.offset < len(signed.data) and len(signed.field()):
            raise ArchiveError("invalid_signing_block", "Unexpected v2 signed-data extension")
        signed.done()
        signer.field()  # Signatures remain unverified.
        signer.field()  # SubjectPublicKeyInfo remains unverified against the certificate.
        signer.done()
        rows.append(
            {
                "signer_index": signer_index,
                "certificates": certificates,
                "certificate_order": "declared_leaf_first_unverified",
                "attribute_ids": identifiers,
                "rotation_lineage": "not_parsed_or_verified",
                **sdk,
            }
        )
    if not rows:
        raise ArchiveError("invalid_signing_block", "Scheme has no signers")
    return rows


def inventory(handle, archive, entries):
    from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates

    diagnostics, schemes = [], []
    total = 0
    v1 = []
    for name, info in sorted(entries.items()):
        if not name.upper().startswith("META-INF/") or not name.upper().endswith(
            (".RSA", ".DSA", ".EC")
        ):
            continue
        total += info.file_size
        if total > MAX_BLOCK or len(v1) >= 32:
            raise ArchiveError("signing_limit", "JAR signature containers exceed inventory budget")
        data, complete = _read(archive, info, MAX_BLOCK)
        try:
            certificates = load_der_pkcs7_certificates(data) if complete else []
            if not certificates or len(certificates) > MAX_CERTIFICATES:
                raise ValueError("Certificate count is empty or exceeds budget")
            v1.append({"entry": name, "certificates": [certificate_row(c) for c in certificates]})
        except (ValueError, TypeError, UnsupportedAlgorithm) as exc:
            diagnostics.append(
                {
                    "scheme": "v1",
                    "entry": name,
                    "code": "invalid_certificate_container",
                    "message": str(exc),
                }
            )
    v1_present = any(
        name.upper().startswith("META-INF/") and name.upper().endswith((".RSA", ".DSA", ".EC"))
        for name in entries
    )
    schemes.append(
        {
            "scheme": "v1",
            "container_present": v1_present,
            "containers": v1,
            "certificate_role": "pkcs7_certificate_bag_not_resolved_signer_identity",
        }
    )
    try:
        pairs = signing_pairs(handle, archive.start_dir)
        for identifier, scheme in SCHEMES.items():
            row = {"scheme": scheme, "container_present": pairs is not None and identifier in pairs}
            if row["container_present"]:
                if scheme == "v3.1":
                    row["certificate_extraction"] = "unsupported"
                    diagnostics.append(
                        {"scheme": scheme, "code": "certificate_extraction_unsupported"}
                    )
                else:
                    try:
                        row["signers"] = scheme_signers(pairs[identifier], scheme)
                    except (ArchiveError, ValueError, TypeError, UnsupportedAlgorithm) as exc:
                        row["certificate_extraction"] = "error"
                        diagnostics.append(
                            {
                                "scheme": scheme,
                                "code": getattr(exc, "code", "invalid_certificate"),
                                "message": str(exc),
                            }
                        )
            schemes.append(row)
        unknown = [f"0x{value:08x}" for value in (pairs or {}) if value not in SCHEMES]
    except ArchiveError as exc:
        diagnostics.append({"code": exc.code, "message": str(exc)})
        schemes.extend({"scheme": scheme, "container_present": None} for scheme in SCHEMES.values())
        unknown = []
    return {
        "status": "partial" if diagnostics else "ok",
        "schemes": schemes,
        "unknown_signing_block_ids": unknown,
        "diagnostics": diagnostics,
        "cryptographic_verification": "not_performed",
        "apk_content_integrity": "not_verified",
        "certificate_trust": "not_evaluated",
        "v4_sidecar": "not_inspected",
        "interpretation": (
            "Container presence and certificate metadata do not establish a valid APK signature."
        ),
    }
