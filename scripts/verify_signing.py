"""Compare real signed, unsigned, multisigner and tampered APKs with apksigner."""

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from dataclasses import replace
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs12 import serialize_key_and_certificates
from cryptography.x509.oid import NameOID

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--apksigner-jar", required=True, type=Path)
    parser.add_argument("--java", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    original = hashlib.sha256(args.apk.read_bytes()).hexdigest()
    results = []
    with tempfile.TemporaryDirectory(prefix="droidasc-signing-oracle-") as directory:
        root = Path(directory)
        unsigned = root / "unsigned.apk"
        marker = b"droidasc synthetic signing acceptance payload"
        with zipfile.ZipFile(args.apk) as source, zipfile.ZipFile(unsigned, "w") as target:
            for info in source.infolist():
                if not info.filename.upper().startswith("META-INF/"):
                    target.writestr(info.filename, source.read(info))
            target.writestr("assets/droidasc-signing-oracle.txt", marker)
        stores = []
        for index in range(2):
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name(
                [x509.NameAttribute(NameOID.COMMON_NAME, f"Acceptance signer {index}")]
            )
            now = datetime.datetime.now(datetime.timezone.utc)
            cert = (
                x509.CertificateBuilder()
                .subject_name(name)
                .issuer_name(name)
                .public_key(key.public_key())
                .serial_number(index + 1)
                .not_valid_before(now - datetime.timedelta(days=1))
                .not_valid_after(now + datetime.timedelta(days=1))
                .sign(key, hashes.SHA256())
            )
            path = root / f"signer{index}.p12"
            path.write_bytes(
                serialize_key_and_certificates(
                    b"signer",
                    key,
                    cert,
                    None,
                    serialization.BestAvailableEncryption(b"synthetic-password"),
                )
            )
            stores.append(path)

        command = [args.java, "-jar", str(args.apksigner_jar.resolve())]

        def run(arguments):
            return subprocess.run(command + arguments, capture_output=True, timeout=60, check=False)

        service = DroidAscService(
            replace(Settings.from_env(), allowed_roots=(root,), timeout_seconds=60)
        )
        try:
            variants = [("unsigned", unsigned, False)]
            for name, v1, v2, v3, multi in [
                ("v1", True, False, False, False),
                ("v2-v3", False, True, True, False),
                ("multisigner", True, True, False, True),
            ]:
                signed = root / (name + ".apk")
                parameters = [
                    "sign",
                    "--min-sdk-version",
                    "24",
                    "--v1-signing-enabled",
                    str(v1).lower(),
                    "--v2-signing-enabled",
                    str(v2).lower(),
                    "--v3-signing-enabled",
                    str(v3).lower(),
                    "--v4-signing-enabled",
                    "false",
                    "--ks",
                    str(stores[0]),
                    "--ks-pass",
                    "pass:synthetic-password",
                    "--v1-signer-name",
                    "SIGNER0",
                ]
                if multi:
                    parameters += [
                        "--next-signer",
                        "--ks",
                        str(stores[1]),
                        "--ks-pass",
                        "pass:synthetic-password",
                        "--v1-signer-name",
                        "SIGNER1",
                    ]
                signed_result = run(parameters + ["--out", str(signed), str(unsigned)])
                assert signed_result.returncode == 0, signed_result.stderr.decode(errors="replace")
                variants.append((name, signed, True))
                tampered = root / (name + "-tampered.apk")
                data = signed.read_bytes()
                assert data.count(marker) == 1
                tampered.write_bytes(data.replace(marker, b"X" + marker[1:]))
                variants.append((name + "-tampered", tampered, False))
            for name, path, valid in variants:
                # v1-only signatures are evaluated on pre-v2-required Android versions.
                maximum_sdk = 27 if name.startswith("v1") else None
                sdk_arguments = ["--max-sdk-version", "27"] if maximum_sdk else []
                verified = run(
                    [
                        "verify",
                        "--min-sdk-version",
                        "24",
                        *sdk_arguments,
                        "--verbose",
                        "--print-certs",
                        str(path),
                    ]
                )
                assert (verified.returncode == 0) is valid, (name, verified.stdout, verified.stderr)
                inventory = service.query_archive(str(path), operation="signing_inventory")
                assert inventory["status"] == "ok", inventory
                assert inventory["cryptographic_verification"] == "not_performed"
                baseline_name = name.removesuffix("-tampered")
                assert {s["scheme"] for s in inventory["schemes"] if s["container_present"]} == {
                    "unsigned": set(),
                    "v1": {"v1"},
                    "v2-v3": {"v2", "v3"},
                    "multisigner": {"v1", "v2"},
                }[baseline_name]
                expected = set(
                    re.findall(r"certificate SHA-256 digest: ([0-9a-f]+)", verified.stdout.decode())
                )
                actual = set()
                for scheme in inventory["schemes"]:
                    for signer in scheme.get("signers", []):
                        actual.update(cert["sha256"] for cert in signer["certificates"])
                    for container in scheme.get("containers", []):
                        actual.update(cert["sha256"] for cert in container["certificates"])
                if valid:
                    assert actual == expected and actual, (name, expected, actual)
                results.append(
                    {
                        "variant": name,
                        "apksigner_valid": valid,
                        "verification_min_sdk": 24,
                        "verification_max_sdk": maximum_sdk,
                        "apksigner_sha256": sorted(expected),
                        "inventory_sha256": sorted(actual),
                        "inventory": inventory,
                    }
                )
            for row in results:
                if row["variant"].endswith("-tampered"):
                    baseline = next(
                        item
                        for item in results
                        if item["variant"] == row["variant"].removesuffix("-tampered")
                    )
                    assert baseline["inventory"]["schemes"] == row["inventory"]["schemes"]
        finally:
            service.close()
    assert hashlib.sha256(args.apk.read_bytes()).hexdigest() == original
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"source_sha256": original, "results": results}, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"variants": len(results), "original_unchanged": True, "output": str(args.output)}
        )
    )


if __name__ == "__main__":
    main()
