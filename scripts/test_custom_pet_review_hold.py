#!/usr/bin/env python3
"""Regression tests for Raven's narrow custom-pet renderer patch."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("patch_custom_pet_review_hold.py")
SPEC = importlib.util.spec_from_file_location("custom_pet_review_hold", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FIXTURE = (
    "function k(e){let {avatarRef:n,isAnimationEnabled:r,lookFrame:i,"
    "prefersReducedMotion:a,spriteRowCount:o,state:s}=e,c=true,l=null,u=11,"
    "d=s,f=()=>A(d,a||!c)}function A(e,t){let n=z[e];return n}"
    + MODULE.OLD_COMPONENT
)


class CustomPetReviewHoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.patched = MODULE.patch_avatar(FIXTURE.encode()).decode()

    def test_review_hold_is_custom_pet_only(self) -> None:
        self.assertIn("o==null||d!==`idle`&&d!==`review`", self.patched)
        self.assertIn("3.2e3", self.patched)
        self.assertIn(MODULE.HOLD_MARKER, self.patched)

    def test_semantic_states_cancel_hold(self) -> None:
        self.assertIn("d!==`idle`&&d!==`review`", self.patched)
        self.assertIn("e(),Q(null);return", self.patched)

    def test_custom_hover_uses_all_eight_frames(self) -> None:
        self.assertIn("isCustomPet:C", self.patched)
        self.assertIn("A(d,a||!c,C===!0)", self.patched)
        self.assertIn(MODULE.HOVER_MARKER, self.patched)
        self.assertIn(MODULE.CUSTOM_PET_MARKER, self.patched)

    def test_no_custom_completion_event_is_added(self) -> None:
        self.assertNotIn("raven-turn-completed", self.patched)

    def test_patcher_is_idempotent(self) -> None:
        once = MODULE.patch_avatar(FIXTURE.encode())
        self.assertEqual(MODULE.patch_avatar(once), once)


if __name__ == "__main__":
    unittest.main()
