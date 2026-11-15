from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path


class UploadError(Exception):
    pass


def request(url: str, token: str, *, method: str, body: bytes | None = None,
             headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"token {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def parse_artifact(filename: str) -> str:
    stem = filename
    if stem.endswith(".pkg.tar.zst"):
        stem = stem[: -len(".pkg.tar.zst")]
    elif stem.endswith(".pkg.tar.xz"):
        stem = stem[: -len(".pkg.tar.xz")]
    elif ".pkg.tar." in stem:
        stem = stem.split(".pkg.tar.")[0]
    else:
        raise UploadError(f"cannot parse artifact filename: {filename}")
    parts = stem.split("-")
    if len(parts) < 3:
        raise UploadError(f"cannot parse artifact filename: {filename}")
    name = "-".join(parts[:-3])
    if not name:
        raise UploadError(f"cannot parse artifact filename: {filename}")
    return name


def upload_artifact(artifact: Path, *, gitea_base: str, owner: str,
                    name: str, token: str, force: bool = False) -> str:
    url = (f"{gitea_base.rstrip('/')}/api/packages/{owner}/arch/{name}")
    body = artifact.read_bytes()

    status = request(
        url, token, method="PUT", body=body,
        headers={"Content-Type": "application/octet-stream"},
    )
    if status == 201 or status == 200:
        return f"uploaded {artifact.name} (HTTP {status})"

    if status == 409:
        if not force:
            return f"skipped {artifact.name} (already published, HTTP 409; use --force-upload to overwrite)"
        del_url = (f"{gitea_base.rstrip('/')}/api/v1/packages/{owner}/arch/{name}")
        request(del_url, token, method="DELETE")
        status = request(
            url, token, method="PUT", body=body,
            headers={"Content-Type": "application/octet-stream"},
        )
        if status in (200, 201):
            return f"re-uploaded {artifact.name} (HTTP {status})"
        return f"re-upload failed for {artifact.name} (HTTP {status})"

    if status == 400:
        raise UploadError(f"Gitea rejected {artifact.name} (HTTP 400, invalid package)")
    raise UploadError(f"upload {artifact.name} failed (HTTP {status})")


def ensure_token(token: str | None) -> str:
    if not token:
        raise UploadError(
            "no Gitea token: pass --token or set GITEA_TOKEN (required to upload)"
        )
    return token
