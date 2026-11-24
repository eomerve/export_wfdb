
from pathlib import Path
import struct
import json
import os

os.umask(0o077)

BASE = Path.home() / (
    "bistos-capture/bistos-capture/"
    "capture_20261124_154913"
)

OUTPUT = BASE / "WFDB_RECORDS"
OUTPUT.mkdir(exist_ok=True)

raw = (BASE / "cms_raw.bin").read_bytes()

# Temporary frequency for format testing only
FS = 250

frames = []
offset = 0

while offset + 10 <= len(raw):

    if raw[offset:offset+4] != b"QCMS":
        break

    length = int.from_bytes(
        raw[offset+8:offset+10], "little"
    )

    if length < 10 or offset + length > len(raw):
        break

    packet = raw[offset:offset+length]

    if length == 2518 and packet[7] == 5:
        frames.append(packet)

    offset += length

if not frames:
    raise SystemExit("No frames found")

BLOCKS = {
    "candidate_1": (128, 896),
    "candidate_2": (1472, 1920)
}

for name, (start, end) in BLOCKS.items():

    samples = []

    for packet in frames:

        block = packet[start:end]

        values = struct.unpack(
            f"<{len(block)//2}h",
            block
        )

        samples.extend(values)

    dat_path = OUTPUT / f"{name}.dat"
    hea_path = OUTPUT / f"{name}.hea"

    # Write signed 16-bit binary samples
    dat_path.write_bytes(
        struct.pack(
            f"<{len(samples)}h",
            *samples
        )
    )

    checksum = sum(samples) % 65536

    if checksum >= 32768:
        checksum -= 65536

    # WFDB header
    with open(hea_path, "w") as f:

        f.write(
            f"{name} 1 {FS} {len(samples)}\n"
        )

        f.write(
            f"{name}.dat 16 1(0)/adu "
            f"16 0 {samples[0]} "
            f"{checksum} 0 RAW_CANDIDATE\n"
        )

        f.write("# UNVERIFIED SIGNAL\n")
        f.write("# Sampling rate is assumed\n")
        f.write("# Not for clinical use\n")

    metadata = {
        "status": "unverified",
        "start_offset": start,
        "end_offset_exclusive": end,
        "sample_count": len(samples),
        "assumed_frequency_hz": FS,
        "frame_count": len(frames),
        "format": "signed_int16_le",
        "minimum": min(samples),
        "maximum": max(samples)
    }

    with open(
        OUTPUT / f"{name}.json", "w"
    ) as f:

        json.dump(metadata, f, indent=4)

    print("\nRecord:", name)
    print("Samples:", len(samples))
    print("DAT:", dat_path)
    print("HEA:", hea_path)

print("\nExport completed.")