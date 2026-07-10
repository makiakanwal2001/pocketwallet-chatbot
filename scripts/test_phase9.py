"""
Phase 9 — Prompt Management Tests
Tests: prompt registry, versioning, activation, shadow mode.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from prompts.registry import (
    init_prompt_table, seed_default_prompts,
    get_active_prompt, get_shadow_prompt,
    get_prompt_for_request, create_prompt_version,
    activate_prompt, list_prompt_versions, set_shadow_pct,
)

DIVIDER = "=" * 65

def run_test(desc: str, result: bool) -> bool:
    print(f"  {'[PASS]' if result else '[FAIL]'} {desc}")
    return result


def main():
    print(DIVIDER)
    print("PocketWallet — Phase 9 Prompt Management Tests")
    print(DIVIDER)

    passed = 0
    total  = 0

    # ── Setup ─────────────────────────────────────────────────────────────────
    print("\nInitialising prompt registry...")
    init_prompt_table()
    seed_default_prompts()

    # ── Test 1: Active prompt retrieval ───────────────────────────────────────
    print(f"\n[Test 1] Active prompt retrieval")
    active = get_active_prompt("answer_generation")
    total += 1; passed += run_test("active prompt exists",          active is not None)
    total += 1; passed += run_test("active prompt is version 1",    active["version"] == 1)
    total += 1; passed += run_test("active prompt has content",     len(active["content"]) > 50)

    # ── Test 2: Shadow prompt ─────────────────────────────────────────────────
    print(f"\n[Test 2] Shadow prompt")
    shadow = get_shadow_prompt("answer_generation")
    total += 1; passed += run_test("shadow prompt exists (v2 at 10%)", shadow is not None)
    total += 1; passed += run_test("shadow prompt is version 2",       shadow and shadow["version"] == 2)
    total += 1; passed += run_test("shadow_pct is 10",                 shadow and shadow["shadow_pct"] == 10)

    # ── Test 3: Shadow routing ────────────────────────────────────────────────
    print(f"\n[Test 3] Shadow routing (10% traffic)")
    active_count = 0
    shadow_count = 0
    for i in range(100):
        p = get_prompt_for_request("answer_generation", request_id=i)
        if p["_routing"] == "shadow":
            shadow_count += 1
        else:
            active_count += 1

    total += 1; passed += run_test(
        f"~10% routed to shadow ({shadow_count}/100)",
        8 <= shadow_count <= 12
    )
    total += 1; passed += run_test(
        f"~90% routed to active ({active_count}/100)",
        88 <= active_count <= 92
    )

    # ── Test 4: Create new version ────────────────────────────────────────────
    print(f"\n[Test 4] Create new prompt version")
    new_prompt = create_prompt_version(
        prompt_key  = "answer_generation",
        content     = "You are PocketWallet support v3. Answer clearly. Source: {policy_context}",
        description = "v3 — Minimal test prompt",
        created_by  = "test_admin",
    )
    total += 1; passed += run_test("new version created",           new_prompt["version"] == 3)
    total += 1; passed += run_test("new version is not active",     not new_prompt["is_active"])
    total += 1; passed += run_test("created_by is correct",         new_prompt["created_by"] == "test_admin")

    # ── Test 5: Activate new version ─────────────────────────────────────────
    print(f"\n[Test 5] Activate prompt version")
    ok = activate_prompt("answer_generation", version=3)
    total += 1; passed += run_test("activation succeeded",          ok)

    now_active = get_active_prompt("answer_generation")
    total += 1; passed += run_test("v3 is now active",              now_active["version"] == 3)

    # ── Test 6: Rollback ──────────────────────────────────────────────────────
    print(f"\n[Test 6] Rollback to v1")
    activate_prompt("answer_generation", version=1)
    rolled_back = get_active_prompt("answer_generation")
    total += 1; passed += run_test("rolled back to v1",             rolled_back["version"] == 1)

    # ── Test 7: List versions ─────────────────────────────────────────────────
    print(f"\n[Test 7] List all versions")
    versions = list_prompt_versions("answer_generation")
    total += 1; passed += run_test("3 versions exist",              len(versions) == 3)
    total += 1; passed += run_test("versions ordered newest first", versions[0]["version"] == 3)

    print(f"\n  Prompt history for 'answer_generation':")
    for v in versions:
        active_marker = "← active" if v["is_active"] else ""
        shadow_marker = f"shadow={v['shadow_pct']}%" if v["shadow_pct"] > 0 else ""
        print(f"  v{v['version']} | {v['description']:<35} | "
              f"by={v['created_by']:<12} {active_marker} {shadow_marker}")

    # ── Test 8: Update shadow percentage ─────────────────────────────────────
    print(f"\n[Test 8] Update shadow percentage")
    ok = set_shadow_pct("answer_generation", version=2, pct=25)
    total += 1; passed += run_test("shadow pct updated to 25%",     ok)
    shadow_updated = get_shadow_prompt("answer_generation")
    total += 1; passed += run_test("shadow prompt now at 25%",
                                   shadow_updated and shadow_updated["shadow_pct"] == 25)

    # ── Final ─────────────────────────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print(f"RESULTS: {passed}/{total} tests passed")
    print(f"Phase 9 DoD: {'MET ✓' if passed == total else 'NOT MET ✗'}")
    print(DIVIDER)


if __name__ == "__main__":
    main()
