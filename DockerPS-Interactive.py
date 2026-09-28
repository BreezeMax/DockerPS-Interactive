#!/usr/bin/env python3

import argparse
import curses
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


VERSION = "2.0.0"


# ============================================================
# Colors
# ============================================================

class Colors:
    HEADER = 1
    TITLE = 2
    GREEN = 3
    YELLOW = 4
    RED = 5
    CYAN = 6
    GRAY = 7
    WHITE = 8
    SELECTED = 9


COLOR_ENABLED = True


def init_colors():
    if not COLOR_ENABLED:
        return

    if not curses.has_colors():
        return

    curses.start_color()

    try:
        curses.use_default_colors()
    except curses.error:
        pass

    curses.init_pair(
        Colors.HEADER,
        curses.COLOR_BLACK,
        curses.COLOR_CYAN
    )

    curses.init_pair(
        Colors.TITLE,
        curses.COLOR_CYAN,
        -1
    )

    curses.init_pair(
        Colors.GREEN,
        curses.COLOR_GREEN,
        -1
    )

    curses.init_pair(
        Colors.YELLOW,
        curses.COLOR_YELLOW,
        -1
    )

    curses.init_pair(
        Colors.RED,
        curses.COLOR_RED,
        -1
    )

    curses.init_pair(
        Colors.CYAN,
        curses.COLOR_CYAN,
        -1
    )

    curses.init_pair(
        Colors.GRAY,
        curses.COLOR_WHITE,
        -1
    )

    curses.init_pair(
        Colors.WHITE,
        curses.COLOR_WHITE,
        -1
    )

    curses.init_pair(
        Colors.SELECTED,
        curses.COLOR_BLACK,
        curses.COLOR_CYAN
    )


def color_pair(number):
    if not COLOR_ENABLED:
        return 0

    try:
        return curses.color_pair(number)
    except curses.error:
        return 0


# ============================================================
# CLI
# ============================================================

def build_argument_parser():
    parser = argparse.ArgumentParser(
        prog="docker-list.py",
        description=(
            "Interactive terminal Docker container manager."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  Show all containers:
    ./docker-list.py

  Search for postgres:
    ./docker-list.py --search postgres

  Show only running containers:
    ./docker-list.py --status running

  Show containers from a Compose project:
    ./docker-list.py --project myproject

  Show a Compose service:
    ./docker-list.py --service web

  Newest containers first:
    ./docker-list.py --sort created --desc

  Oldest containers first:
    ./docker-list.py --sort created --asc

  Alphabetical by name:
    ./docker-list.py --sort name --asc

  Combine filters:
    ./docker-list.py \\
        --project myproject \\
        --status running \\
        --sort name

Interactive shortcuts:

  ↑ / ↓ / j / k    Select container
  Enter             Open details
  /                 Search
  f                 Filters
  s                 Sort by name
  S                 Sort by status
  r                 Refresh
  c                 Clear search
  q                 Quit

Detail shortcuts:

  L                 Logs
  F                 Follow logs
  E                 Execute shell
  R                 Restart
  S                 Stop
  I                 Docker inspect
  B / Esc           Back
""",
    )

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}"
    )

    parser.add_argument(
        "-s",
        "--search",
        default="",
        help=(
            "Search container name, ID, image, "
            "project, service or ports."
        )
    )

    parser.add_argument(
        "--status",
        choices=[
            "all",
            "running",
            "stopped"
        ],
        default="all",
        help="Filter by container status."
    )

    parser.add_argument(
        "--project",
        "--stack",
        dest="project",
        default="all",
        help="Filter by Docker Compose project."
    )

    parser.add_argument(
        "--service",
        default="all",
        help="Filter by Docker Compose service."
    )

    parser.add_argument(
        "--sort",
        choices=[
            "created",
            "name",
            "status",
            "project",
            "service"
        ],
        default="created",
        help="Sort containers by this field."
    )

    direction = parser.add_mutually_exclusive_group()

    direction.add_argument(
        "--asc",
        action="store_true",
        help="Sort ascending."
    )

    direction.add_argument(
        "--desc",
        action="store_true",
        help="Sort descending."
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable terminal colors."
    )

    return parser


# ============================================================
# General helpers
# ============================================================

def parse_docker_timestamp(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except (ValueError, TypeError):
        return None


def format_docker_timestamp(value):
    dt = parse_docker_timestamp(value)

    if dt is None:
        return value or "-"

    return dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )


def truncate(text, width):
    text = str(text)

    if width <= 0:
        return ""

    if len(text) <= width:
        return text

    if width <= 3:
        return text[:width]

    return text[:width - 3] + "..."


def terminal_has_docker():
    return shutil.which("docker") is not None


# ============================================================
# Docker command runner
# ============================================================

def run_command(
    command,
    timeout=None,
    stdin=None
):
    """
    Execute a command without invoking a shell.

    Returns:
        stdout string on success
        None on failure
    """

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            stdin=stdin,
            timeout=timeout
        )

        if result.returncode != 0:
            return None

        return result.stdout

    except (
        OSError,
        subprocess.SubprocessError,
        subprocess.TimeoutExpired
    ):
        return None


def run_command_with_error(
    command,
    timeout=None
):
    """
    Same as run_command(), but returns:

        (success, stdout, stderr)
    """

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )

        return (
            result.returncode == 0,
            result.stdout,
            result.stderr
        )

    except (
        OSError,
        subprocess.SubprocessError,
        subprocess.TimeoutExpired
    ) as exc:

        return (
            False,
            "",
            str(exc)
        )


# ============================================================
# Container data model
# ============================================================

@dataclass
class Container:
    id: str
    name: str
    image: str
    status: str
    status_text: str
    running: bool

    created: str
    created_display: str

    started_at: str
    started_at_display: str

    restart_count: int

    project: str
    service: str

    ports: str
    networks: List[str] = field(
        default_factory=list
    )

    mounts: List[str] = field(
        default_factory=list
    )

    command: str = ""
    entrypoint: str = ""

    working_dir: str = ""
    user: str = ""

    restart_policy: str = ""

    environment: List[str] = field(
        default_factory=list
    )


# ============================================================
# Docker manager
# ============================================================

class DockerManager:

    def __init__(self):
        self.last_error = ""

    def _error(self, message):
        self.last_error = message

    # --------------------------------------------------------
    # List containers
    # --------------------------------------------------------

    def list_containers(self):
        self.last_error = ""

        if not terminal_has_docker():
            self._error(
                "Docker executable was not found."
            )
            return []

        success, output, error = run_command_with_error(
            ["docker", "ps", "-aq"]
        )

        if not success:
            self._error(
                error.strip()
                or "Unable to execute docker."
            )
            return []

        ids = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]

        if not ids:
            return []

        # One inspect call for all containers.
        success, output, error = run_command_with_error(
            ["docker", "inspect", *ids]
        )

        if not success:
            self._error(
                error.strip()
                or "Unable to inspect Docker containers."
            )
            return []

        try:
            inspect_data = json.loads(output)

        except json.JSONDecodeError as exc:
            self._error(
                f"Invalid Docker JSON: {exc}"
            )
            return []

        containers = []

        for data in inspect_data:

            try:
                container = self._parse_container(
                    data
                )

                containers.append(container)

            except Exception:
                # One malformed container should not
                # prevent all other containers from showing.
                continue

        return containers

    # --------------------------------------------------------
    # Parse container
    # --------------------------------------------------------

    def _parse_container(self, data):

        config = data.get(
            "Config",
            {}
        )

        state = data.get(
            "State",
            {}
        )

        host_config = data.get(
            "HostConfig",
            {}
        )

        network_settings = data.get(
            "NetworkSettings",
            {}
        )

        labels = config.get(
            "Labels"
        ) or {}

        container_id = data.get(
            "Id",
            ""
        )

        name = data.get(
            "Name",
            ""
        ).lstrip("/")

        if not name:
            name = "-"

        # ----------------------------------------------------
        # Compose
        # ----------------------------------------------------

        project = labels.get(
            "com.docker.compose.project",
            "-"
        )

        service = labels.get(
            "com.docker.compose.service",
            "-"
        )

        # ----------------------------------------------------
        # Created
        # ----------------------------------------------------

        created = data.get(
            "Created",
            ""
        )

        created_display = format_docker_timestamp(
            created
        )

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        status = state.get(
            "Status",
            "unknown"
        )

        running = bool(
            state.get(
                "Running",
                False
            )
        )

        # Use Docker's normalized state as the
        # primary status, instead of docker ps's
        # human-readable "Up 2 hours" value.
        status_text = status.capitalize()

        # ----------------------------------------------------
        # Started At
        # ----------------------------------------------------

        started_at = state.get(
            "StartedAt",
            ""
        )

        started_at_display = (
            format_docker_timestamp(
                started_at
            )
            if started_at
            else "-"
        )

        # ----------------------------------------------------
        # Restart count
        # ----------------------------------------------------

        restart_count = state.get(
            "RestartCount",
            0
        )

        # ----------------------------------------------------
        # Ports
        # ----------------------------------------------------

        ports = []

        port_data = (
            network_settings.get(
                "Ports"
            )
            or {}
        )

        for container_port, bindings in (
            port_data.items()
        ):

            if bindings:

                for binding in bindings:

                    host_ip = binding.get(
                        "HostIp",
                        ""
                    )

                    host_port = binding.get(
                        "HostPort",
                        ""
                    )

                    if host_ip in (
                        "",
                        "0.0.0.0",
                        "::"
                    ):
                        ports.append(
                            f"{host_port}->{container_port}"
                        )

                    else:
                        ports.append(
                            f"{host_ip}:{host_port}"
                            f"->{container_port}"
                        )

            else:
                ports.append(
                    container_port
                )

        ports_text = (
            ", ".join(ports)
            if ports
            else "-"
        )

        # ----------------------------------------------------
        # Networks
        # ----------------------------------------------------

        networks = list(
            (
                network_settings.get(
                    "Networks"
                )
                or {}
            ).keys()
        )

        # ----------------------------------------------------
        # Mounts
        # ----------------------------------------------------

        mount_text = []

        mounts = data.get(
            "Mounts",
            []
        )

        for mount in mounts:

            source = mount.get(
                "Source",
                ""
            )

            destination = mount.get(
                "Destination",
                ""
            )

            mount_type = mount.get(
                "Type",
                ""
            )

            mode = mount.get(
                "Mode",
                ""
            )

            rw = mount.get(
                "RW",
                True
            )

            if mode:
                mode_text = mode

            else:
                mode_text = (
                    "rw"
                    if rw
                    else "ro"
                )

            mount_text.append(
                f"{source} -> {destination} "
                f"({mount_type}, {mode_text})"
            )

        # ----------------------------------------------------
        # Command / entrypoint
        # ----------------------------------------------------

        command_parts = (
            config.get("Cmd")
            or []
        )

        entrypoint_parts = (
            config.get("Entrypoint")
            or []
        )

        command_text = " ".join(
            str(x)
            for x in command_parts
        )

        entrypoint_text = " ".join(
            str(x)
            for x in entrypoint_parts
        )

        # ----------------------------------------------------
        # User
        # ----------------------------------------------------

        user = config.get(
            "User",
            ""
        )

        if not user:
            user = "root"

        # ----------------------------------------------------
        # Working directory
        # ----------------------------------------------------

        working_dir = config.get(
            "WorkingDir",
            ""
        )

        # ----------------------------------------------------
        # Restart policy
        # ----------------------------------------------------

        restart_policy = (
            host_config
            .get(
                "RestartPolicy",
                {}
            )
            .get(
                "Name",
                ""
            )
        )

        # ----------------------------------------------------
        # Environment
        # ----------------------------------------------------

        environment = config.get(
            "Env",
            []
        )

        return Container(
            id=container_id,
            name=name,
            image=config.get(
                "Image",
                "-"
            ),
            status=status,
            status_text=status_text,
            running=running,
            created=created,
            created_display=created_display,
            started_at=started_at,
            started_at_display=started_at_display,
            restart_count=restart_count,
            project=project,
            service=service,
            ports=ports_text,
            networks=networks,
            mounts=mount_text,
            command=command_text,
            entrypoint=entrypoint_text,
            working_dir=working_dir,
            user=user,
            restart_policy=restart_policy,
            environment=environment
        )

    # --------------------------------------------------------
    # Logs
    # --------------------------------------------------------

    def logs(
        self,
        container_id,
        lines=50
    ):

        success, output, error = (
            run_command_with_error(
                [
                    "docker",
                    "logs",
                    "--tail",
                    str(lines),
                    container_id
                ]
            )
        )

        if not success:
            self._error(
                error.strip()
                or "Unable to retrieve logs."
            )

            return [
                self.last_error
            ]

        return output.splitlines()

    # --------------------------------------------------------
    # Inspect
    # --------------------------------------------------------

    def inspect(self, container_id):

        success, output, error = (
            run_command_with_error(
                [
                    "docker",
                    "inspect",
                    container_id
                ]
            )
        )

        if not success:
            self._error(
                error.strip()
                or "Unable to retrieve docker inspect."
            )

            return None

        return output

    # --------------------------------------------------------
    # Restart
    # --------------------------------------------------------

    def restart(self, container_id):

        success, output, error = (
            run_command_with_error(
                [
                    "docker",
                    "restart",
                    container_id
                ]
            )
        )

        if not success:
            self._error(
                error.strip()
                or "Restart failed."
            )

            return False

        return True

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    def stop(self, container_id):

        success, output, error = (
            run_command_with_error(
                [
                    "docker",
                    "stop",
                    container_id
                ]
            )
        )

        if not success:
            self._error(
                error.strip()
                or "Stop failed."
            )

            return False

        return True


# ============================================================
# Secret masking
# ============================================================

SENSITIVE_ENV_NAMES = (
    "PASSWORD",
    "PASSWD",
    "PASS",
    "SECRET",
    "TOKEN",
    "API_KEY",
    "APIKEY",
    "PRIVATE_KEY",
    "ACCESS_KEY",
    "SECRET_KEY",
    "CREDENTIAL",
    "CREDENTIALS",
)


def is_sensitive_environment_name(name):
    upper = name.upper()

    return any(
        keyword in upper
        for keyword in SENSITIVE_ENV_NAMES
    )


def mask_environment(environment):
    result = []

    for item in environment:

        name, separator, value = (
            item.partition("=")
        )

        if (
            separator
            and is_sensitive_environment_name(
                name
            )
        ):
            value = "********"

        result.append(
            f"{name}{separator}{value}"
        )

    return result


# ============================================================
# Curses helpers
# ============================================================

def safe_addstr(
    window,
    y,
    x,
    text,
    attr=0
):
    try:

        max_y, max_x = (
            window.getmaxyx()
        )

        if y < 0 or y >= max_y:
            return

        if x < 0 or x >= max_x:
            return

        text = str(text)

        available = max_x - x - 1

        if available <= 0:
            return

        window.addnstr(
            y,
            x,
            text,
            available,
            attr
        )

    except curses.error:
        pass


def status_color(container):
    if container.running:
        return Colors.GREEN

    if container.status in (
        "restarting",
        "paused"
    ):
        return Colors.YELLOW

    return Colors.RED


def confirm_action(
    window,
    message
):
    max_y, max_x = (
        window.getmaxyx()
    )

    y = max_y // 2

    window.move(y, 0)
    window.clrtoeol()

    safe_addstr(
        window,
        y,
        max(
            0,
            (max_x - len(message)) // 2
        ),
        message,
        curses.A_BOLD
        | color_pair(Colors.YELLOW)
    )

    window.refresh()

    while True:

        key = window.getch()

        if key in (
            ord("y"),
            ord("Y")
        ):
            return True

        if key in (
            ord("n"),
            ord("N"),
            27
        ):
            return False


# ============================================================
# Docker UI
# ============================================================

class DockerUI:

    def __init__(
        self,
        stdscr,
        docker,
        args
    ):

        self.stdscr = stdscr
        self.docker = docker
        self.args = args

        self.containers = []
        self.filtered = []

        self.selected = 0
        self.scroll = 0

        self.search = args.search or ""

        self.sort_mode = args.sort

        if args.asc:
            self.sort_reverse = False

        elif args.desc:
            self.sort_reverse = True

        else:
            # Default: newest first.
            self.sort_reverse = True

        self.filter_status = args.status

        self.filter_project = args.project

        self.filter_service = args.service

        self.message = ""

        self.refresh_containers()

    # ========================================================
    # Data
    # ========================================================

    def refresh_containers(self):

        self.containers = (
            self.docker.list_containers()
        )

        if self.docker.last_error:

            self.message = (
                self.docker.last_error
            )

        else:

            self.message = (
                f"{len(self.containers)} "
                f"container(s) loaded."
            )

        self.apply_filters()

    def apply_filters(self):

        result = []

        search = (
            self.search.strip().lower()
        )

        for container in self.containers:

            # ------------------------------------------------
            # Search
            # ------------------------------------------------

            if search:

                searchable = " ".join([
                    container.name,
                    container.id,
                    container.image,
                    container.project,
                    container.service,
                    container.ports,
                    container.status,
                ]).lower()

                if search not in searchable:
                    continue

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            if self.filter_status == "running":

                if not container.running:
                    continue

            elif self.filter_status == "stopped":

                if container.running:
                    continue

            # ------------------------------------------------
            # Project
            # ------------------------------------------------

            if (
                self.filter_project != "all"
                and
                container.project
                != self.filter_project
            ):
                continue

            # ------------------------------------------------
            # Service
            # ------------------------------------------------

            if (
                self.filter_service != "all"
                and
                container.service
                != self.filter_service
            ):
                continue

            result.append(container)

        # ====================================================
        # Sorting
        # ====================================================

        if self.sort_mode == "name":

            result.sort(
                key=lambda x:
                    x.name.lower(),
                reverse=self.sort_reverse
            )

        elif self.sort_mode == "status":

            result.sort(
                key=lambda x: (
                    x.running,
                    x.status,
                    x.name.lower()
                ),
                reverse=self.sort_reverse
            )

        elif self.sort_mode == "project":

            result.sort(
                key=lambda x: (
                    x.project.lower(),
                    x.name.lower()
                ),
                reverse=self.sort_reverse
            )

        elif self.sort_mode == "service":

            result.sort(
                key=lambda x: (
                    x.service.lower(),
                    x.name.lower()
                ),
                reverse=self.sort_reverse
            )

        else:

            # Created timestamp is intentionally sorted
            # as a string. Docker uses ISO-8601 timestamps,
            # making lexical ordering correct and preserving
            # nanosecond precision that Python datetime does not.
            result.sort(
                key=lambda x:
                    x.created,
                reverse=self.sort_reverse
            )

        self.filtered = result

        if self.selected >= len(
            self.filtered
        ):

            self.selected = max(
                0,
                len(self.filtered) - 1
            )

    # ========================================================
    # Header
    # ========================================================

    def draw_header(self, title):

        max_y, max_x = (
            self.stdscr.getmaxyx()
        )

        safe_addstr(
            self.stdscr,
            0,
            0,
            " Docker Manager ",
            color_pair(Colors.HEADER)
            | curses.A_BOLD
        )

        safe_addstr(
            self.stdscr,
            1,
            0,
            title,
            color_pair(Colors.TITLE)
            | curses.A_BOLD
        )

        safe_addstr(
            self.stdscr,
            2,
            0,
            "=" * max(
                0,
                max_x - 1
                   
            ),
            color_pair(Colors.GRAY)
        )

    # ========================================================
    # Overview
    # ========================================================

    def draw_overview(self):

        self.stdscr.erase()

        max_y, max_x = (
            self.stdscr.getmaxyx()
        )

        self.draw_header(
            "Container overview"
        )

        # ----------------------------------------------------
        # Filters
        # ----------------------------------------------------

        filter_line = (
            f"Search: {self.search or '-'}    "
            f"Status: {self.filter_status}    "
            f"Project: {self.filter_project}    "
            f"Service: {self.filter_service}"
        )

        safe_addstr(
            self.stdscr,
            3,
            0,
            filter_line,
            color_pair(Colors.GRAY)
        )

        # ----------------------------------------------------
        # Sort
        # ----------------------------------------------------

        direction = (
            "DESC"
            if self.sort_reverse
            else "ASC"
        )

        sort_text = (
            f"Sort: {self.sort_mode} {direction}"
        )

        safe_addstr(
            self.stdscr,
            4,
            0,
            sort_text,
            color_pair(Colors.CYAN)
        )

        # ----------------------------------------------------
        # Columns
        # ----------------------------------------------------

        top = 6

        gap = 2
        base_widths = [30, 12, 20, 26, 30]
        col_widths = list(base_widths)
         

        total_base = sum(col_widths) + gap * (len(col_widths) - 1)
        extra_space = max_x - 1 - total_base

        if extra_space > 0:
            col_widths[0] += extra_space // 3
            col_widths[4] += extra_space - (extra_space // 3)

        col_x = []
        curr_x = 0

        for w in col_widths:
            col_x.append(curr_x)
            curr_x += w + gap

        columns = [
            "Container",
            "Status",
            "Created At",
            "Project / Service",
            "Image / Ports"
        ]

        for i, column in enumerate(
            columns
        ):

            x = col_x[i]

            safe_addstr(
                self.stdscr,
                top,
                x,
                truncate(
                    column,
                    col_widths[i]
                ),
                curses.A_BOLD
                | color_pair(Colors.HEADER)
            )

        safe_addstr(
            self.stdscr,
            top + 1,
            0,
            "-" * max(
                0,
                max_x - 1
                   
            ),
            color_pair(Colors.GRAY)
        )

        # ----------------------------------------------------
        # No containers
        # ----------------------------------------------------

        if not self.filtered:

            safe_addstr(
                self.stdscr,
                top + 3,
                2,
                "No containers found.",
                color_pair(Colors.YELLOW)
            )

            self.draw_footer()

            self.stdscr.refresh()

            return

        # ----------------------------------------------------
        # Visible rows
        # ----------------------------------------------------

        visible_height = max(
            1,
            max_y - top - 5
        )

        if self.selected < self.scroll:

            self.scroll = self.selected

        if (
            self.selected
            >= self.scroll
            + visible_height
        ):

            self.scroll = (
                self.selected
                - visible_height
                + 1
            )

        for row in range(
            visible_height
        ):

            index = (
                self.scroll
                + row
            )

            if index >= len(
                self.filtered
            ):
                break

            container = self.filtered[
                index
            ]

            y = (
                top
                + 2
                + row
            )

            selected = (
                index
                == self.selected
            )

            attr = (
                color_pair(Colors.SELECTED)
                if selected
                else 0
            )

            # ------------------------------------------------
            # Values
            # ------------------------------------------------

            name = (
                f"{container.name} "
                f"({container.id[:12]})"
            )

            status = container.status_text

            created = (
                container.created_display
            )

            project_service = (
                f"{container.project} / "
                f"{container.service}"
            )

            image_ports = (
                f"{container.image} "
                f"{container.ports}"
            )

            values = [
                name,
                status,
                created,
                project_service,
                image_ports
            ]

            # ------------------------------------------------
            # Draw
            # ------------------------------------------------

            for col, value in enumerate(
                values
            ):

                x = col_x[col]
                       
                               
                 

                width = col_widths[col]
                      
                                 
                 

                if col == 1:

                    status_attr = attr

                    if not selected:

                        status_attr |= (
                            color_pair(
                                status_color(
                                    container
                                )
                            )
                        )

                    safe_addstr(
                        self.stdscr,
                        y,
                        x,
                        truncate(
                            value,
                            width
                        ),
                        status_attr
                    )

                else:

                    safe_addstr(
                        self.stdscr,
                        y,
                        x,
                        truncate(
                            value,
                            width
                        ),
                        attr
                    )

        self.draw_footer()

        self.stdscr.refresh()

    # ========================================================
    # Footer
    # ========================================================

    def draw_footer(self):

        max_y, max_x = (
            self.stdscr.getmaxyx()
        )

        footer = (
            "↑↓ Select  "
            "Enter Details  "
            "s Name  "
            "S Status  "
            "r Refresh  "
            "/ Search  "
            "f Filters  "
            "c Clear  "
            "q Quit"
        )

        safe_addstr(
            self.stdscr,
            max_y - 2,
            0,
            footer,
            color_pair(Colors.HEADER)
        )

        safe_addstr(
            self.stdscr,
            max_y - 1,
            0,
            self.message,
            color_pair(Colors.YELLOW)
        )

    # ========================================================
    # Search
    # ========================================================

    def search_container(self):

        curses.echo()

        max_y, max_x = (
            self.stdscr.getmaxyx()
        )

        self.stdscr.move(
            max_y - 1,
            0
        )

        self.stdscr.clrtoeol()

        safe_addstr(
            self.stdscr,
            max_y - 1,
            0,
            "Search: "
        )

        try:

            value = self.stdscr.getstr(
                max_y - 1,
                8,
                max(
                    1,
                    max_x - 9
                )
            ).decode(
                "utf-8",
                errors="replace"
            )

        except Exception:

            value = ""

        curses.noecho()

        self.search = value.strip()

        self.selected = 0
        self.scroll = 0

        self.apply_filters()

    # ========================================================
    # Sorting
    # ========================================================

    def toggle_sort(
        self,
        mode,
        default_reverse=False
    ):

        if self.sort_mode == mode:

            self.sort_reverse = (
                not self.sort_reverse
            )

        else:

            self.sort_mode = mode

            self.sort_reverse = (
                default_reverse
            )

        self.apply_filters()

    # ========================================================
    # Filter menu
    # ========================================================

    def filter_menu(self):

        projects = sorted(
            set(
                c.project
                for c in self.containers
            )
        )

        services = sorted(
            set(
                c.service
                for c in self.containers
            )
        )

        statuses = [
            "all",
            "running",
            "stopped"
        ]

        project_options = (
            ["all"]
            + projects
        )

        service_options = (
            ["all"]
            + services
        )

        menu_items = [
            [
                "Status",
                statuses,
                self.filter_status
            ],
            [
                "Project",
                project_options,
                self.filter_project
            ],
            [
                "Service",
                service_options,
                self.filter_service
            ]
        ]

        current_menu = 0

        while True:

            self.stdscr.erase()

            self.draw_header(
                "Filters"
            )

            y = 4

            for i, (
                label,
                options,
                current
            ) in enumerate(
                menu_items
            ):

                attr = (
                    color_pair(
                        Colors.SELECTED
                    )
                    if i == current_menu
                    else curses.A_BOLD
                )

                safe_addstr(
                    self.stdscr,
                    y,
                    2,
                    f"{label}: {current}",
                    attr
                )

                y += 2

            safe_addstr(
                self.stdscr,
                y + 1,
                2,
                "↑↓ Select   "
                "←→ Change   "
                "Enter Apply   "
                "Esc Cancel",
                color_pair(Colors.GRAY)
            )

            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key in (
                curses.KEY_UP,
                ord("k")
            ):

                current_menu = max(
                    0,
                    current_menu - 1
                )

            elif key in (
                curses.KEY_DOWN,
                ord("j")
            ):

                current_menu = min(
                    len(menu_items) - 1,
                    current_menu + 1
                )

            elif key in (
                curses.KEY_LEFT,
                curses.KEY_RIGHT
            ):

                (
                    label,
                    options,
                    current
                ) = menu_items[
                    current_menu
                ]

                try:
                    current_index = (
                        options.index(
                            current
                        )
                    )

                except ValueError:
                    current_index = 0

                if key == curses.KEY_LEFT:
                    current_index -= 1

                else:
                    current_index += 1

                current_index %= len(
                    options
                )

                menu_items[
                    current_menu
                ] = [
                    label,
                    options,
                    options[
                        current_index
                    ]
                ]

            elif key in (
                curses.KEY_ENTER,
                10,
                13
            ):

                self.filter_status = (
                    menu_items[0][2]
                )

                self.filter_project = (
                    menu_items[1][2]
                )

                self.filter_service = (
                    menu_items[2][2]
                )

                self.selected = 0
                self.scroll = 0

                self.apply_filters()

                return

            elif key == 27:

                return

    # ========================================================
    # Detail page
    # ========================================================

    def detail_page(
        self,
        container
    ):

        while True:

            self.stdscr.erase()

            max_y, max_x = (
                self.stdscr.getmaxyx()
            )

            title = (
                f"{container.name} "
                f"({container.id[:12]})"
            )

            self.draw_header(
                title
            )

            y = 4

            # ------------------------------------------------
            # Container
            # ------------------------------------------------

            y = self.draw_section_title(
                y,
                "Container"
            )

            y = self.draw_field(
                y,
                "Name",
                container.name
            )

            y = self.draw_field(
                y,
                "ID",
                container.id
            )

            y = self.draw_field(
                y,
                "Status",
                container.status_text,
                color_pair(
                    status_color(
                        container
                    )
                )
            )

            y = self.draw_field(
                y,
                "Created At",
                container.created_display
            )

            y = self.draw_field(
                y,
                "Started At",
                container.started_at_display
            )

            y = self.draw_field(
                y,
                "Restart count",
                container.restart_count
            )

            y = self.draw_field(
                y,
                "Restart policy",
                container.restart_policy or "-"
            )

            y += 1

            # ------------------------------------------------
            # Compose
            # ------------------------------------------------

            y = self.draw_section_title(
                y,
                "Docker Compose"
            )

            y = self.draw_field(
                y,
                "Project",
                container.project
            )

            y = self.draw_field(
                y,
                "Service",
                container.service
            )

            y += 1

            # ------------------------------------------------
            # Runtime
            # ------------------------------------------------

            y = self.draw_section_title(
                y,
                "Runtime"
            )

            y = self.draw_field(
                y,
                "Image",
                container.image
            )

            y = self.draw_field(
                y,
                "User",
                container.user
            )

            y = self.draw_field(
                y,
                "Working dir",
                container.working_dir or "-"
            )

            y = self.draw_field(
                y,
                "Networks",
                ", ".join(
                    container.networks
                ) or "-"
            )

            y = self.draw_field(
                y,
                "Ports",
                container.ports
            )

            y += 1

            # ------------------------------------------------
            # Command
            # ------------------------------------------------

            y = self.draw_section_title(
                y,
                "Command"
            )

            y = self.draw_field(
                y,
                "Entrypoint",
                container.entrypoint or "-"
            )

            y = self.draw_field(
                y,
                "Command",
                container.command or "-"
            )

            # ------------------------------------------------
            # Mounts / Environment
            # ------------------------------------------------

            # These sections have priority over recent logs.
            # Recent logs are only shown in the space that remains
            # after the complete Environment section has been drawn.
            footer_y = max_y - 1

            if y < footer_y - 1:

                y += 1

                y = self.draw_section_title(
                    y,
                    "Mounts"
                )

                for mount in container.mounts:

                    if y >= footer_y:
                        break

                    safe_addstr(
                        self.stdscr,
                        y,
                        2,
                        mount,
                        color_pair(
                            Colors.GRAY
                        )
                    )

                    y += 1

            # Environment has priority over logs. Do not reserve
            # any space for logs while drawing it.
            if y < footer_y - 1:

                y += 1

                y = self.draw_section_title(
                    y,
                    "Environment"
                )

                masked_environment = (
                    mask_environment(
                        container.environment
                    )
                )

                for env in masked_environment:

                    if y >= footer_y:
                        break

                    safe_addstr(
                        self.stdscr,
                        y,
                        2,
                        env,
                        color_pair(
                            Colors.GRAY
                        )
                    )

                    y += 1

            # ------------------------------------------------
            # Recent logs
            # ------------------------------------------------

            # Logs are shown directly below Environment. If there
            # is no vertical space left before the footer, they are
            # not shown at all; use [L] Logs to inspect them.
            available_log_lines = footer_y - y - 2

            if available_log_lines > 0:

                logs = self.docker.logs(
                    container.id,
                    100
                )

                visible_logs = logs[
                    -available_log_lines:
                ]

                if visible_logs:

                    log_y = y + 1

                    safe_addstr(
                        self.stdscr,
                        log_y,
                        0,
                        "Recent logs",
                        color_pair(Colors.CYAN)
                        | curses.A_BOLD
                    )

                    for i, line in enumerate(
                        visible_logs
                    ):
                        safe_addstr(
                            self.stdscr,
                            log_y + 1 + i,
                            2,
                            line,
                            color_pair(Colors.GRAY)
                        )

            # ------------------------------------------------
            # Footer
            # ------------------------------------------------

            footer = (
                "[L] Logs  "
                "[F] Follow  "
                "[E] Shell  "
                "[R] Restart  "
                "[S] Stop  "
                "[I] Inspect  "
                "[B] Back"
            )

            safe_addstr(
                self.stdscr,
                max_y - 1,
                0,
                footer,
                color_pair(Colors.HEADER)
            )

            self.stdscr.refresh()

            key = self.stdscr.getch()

            # ------------------------------------------------
            # Back
            # ------------------------------------------------

            if key in (
                27,
                ord("b"),
                ord("B")
            ):
                return

            # ------------------------------------------------
            # Logs
            # ------------------------------------------------

            elif key in (
                ord("l"),
                ord("L")
            ):

                self.logs_page(
                    container,
                    follow=False
                )

            # ------------------------------------------------
            # Follow logs
            # ------------------------------------------------

            elif key in (
                ord("f"),
                ord("F")
            ):

                self.follow_logs(
                    container
                )

            # ------------------------------------------------
            # Shell
            # ------------------------------------------------

            elif key in (
                ord("e"),
                ord("E")
            ):

                self.exec_shell(
                    container
                )

            # ------------------------------------------------
            # Restart
            # ------------------------------------------------

            elif key == ord("R"):

                if not confirm_action(
                    self.stdscr,
                    f"Restart '{container.name}'? [y/n]"
                ):
                    continue

                if self.docker.restart(
                    container.id
                ):

                    self.message = (
                        f"Container '{container.name}' "
                        f"restarted."
                    )

                else:

                    self.message = (
                        self.docker.last_error
                        or "Restart failed."
                    )

                self.refresh_containers()

                updated = self.find_container(
                    container.id
                )

                if updated:
                    container = updated

            # ------------------------------------------------
            # Stop
            # ------------------------------------------------

            elif key == ord("S"):

                if not container.running:

                    self.message = (
                        "Container is already stopped."
                    )

                    continue

                if not confirm_action(
                    self.stdscr,
                    f"Stop '{container.name}'? [y/n]"
                ):
                    continue

                if self.docker.stop(
                    container.id
                ):

                    self.message = (
                        f"Container '{container.name}' "
                        f"stopped."
                    )

                else:

                    self.message = (
                        self.docker.last_error
                        or "Stop failed."
                    )

                self.refresh_containers()

                updated = self.find_container(
                    container.id
                )

                if updated:
                    container = updated

            # ------------------------------------------------
            # Inspect
            # ------------------------------------------------

            elif key in (
                ord("i"),
                ord("I")
            ):

                self.inspect_page(
                    container
                )

    # ========================================================
    # Detail helpers
    # ========================================================

    def draw_section_title(
        self,
        y,
        title
    ):

        safe_addstr(
            self.stdscr,
            y,
            0,
            title,
            color_pair(Colors.CYAN)
            | curses.A_BOLD
        )

        return y + 1

    def draw_field(
        self,
        y,
        label,
        value,
        attr=0
    ):

        safe_addstr(
            self.stdscr,
            y,
            0,
            f"{label}:",
            curses.A_BOLD
        )

        safe_addstr(
            self.stdscr,
            y,
            18,
            value,
            attr
        )

        return y + 1

    def find_container(
        self,
        container_id
    ):

        for container in self.containers:

            if container.id == container_id:
                return container

        return None

    # ========================================================
    # Logs page
    # ========================================================

    def logs_page(
        self,
        container,
        follow=False
    ):

        if follow:
            self.follow_logs(
                container
            )
            return

        logs = self.docker.logs(
            container.id,
            200
        )

        scroll = max(
            0,
            len(logs) - 1
        )

        while True:

            self.stdscr.erase()

            max_y, max_x = (
                self.stdscr.getmaxyx()
            )

            self.draw_header(
                f"Logs — {container.name}"
            )

            available = max(
                1,
                max_y - 6
            )

            max_scroll = max(
                0,
                len(logs) - available
            )

            scroll = min(
                scroll,
                max_scroll
            )

            visible = logs[
                scroll:
                scroll + available
            ]

            for i, line in enumerate(
                visible
            ):

                safe_addstr(
                    self.stdscr,
                    4 + i,
                    0,
                    line,
                    color_pair(
                        Colors.GRAY
                    )
                )

            footer = (
                "↑↓/jk Scroll  "
                "Home/End  "
                "F Follow  "
                "R Refresh  "
                "B/Esc Back"
            )

            safe_addstr(
                self.stdscr,
                max_y - 1,
                0,
                footer,
                color_pair(Colors.HEADER)
            )

            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key in (
                27,
                ord("b"),
                ord("B")
            ):
                return

            elif key in (
                curses.KEY_UP,
                ord("k")
            ):

                scroll = max(
                    0,
                    scroll - 1
                )

            elif key in (
                curses.KEY_DOWN,
                ord("j")
            ):

                scroll = min(
                    max_scroll,
                    scroll + 1
                )

            elif key == curses.KEY_HOME:

                scroll = 0

            elif key == curses.KEY_END:

                scroll = max_scroll

            elif key in (
                ord("f"),
                ord("F")
            ):

                self.follow_logs(
                    container
                )

            elif key in (
                ord("r"),
                ord("R")
            ):

                logs = self.docker.logs(
                    container.id,
                    200
                )

                max_scroll = max(
                    0,
                    len(logs) - available
                )

                scroll = max_scroll

    # ========================================================
    # Follow logs
    # ========================================================

    def follow_logs(
        self,
        container
    ):

        self.leave_curses()

        try:

            print()
            print(
                f"Following logs for "
                f"{container.name}"
            )

            print(
                "Press Ctrl+C to return."
            )

            print()

            try:

                subprocess.run(
                    [
                        "docker",
                        "logs",
                        "--tail",
                        "50",
                        "--follow",
                        container.id
                    ],
                    check=False
                )

            except OSError as exc:

                print(
                    f"Unable to execute docker: {exc}"
                )

        except KeyboardInterrupt:

            pass

        finally:

            self.restore_curses()

    # ========================================================
    # Execute shell
    # ========================================================

    def exec_shell(
        self,
        container
    ):

        if not container.running:

            self.message = (
                "Container is not running."
            )

            return

        self.leave_curses()

        try:

            print()
            print(
                f"Opening shell in "
                f"{container.name}"
            )

            print(
                "Trying /bin/bash..."
            )

            result = subprocess.call(
                [
                    "docker",
                    "exec",
                    "-it",
                    container.id,
                    "/bin/bash"
                ]
            )

            # Some containers do not contain bash. In that case
            # fall back to the more widely available /bin/sh.
            if result != 0:

                print()
                print(
                    "/bin/bash failed, trying /bin/sh..."
                )

                result = subprocess.call(
                    [
                        "docker",
                        "exec",
                        "-it",
                        container.id,
                        "/bin/sh"
                    ]
                )

            if result != 0:

                print()
                print(
                    "Shell exited."
                )

                input(
                    "Press Enter to return..."
                )

        except KeyboardInterrupt:

            pass

        except OSError as exc:

            print(
                f"Exec failed: {exc}"
            )

            input(
                "Press Enter to return..."
            )

        finally:

            self.restore_curses()

    # ========================================================
    # Inspect
    # ========================================================

    def inspect_page(
        self,
        container
    ):

        output = self.docker.inspect(
            container.id
        )

        if output is None:

            output_lines = [
                self.docker.last_error
                or "Unable to retrieve docker inspect."
            ]

        else:

            try:

                data = json.loads(
                    output
                )

                formatted = json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                )

                output_lines = (
                    formatted.splitlines()
                )

            except json.JSONDecodeError:

                output_lines = (
                    output.splitlines()
                )

        scroll = 0

        while True:

            self.stdscr.erase()

            max_y, max_x = (
                self.stdscr.getmaxyx()
            )

            self.draw_header(
                "Docker Inspect"
            )

            available = max(
                1,
                max_y - 5
            )

            max_scroll = max(
                0,
                len(output_lines)
                - available
            )

            scroll = min(
                max(
                    0,
                    scroll
                ),
                max_scroll
            )

            visible_lines = (
                output_lines[
                    scroll:
                    scroll + available
                ]
            )

            for i, line in enumerate(
                visible_lines
            ):

                safe_addstr(
                    self.stdscr,
                    4 + i,
                    0,
                    line,
                    color_pair(
                        Colors.GRAY
                    )
                )

            safe_addstr(
                self.stdscr,
                max_y - 1,
                0,
                "↑↓/jk Scroll  "
                "Home/End  "
                "B/Esc Back",
                color_pair(Colors.HEADER)
            )

            self.stdscr.refresh()

            key = self.stdscr.getch()

            if key in (
                27,
                ord("b"),
                ord("B")
            ):
                return

            elif key in (
                curses.KEY_UP,
                ord("k")
            ):

                scroll = max(
                    0,
                    scroll - 1
                )

            elif key in (
                curses.KEY_DOWN,
                ord("j")
            ):

                scroll = min(
                    max_scroll,
                    scroll + 1
                )

            elif key == curses.KEY_HOME:

                scroll = 0

            elif key == curses.KEY_END:

                scroll = max_scroll

    # ========================================================
    # Curses external command handling
    # ========================================================

    def leave_curses(self):

        try:
            curses.def_prog_mode()
        except curses.error:
            pass

        try:
            curses.endwin()
        except curses.error:
            pass

    def restore_curses(self):

        try:
            curses.reset_prog_mode()
        except curses.error:
            pass

        try:
            curses.curs_set(0)
        except curses.error:
            pass

        self.stdscr.clear()
        self.stdscr.refresh()

    # ========================================================
    # Main loop
    # ========================================================

    def run(self):

        while True:

            self.draw_overview()

            key = self.stdscr.getch()

            # ------------------------------------------------
            # Resize
            # ------------------------------------------------

            if key == curses.KEY_RESIZE:

                continue

            # ------------------------------------------------
            # Quit
            # ------------------------------------------------

            if key in (
                ord("q"),
                ord("Q")
            ):

                break

            # ------------------------------------------------
            # Up
            # ------------------------------------------------

            elif key in (
                curses.KEY_UP,
                ord("k")
            ):

                if self.filtered:

                    self.selected = max(
                        0,
                        self.selected - 1
                    )

            # ------------------------------------------------
            # Down
            # ------------------------------------------------

            elif key in (
                curses.KEY_DOWN,
                ord("j")
            ):

                if self.filtered:

                    self.selected = min(
                        len(
                            self.filtered
                        ) - 1,
                        self.selected + 1
                    )

            # ------------------------------------------------
            # Enter
            # ------------------------------------------------

            elif key in (
                curses.KEY_ENTER,
                10,
                13
            ):

                if self.filtered:

                    container = (
                        self.filtered[
                            self.selected
                        ]
                    )

                    self.detail_page(
                        container
                    )

            # ------------------------------------------------
            # Search
            # ------------------------------------------------

            elif key == ord("/"):

                self.search_container()

            # ------------------------------------------------
            # Sort name
            # ------------------------------------------------

            elif key == ord("s"):

                self.toggle_sort(
                    "name",
                    default_reverse=False
                )

            # ------------------------------------------------
            # Sort status
            # ------------------------------------------------

            elif key == ord("S"):

                self.toggle_sort(
                    "status",
                    default_reverse=False
                )

            # ------------------------------------------------
            # Filters
            # ------------------------------------------------

            elif key == ord("f"):

                self.filter_menu()

            # ------------------------------------------------
            # Refresh
            # ------------------------------------------------

            elif key == ord("r"):

                self.refresh_containers()

            # ------------------------------------------------
            # Clear search / filters / sorting
            # ------------------------------------------------

            elif key == ord("c"):
                # Return completely to the default overview state.
                self.search = ""
                self.filter_status = "all"
                self.filter_project = "all"
                self.filter_service = "all"
                self.sort_mode = "created"
                self.sort_reverse = True

                self.selected = 0
                self.scroll = 0

                self.apply_filters()

                self.message = (
                    "Search, filters and sorting cleared."
                )


# ============================================================
# Curses entry point
# ============================================================

def curses_main(
    stdscr,
    args
):

    try:
        curses.curs_set(0)
    except curses.error:
        pass

    stdscr.keypad(True)

    init_colors()

    docker = DockerManager()

    ui = DockerUI(
        stdscr,
        docker,
        args
    )

    ui.run()


# ============================================================
# Main
# ============================================================

def main():

    global COLOR_ENABLED

    parser = build_argument_parser()

    args = parser.parse_args()

    COLOR_ENABLED = not args.no_color

    if not terminal_has_docker():

        print(
            "Error: docker executable was not found.",
            file=sys.stderr
        )

        print(
            "Make sure Docker is installed and "
            "available in PATH.",
            file=sys.stderr
        )

        return 1

    try:

        curses.wrapper(
            curses_main,
            args
        )

    except KeyboardInterrupt:

        pass

    except curses.error as exc:

        print(
            f"Terminal error: {exc}",
            file=sys.stderr
        )

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
