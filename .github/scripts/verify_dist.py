"""Record or verify SHA-256 digests of the release distributions in dist/.

    python verify_dist.py record dist   # after the single build
    python verify_dist.py verify dist   # before testing and before publishing

`record` requires exactly one wheel and one sdist and writes dist/SHA256SUMS.
`verify` fails if any file is missing, altered, or unlisted, so the files that
are tested are byte-for-byte the files that are published. It prints the
verified file paths, one per line, for the caller to use.
"""
import glob
import hashlib
import os
import sys

SUMS = "SHA256SUMS"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg):
    print(f"verify_dist: {msg}", file=sys.stderr)
    sys.exit(1)


def dists(d):
    wheels = sorted(glob.glob(os.path.join(d, "*.whl")))
    sdists = sorted(glob.glob(os.path.join(d, "*.tar.gz")))
    if len(wheels) != 1 or len(sdists) != 1:
        fail(f"expected exactly one wheel and one sdist, found {wheels + sdists}")
    return wheels + sdists


def record(d):
    lines = [f"{sha256(p)}  {os.path.basename(p)}\n" for p in dists(d)]
    with open(os.path.join(d, SUMS), "w", encoding="utf-8") as f:
        f.writelines(lines)
    sys.stdout.write("".join(lines))


def verify(d):
    sums_path = os.path.join(d, SUMS)
    if not os.path.isfile(sums_path):
        fail(f"{sums_path} is missing")
    expected = {}
    with open(sums_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                digest, name = line.rstrip("\n").split("  ", 1)
                expected[name] = digest
    present = {os.path.basename(p) for p in dists(d)}
    if present != set(expected):
        fail(f"dist/ contents {sorted(present)} do not match {SUMS} {sorted(expected)}")
    for name, digest in sorted(expected.items()):
        actual = sha256(os.path.join(d, name))
        if actual != digest:
            fail(f"{name}: sha256 {actual} != recorded {digest}")
        print(os.path.join(d, name))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("record", "verify"):
        fail("usage: verify_dist.py record|verify DIST_DIR")
    {"record": record, "verify": verify}[sys.argv[1]](sys.argv[2])
