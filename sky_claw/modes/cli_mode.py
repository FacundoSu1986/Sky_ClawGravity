from __future__ import annotations
import asyncio
import sys
import uuid

from sky_claw.logging_config import correlation_id_var
from sky_claw.app_context import AppContext


async def _run_cli(ctx: AppContext) -> None:
    assert ctx.router and ctx.session
    print("Sky-Claw interactive mode. Type 'exit' or 'quit' to leave.\n")
    chat_id = "cli-session"
    while True:
        try:
            user_input = await asyncio.to_thread(input, "you> ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        text = user_input.strip()
        if not text:
            continue
        correlation_id_var.set(str(uuid.uuid4()))
        try:
            response = await ctx.router.chat(text, ctx.session, chat_id=chat_id)
            print(f"\nsky-claw> {response}\n")
        except RuntimeError as exc:
            print(f"\n[error] {exc}\n")


async def _run_oneshot(ctx: AppContext, command: str) -> None:
    assert ctx.router and ctx.session
    correlation_id_var.set(str(uuid.uuid4()))
    try:
        response = await ctx.router.chat(command, ctx.session, chat_id="oneshot")
        print(response)
    except RuntimeError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        sys.exit(1)
