"""Small Flet GUI for one-click SpotX install or uninstall.

Requires: pip install flet
"""

from __future__ import annotations

import asyncio
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

import flet as ft


SPOTX_SCRIPT_URL = "https://raw.githubusercontent.com/SpotX-Official/SpotX-Bash/main/spotx.sh"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SPOTIFY_ICON = "main.png"
IS_WINDOWS = sys.platform.startswith("win")
WINDOWS_SPOTX_PS = (
	"$ErrorActionPreference='Stop'; "
	"try { iex \"& { $(iwr -useb 'https://raw.githubusercontent.com/SpotX-Official/SpotX/refs/heads/main/run.ps1') } -new_theme\" } "
	"catch { iex \"& { $(iwr -useb 'https://spotx-official.github.io/SpotX/run.ps1') } -m -new_theme\" }"
)


@dataclass(frozen=True)
class Action:
	name: str
	command: str


INSTALL_ACTION = Action(
	name="Install SpotX",
	command=f"/bin/bash -lc {shlex.quote(f'curl -fsSL {SPOTX_SCRIPT_URL} | /bin/bash -s -f --')}",
)
UPDATE_ACTION = Action(
	name="Update Spotify",
	command=f"/bin/bash -lc {shlex.quote(f'curl -fsSL {SPOTX_SCRIPT_URL} | /bin/bash -s -- --installmac')}",
)
UNINSTALL_ACTION = Action(
	name="Uninstall SpotX",
	command=f"/bin/bash -lc {shlex.quote(f'curl -fsSL {SPOTX_SCRIPT_URL} | /bin/bash -s -- --uninstall')}",
)


async def run_action(page: ft.Page, action: Action, output: ft.TextField, status: ft.Text, buttons: list[ft.Button], busy: ft.ProgressRing) -> None:
	def sanitize_output(message: str) -> str:
		message = message.replace("\r\n", "\n").replace("\r", "\n")
		return ANSI_ESCAPE_RE.sub("", message)

	def append(message: str) -> None:
		output.value = (output.value or "") + sanitize_output(message)
		page.update()

	for button in buttons:
		button.disabled = True
	busy.visible = True
	status.value = f"Running {action.name.lower()}..."
	page.update()

	if IS_WINDOWS:
		append("$ powershell -NoProfile -ExecutionPolicy Bypass -Command <SpotX run.ps1>\n\n")
		process = await asyncio.create_subprocess_exec(
			"powershell",
			"-NoProfile",
			"-ExecutionPolicy",
			"Bypass",
			"-Command",
			WINDOWS_SPOTX_PS,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.STDOUT,
		)
	else:
		append(f"$ {action.command}\n\n")
		process = await asyncio.create_subprocess_shell(
			action.command,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.STDOUT,
		)

	assert process.stdout is not None
	while True:
		line = await process.stdout.readline()
		if not line:
			break
		append(line.decode(errors="replace"))

	return_code = await process.wait()
	append(f"\n[exit code: {return_code}]\n")
	status.value = f"{action.name} finished with exit code {return_code}."

	busy.visible = False
	for button in buttons:
		button.disabled = False
	page.update()


def main(page: ft.Page) -> None:
	page.title = "SpotX One-Click Installer"
	page.window_width = 920
	page.window_height = 760
	page.theme_mode = ft.ThemeMode.DARK
	page.padding = 24
	page.scroll = ft.ScrollMode.AUTO

	output = ft.TextField(
		value="",
		multiline=True,
		read_only=True,
		min_lines=18,
		max_lines=22,
		expand=True,
		border_radius=12,
		text_style=ft.TextStyle(font_family="Menlo", size=13),
	)

	status = ft.Text("Ready.", size=14, weight=ft.FontWeight.W_600)
	busy = ft.ProgressRing(visible=False, stroke_width=3)

	install_button = ft.Button(
		content="Install SpotX",
		icon=ft.Icons.DOWNLOAD,
		bgcolor=ft.Colors.GREEN_700,
		color=ft.Colors.GREEN_100,
	)
	update_button = ft.Button(
		content="Update Spotify",
		icon=ft.Icons.SYSTEM_UPDATE_ALT,
		bgcolor=ft.Colors.BLUE_700,
		color=ft.Colors.BLUE_100,
	)
	uninstall_button = ft.Button(
		content="Uninstall SpotX",
		icon=ft.Icons.DELETE_OUTLINE,
		bgcolor=ft.Colors.RED_700,
		color=ft.Colors.RED_100,
	)

	buttons = [install_button, update_button, uninstall_button]

	async def on_install(_: ft.ControlEvent) -> None:
		await run_action(page, INSTALL_ACTION, output, status, buttons, busy)

	async def on_update(_: ft.ControlEvent) -> None:
		await run_action(page, UPDATE_ACTION, output, status, buttons, busy)

	async def on_uninstall(_: ft.ControlEvent) -> None:
		await run_action(page, UNINSTALL_ACTION, output, status, buttons, busy)

	install_button.on_click = on_install
	update_button.on_click = on_update
	uninstall_button.on_click = on_uninstall

	page.add(
		ft.Column(
			[
				ft.Row(
					[
						ft.Image(src=SPOTIFY_ICON, width=56, height=56),
						ft.Text("SpotX One-Click Installer", size=28, weight=ft.FontWeight.BOLD),
					],
					spacing=12,
					vertical_alignment=ft.CrossAxisAlignment.CENTER,
				),
				ft.Text(
					"Runs the official SpotX Bash script and streams terminal output into this window.",
					size=14,
					color=ft.Colors.BLUE_GREY_200,
				),
				ft.Row([install_button, update_button, uninstall_button, busy], spacing=12),
				status,
				ft.Container(
					content=output,
					expand=True,
					border=ft.Border(
						top=ft.BorderSide(1, ft.Colors.WHITE24),
						right=ft.BorderSide(1, ft.Colors.WHITE24),
						bottom=ft.BorderSide(1, ft.Colors.WHITE24),
						left=ft.BorderSide(1, ft.Colors.WHITE24),
					),
					border_radius=12,
					padding=12,
				),
			],
			expand=True,
			spacing=16,
		)
	)


if __name__ == "__main__":
	ft.run(main, assets_dir=str(ASSETS_DIR))
