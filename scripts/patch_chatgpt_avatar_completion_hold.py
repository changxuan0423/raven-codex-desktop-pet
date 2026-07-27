#!/usr/bin/env python3
"""Patch ChatGPT's avatar overlay bundle to hold completion mascot feedback."""

from __future__ import annotations

import json
import hashlib
import struct
import sys
from pathlib import Path


TARGET_BASENAME_PREFIX = "webview/assets/avatar-overlay-page-"
LEGACY_TARGET = "webview/assets/avatar-overlay-page--lFBkhmD.js"

OLD_STATE_PREFIX = (
    "function jn({avatar:e,avatarMenuItems:t,debugWindowBorderVisible:n=!1,"
    "interactiveRegionRef:r,isDragging:i=!1,isNotificationTrayOpen:a=!0,"
    "realtimeVoiceSurface:o,layout:s,mascotLayout:c=s.mascot,mascotStyle:l,"
    "mascotDragState:u,mascotResizeHandle:d,notifications:f,onLostPointerCapture:p,"
    "onCloseNotificationTray:m,onPointerCancel:h,onPointerDown:g,onPointerMove:_,"
    "onPointerUp:v,onDismissNotification:y,onOpenNotificationActions:b,onRunNotificationAction:x,"
    "onSubmitQuestionOption:S,onNotificationReplyEditorActiveChange:C,onOpenNotificationReply:w,"
    "onSubmitNotificationReply:T,onOpenNotificationTray:E}){let D=ee(),O=xe(),k=bt(f[0]),"
    "A=f.length>0,te=o?.phase??`inactive`,ne=Ct(o?.isSessionActive??!1,te!==`inactive`),"
    "j=ne===`voice-orb`,M=ne===`hidden`,N=ne===`pet`?c:{...c,height:121,width:hn},"
    "[P,re]=(0,X.useState)(null),[F,I]=(0,X.useState)(null);"
)

NEW_STATE_PREFIX = (
    "function jn({avatar:e,avatarMenuItems:t,debugWindowBorderVisible:n=!1,"
    "interactiveRegionRef:r,isDragging:i=!1,isNotificationTrayOpen:a=!0,"
    "realtimeVoiceSurface:o,layout:s,mascotLayout:c=s.mascot,mascotStyle:l,"
    "mascotDragState:u,mascotResizeHandle:d,notifications:f,onLostPointerCapture:p,"
    "onCloseNotificationTray:m,onPointerCancel:h,onPointerDown:g,onPointerMove:_,"
    "onPointerUp:v,onDismissNotification:y,onOpenNotificationActions:b,onRunNotificationAction:x,"
    "onSubmitQuestionOption:S,onNotificationReplyEditorActiveChange:C,onOpenNotificationReply:w,"
    "onSubmitNotificationReply:T,onOpenNotificationTray:E}){let D=ee(),O=xe(),k=bt(f[0]),"
    "A=f.length>0,te=o?.phase??`inactive`,ne=Ct(o?.isSessionActive??!1,te!==`inactive`),"
    "j=ne===`voice-orb`,M=ne===`hidden`,N=ne===`pet`?c:{...c,height:121,width:hn},"
    "[P,re]=(0,X.useState)(null),[F,I]=(0,X.useState)(null),[qe,Je]=(0,X.useState)(null),"
    "et=(0,X.useRef)(k.mascotState);"
    "(0,X.useEffect)(()=>{let n=et.current;et.current=k.mascotState;"
    "if(!(k.mascotState===`review`||k.mascotState===`idle`&&(n===`running`||n===`review`)))return;"
    "Je(`waving`);let e=window.setTimeout(()=>{Je(null)},3e3);return()=>{window.clearTimeout(e)}},"
    "[k.mascotState]);let Xe=qe!=null?qe:u;"
)

OLD_PROP = "style:l,transientState:u});return"
NEW_PROP = "style:l,transientState:Xe});return"
OLD_PATCH_MARKER = "let Xe=u??(qe!=null&&k.mascotState===`idle`?qe:null)"
PATCH_MARKER = "let Xe=qe!=null?qe:u"
RUNNING_TO_IDLE_MARKER = "k.mascotState===`idle`&&(n===`running`||n===`review`)"
OLD_REVIEW_ONLY_SNIPPET = (
    "[qe,Je]=(0,X.useState)(null);"
    "(0,X.useEffect)(()=>{if(k.mascotState!==`review`)return;Je(`waving`);"
    "let e=window.setTimeout(()=>{Je(null)},3e3);return()=>{window.clearTimeout(e)}},"
    "[k.mascotState]);let Xe=u??(qe!=null&&k.mascotState===`idle`?qe:null);"
)
NEW_RUNNING_TO_IDLE_SNIPPET = (
    "[qe,Je]=(0,X.useState)(null),et=(0,X.useRef)(k.mascotState);"
    "(0,X.useEffect)(()=>{let n=et.current;et.current=k.mascotState;"
    "if(!(k.mascotState===`review`||k.mascotState===`idle`&&(n===`running`||n===`review`)))return;"
    "Je(`waving`);let e=window.setTimeout(()=>{Je(null)},3e3);return()=>{window.clearTimeout(e)}},"
    "[k.mascotState]);let Xe=qe!=null?qe:u;"
)


def read_header(blob: bytes) -> tuple[dict, int, int]:
    pickle_header_size = struct.unpack_from("<I", blob, 0)[0]
    if pickle_header_size != 4:
        raise SystemExit(f"unsupported asar pickle header size: {pickle_header_size}")
    header_size = struct.unpack_from("<I", blob, 4)[0]
    object_size = struct.unpack_from("<I", blob, 8)[0]
    json_size = struct.unpack_from("<I", blob, 12)[0]
    header_json = blob[16 : 16 + json_size].decode("utf-8")
    if object_size < json_size or header_size < object_size:
        raise SystemExit("unsupported asar header size layout")
    return json.loads(header_json), header_size, 8 + header_size


def encode_header(header: dict) -> tuple[bytes, int]:
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    json_size = len(header_json)
    object_size_without_padding = 4 + json_size
    padding = (4 - (object_size_without_padding % 4)) % 4
    object_size = object_size_without_padding + padding
    header_size = 4 + object_size
    return (
        struct.pack("<I", 4)
        + struct.pack("<I", header_size)
        + struct.pack("<I", object_size)
        + struct.pack("<I", json_size)
        + header_json
        + (b"\0" * padding),
        header_size,
    )


def walk_files(node: dict, prefix: str = "") -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    for name, child in node.get("files", {}).items():
        path = f"{prefix}/{name}" if prefix else name
        if "files" in child:
            items.extend(walk_files(child, path))
        else:
            items.append((path, child))
    return items


def get_entry(header: dict, path: str) -> dict:
    node = header
    for part in path.split("/"):
        node = node["files"][part]
    return node


def find_target_file(header: dict, blob: bytes, data_start: int) -> tuple[str, dict]:
    candidates = []
    for path, entry in walk_files(header):
        if path == LEGACY_TARGET or path.startswith(TARGET_BASENAME_PREFIX):
            candidates.append((path, entry))
    matches = []
    for path, entry in candidates:
        offset = int(entry.get("offset", 0))
        size = int(entry.get("size", 0))
        try:
            text = blob[data_start + offset : data_start + offset + size].decode("utf-8")
        except UnicodeDecodeError:
            continue
        if "function jn(" in text and (OLD_PROP in text or PATCH_MARKER in text or OLD_PATCH_MARKER in text):
            matches.append((path, entry))
    if len(matches) != 1:
        raise SystemExit(f"could not find unique avatar overlay target; matches={ [path for path, _ in matches] }")
    return matches[0]


def patch_js(source: bytes) -> bytes:
    text = source.decode("utf-8")
    if RUNNING_TO_IDLE_MARKER in text and PATCH_MARKER in text:
        return source
    if RUNNING_TO_IDLE_MARKER in text and OLD_PATCH_MARKER in text:
        return text.replace(OLD_PATCH_MARKER, PATCH_MARKER).encode("utf-8")
    if OLD_REVIEW_ONLY_SNIPPET in text:
        return text.replace(OLD_REVIEW_ONLY_SNIPPET, NEW_RUNNING_TO_IDLE_SNIPPET).encode("utf-8")
    if text.count(OLD_STATE_PREFIX) == 1:
        text = text.replace(OLD_STATE_PREFIX, NEW_STATE_PREFIX)
    else:
        state_prefix = "N=ee===`pet`?c:{...c,height:121,width:hn},"
        prefix_index = text.find(state_prefix)
        if prefix_index < 0:
            raise SystemExit("could not find avatar overlay state prefix anchor")
        state_start = prefix_index + len(state_prefix)
        state_end = text.find(";fe(`avatar-overlay-computer-use-cursor-changed`", state_start)
        if state_end < 0:
            raise SystemExit("could not find avatar overlay state declaration end")
        existing_state = text[state_start:state_end]
        if existing_state.count("(0,X.useState)(null)") != 2:
            raise SystemExit("could not identify exactly two avatar overlay transient state hooks")
        text = (
            text[:state_end]
            + ","
            + NEW_RUNNING_TO_IDLE_SNIPPET
            + text[state_end:]
        )
    if text.count(OLD_PROP) != 1:
        raise SystemExit("could not find unique transientState prop")
    text = text.replace(OLD_PROP, NEW_PROP)
    return text.encode("utf-8")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: patch_chatgpt_avatar_completion_hold.py <input.asar> <output.asar>")
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    blob = input_path.read_bytes()
    header, old_header_size, old_data_start = read_header(blob)
    target_path, target_entry = find_target_file(header, blob, old_data_start)
    target_offset = int(target_entry["offset"])
    target_size = int(target_entry["size"])
    target_start = old_data_start + target_offset
    target_end = target_start + target_size
    patched_target = patch_js(blob[target_start:target_end])
    target_entry["size"] = len(patched_target)
    if "integrity" in target_entry:
        block_size = int(target_entry["integrity"].get("blockSize", 4194304))
        blocks = [
            hashlib.sha256(patched_target[index : index + block_size]).hexdigest()
            for index in range(0, len(patched_target), block_size)
        ]
        target_entry["integrity"]["hash"] = hashlib.sha256(patched_target).hexdigest()
        target_entry["integrity"]["blocks"] = blocks

    old_files = sorted(
        [
            (path, entry)
            for path, entry in walk_files(header)
            if "offset" in entry and "size" in entry
        ],
        key=lambda item: int(item[1]["offset"]),
    )

    current_offset = 0
    file_payloads: list[bytes] = []
    for path, entry in old_files:
        old_offset = int(entry["offset"])
        old_size = target_size if path == target_path else int(entry["size"])
        original = blob[old_data_start + old_offset : old_data_start + old_offset + old_size]
        payload = patched_target if path == target_path else original
        entry["offset"] = str(current_offset)
        entry["size"] = len(payload)
        file_payloads.append(payload)
        current_offset += len(payload)

    header_bytes, new_header_size = encode_header(header)
    output_path.write_bytes(header_bytes + b"".join(file_payloads))
    print(
        json.dumps(
            {
                "ok": True,
                "input": str(input_path),
                "output": str(output_path),
                "target": target_path,
                "oldHeaderSize": old_header_size,
                "newHeaderSize": new_header_size,
                "oldTargetSize": target_size,
                "newTargetSize": len(patched_target),
                "fileCount": len(old_files),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
