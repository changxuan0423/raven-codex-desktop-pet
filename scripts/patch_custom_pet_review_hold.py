#!/usr/bin/env python3
"""Patch Codex custom pets to hold review and play all eight hover frames."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path


TARGET_PREFIX = "webview/assets/codex-avatar-"
HOLD_MS = 3200
HOLD_MARKER = "d===`idle`&&Z!=null?Z:d"
HOVER_MARKER = "e===`jumping`&&C?j(4,8,140,280):z[e]"
CUSTOM_PET_MARKER = "isCustomPet:o!=null"

OLD_ANIMATION_PROPS = (
    "{avatarRef:n,isAnimationEnabled:r,lookFrame:i,prefersReducedMotion:a,"
    "spriteRowCount:o,state:s}=e"
)
NEW_ANIMATION_PROPS = OLD_ANIMATION_PROPS.replace(
    "state:s}=e", "state:s,isCustomPet:C}=e"
)
OLD_ANIMATION_CALL = "A(d,a||!c)"
NEW_ANIMATION_CALL = "A(d,a||!c,C===!0)"
OLD_ANIMATION_RESOLVER = "function A(e,t){let n=z[e];"
NEW_ANIMATION_RESOLVER = (
    "function A(e,t,C){let n=e===`jumping`&&C?j(4,8,140,280):z[e];"
)

OLD_COMPONENT = """function H(e){let t=(0,G.c)(17),{assetRef:n,className:r,lookFrame:i,spriteVersionNumber:a,spritesheetUrl:o,state:l}=e,d=l===void 0?`idle`:l,f=(0,K.useRef)(null),p=c(),m;t[0]===n?m=t[1]:(m=U(n),t[0]=n,t[1]=m);let h=m,g=u(a??(o==null?2:1)),_;t[2]!==i||t[3]!==p||t[4]!==g||t[5]!==d?(_={avatarRef:f,lookFrame:i,prefersReducedMotion:p,spriteRowCount:g,state:d},t[2]=i,t[3]=p,t[4]=g,t[5]=d,t[6]=_):_=t[6],k(_);let v;t[7]===r?v=t[8]:(v=s(`codex-avatar-root`,r),t[7]=r,t[8]=v);let y=`url(${o??J[h]})`,b=`800% ${g*100}%`,x;t[9]!==y||t[10]!==b?(x={backgroundImage:y,backgroundSize:b},t[9]=y,t[10]=b,t[11]=x):x=t[11];let S;return t[12]!==h||t[13]!==d||t[14]!==v||t[15]!==x?(S=(0,q.jsx)(`div`,{ref:f,className:v,"data-avatar-asset-ref":h,"data-avatar-state":d,style:x,"aria-hidden":`true`,"data-testid":`codex-avatar`}),t[12]=h,t[13]=d,t[14]=v,t[15]=x,t[16]=S):S=t[16],S}"""

HOLD_ONLY_COMPONENT = """function H(e){let t=(0,G.c)(17),{assetRef:n,className:r,lookFrame:i,spriteVersionNumber:a,spritesheetUrl:o,state:l}=e,d=l===void 0?`idle`:l,[Z,Q]=(0,K.useState)(null),ee=(0,K.useRef)(null),f=(0,K.useRef)(null),p=c(),m;t[0]===n?m=t[1]:(m=U(n),t[0]=n,t[1]=m);let h=m,g=u(a??(o==null?2:1)),_;(0,K.useEffect)(()=>{let e=()=>{ee.current!=null&&(window.clearTimeout(ee.current),ee.current=null)};if(o==null||d!==`idle`&&d!==`review`){e(),Q(null);return}d===`review`&&(e(),Q(`review`),ee.current=window.setTimeout(()=>{Q(null),ee.current=null},3.2e3))},[o,d]),(0,K.useEffect)(()=>()=>{ee.current!=null&&window.clearTimeout(ee.current)},[]);let te=d===`idle`&&Z!=null?Z:d;t[2]!==i||t[3]!==p||t[4]!==g||t[5]!==te?(_={avatarRef:f,lookFrame:i,prefersReducedMotion:p,spriteRowCount:g,state:te},t[2]=i,t[3]=p,t[4]=g,t[5]=te,t[6]=_):_=t[6],k(_);let v;t[7]===r?v=t[8]:(v=s(`codex-avatar-root`,r),t[7]=r,t[8]=v);let y=`url(${o??J[h]})`,b=`800% ${g*100}%`,x;t[9]!==y||t[10]!==b?(x={backgroundImage:y,backgroundSize:b},t[9]=y,t[10]=b,t[11]=x):x=t[11];let S;return t[12]!==h||t[13]!==te||t[14]!==v||t[15]!==x?(S=(0,q.jsx)(`div`,{ref:f,className:v,"data-avatar-asset-ref":h,"data-avatar-state":te,style:x,"aria-hidden":`true`,"data-testid":`codex-avatar`}),t[12]=h,t[13]=te,t[14]=v,t[15]=x,t[16]=S):S=t[16],S}"""

NEW_COMPONENT = HOLD_ONLY_COMPONENT.replace(
    "spriteRowCount:g,state:te}",
    "spriteRowCount:g,state:te,isCustomPet:o!=null}",
)


def read_header(blob: bytes) -> tuple[dict, int, int]:
    if struct.unpack_from("<I", blob, 0)[0] != 4:
        raise SystemExit("unsupported asar pickle header")
    header_size = struct.unpack_from("<I", blob, 4)[0]
    object_size = struct.unpack_from("<I", blob, 8)[0]
    json_size = struct.unpack_from("<I", blob, 12)[0]
    if object_size < json_size or header_size < object_size:
        raise SystemExit("unsupported asar header layout")
    header = json.loads(blob[16 : 16 + json_size].decode("utf-8"))
    return header, header_size, 8 + header_size


def encode_header(header: dict) -> tuple[bytes, int]:
    data = json.dumps(header, separators=(",", ":")).encode("utf-8")
    padding = (4 - ((4 + len(data)) % 4)) % 4
    object_size = 4 + len(data) + padding
    header_size = 4 + object_size
    return (
        struct.pack("<IIII", 4, header_size, object_size, len(data))
        + data
        + b"\0" * padding,
        header_size,
    )


def walk_files(node: dict, prefix: str = "") -> list[tuple[str, dict]]:
    files = []
    for name, child in node.get("files", {}).items():
        path = f"{prefix}/{name}" if prefix else name
        if "files" in child:
            files.extend(walk_files(child, path))
        else:
            files.append((path, child))
    return files


def payload(blob: bytes, data_start: int, entry: dict) -> bytes:
    offset, size = int(entry["offset"]), int(entry["size"])
    return blob[data_start + offset : data_start + offset + size]


def find_target(header: dict, blob: bytes, data_start: int) -> tuple[str, dict]:
    matches = []
    for path, entry in walk_files(header):
        if not path.startswith(TARGET_PREFIX) or "offset" not in entry:
            continue
        try:
            text = payload(blob, data_start, entry).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "function H(e)" in text and (
            OLD_COMPONENT in text
            or HOLD_ONLY_COMPONENT in text
            or (HOLD_MARKER in text and CUSTOM_PET_MARKER in text)
        ):
            matches.append((path, entry))
    if len(matches) != 1:
        raise SystemExit(f"could not find unique Codex avatar target: {[p for p, _ in matches]}")
    return matches[0]


def update_integrity(entry: dict, data: bytes) -> None:
    integrity = entry.get("integrity")
    if integrity is None:
        return
    block_size = int(integrity.get("blockSize", 4194304))
    integrity["hash"] = hashlib.sha256(data).hexdigest()
    integrity["blocks"] = [
        hashlib.sha256(data[i : i + block_size]).hexdigest()
        for i in range(0, len(data), block_size)
    ]


def patch_avatar(source: bytes) -> bytes:
    text = source.decode("utf-8")
    if (
        HOLD_MARKER in text
        and HOVER_MARKER in text
        and CUSTOM_PET_MARKER in text
        and OLD_COMPONENT not in text
        and HOLD_ONLY_COMPONENT not in text
    ):
        return source
    if text.count(OLD_COMPONENT) == 1:
        text = text.replace(OLD_COMPONENT, NEW_COMPONENT)
    elif text.count(HOLD_ONLY_COMPONENT) == 1:
        text = text.replace(HOLD_ONLY_COMPONENT, NEW_COMPONENT)
    elif text.count(NEW_COMPONENT) != 1:
        raise SystemExit("could not find unique stock CodexAvatar component")

    replacements = (
        (OLD_ANIMATION_PROPS, NEW_ANIMATION_PROPS, "animation custom-pet flag"),
        (OLD_ANIMATION_CALL, NEW_ANIMATION_CALL, "animation custom-pet input"),
        (OLD_ANIMATION_RESOLVER, NEW_ANIMATION_RESOLVER, "custom hover resolver"),
    )
    for old, new, label in replacements:
        if new in text:
            continue
        if text.count(old) != 1:
            raise SystemExit(f"could not find unique {label}")
        text = text.replace(old, new)
    return text.encode("utf-8")


def patch_archive(input_path: Path, output_path: Path) -> dict:
    blob = input_path.read_bytes()
    header, old_header_size, data_start = read_header(blob)
    target_path, target_entry = find_target(header, blob, data_start)
    old_size = int(target_entry["size"])
    patched = patch_avatar(payload(blob, data_start, target_entry))
    target_entry["size"] = len(patched)
    update_integrity(target_entry, patched)

    files = sorted(
        ((path, entry) for path, entry in walk_files(header) if "offset" in entry),
        key=lambda item: int(item[1]["offset"]),
    )
    offset = 0
    output_payloads = []
    for path, entry in files:
        source_size = old_size if path == target_path else int(entry["size"])
        old_offset = int(entry["offset"])
        data = blob[data_start + old_offset : data_start + old_offset + source_size]
        if path == target_path:
            data = patched
        entry["offset"] = str(offset)
        entry["size"] = len(data)
        output_payloads.append(data)
        offset += len(data)

    header_bytes, new_header_size = encode_header(header)
    output_path.write_bytes(header_bytes + b"".join(output_payloads))
    return {
        "ok": True,
        "input": str(input_path),
        "output": str(output_path),
        "target": target_path,
        "holdMs": HOLD_MS,
        "oldHeaderSize": old_header_size,
        "newHeaderSize": new_header_size,
        "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: patch_custom_pet_review_hold.py <input.asar> <output.asar>"
        )
    print(json.dumps(patch_archive(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))


if __name__ == "__main__":
    main()
