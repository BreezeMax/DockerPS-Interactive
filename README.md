# dockerDockerPS-interactive

An interactive terminal user interface (TUI) for managing Docker containers. Built with Python and `curses`, it requires no external dependencies beyond standard Python 3 and Docker.

---

## Why I Built This

Standard `docker ps` output can be a inconvenient. Text wraps awkwardly across line breaks, port mappings clutter the screen, and getting a clean overview of your running containers, stacks, and services feels unnecessarily frustrating. On top of that, constantly typing repetitive terminal commands like `docker exec -it <container_id> /bin/bash` or `docker logs -f` just to perform quick daily tasks breaks your developer flow.

I built **DockerPS-Interactive** as a lightweight, zero-dependency solution to eliminate that daily CLI friction.

Instead of wrestling with messy terminal columns or memorizing container IDs, **DockerPS-Interactive** gives you a clean, keyboard-driven dashboard right inside your shell:

* **Instant Visual Clarity** — Auto-adjusting table layout designed for maximum readability across all terminal sizes.
* **Effortless Searching & Filtering** — Find containers, Docker Compose projects, or specific services quickly.
* **Single-Keystroke Productivity** — Drop into interactive shells, stream live logs, or inspect container states with a single keypress—no retyping required.

Whether you're debugging local microservices or managing Docker Compose stacks, it's the fast, keyboard-first `docker ps` alternative built to keep you in the flow.
---

---

## Features

* 🔍 **Interactive Search & Filtering**: Filter containers by status, Docker Compose project, or service name.
* ↕️ **Sorting**: Sort by creation date, container name, status, project, or service.
* 📋 **Container Details**: View image details, networks, published ports, mounts, command entrypoints, and environment variables.
* 🔐 **Automatic Secret Masking**: Environment variables containing sensitive keywords (`PASSWORD`, `SECRET`, `KEY`, etc.) are automatically masked.
* 📜 **Logs & Execution**: View or follow logs, run interactive `/bin/bash` or `/bin/sh` shells, inspect raw JSON, and stop or restart containers directly.
* ⚡ **CLI Startup Flags**: Launch directly into pre-filtered or pre-sorted views using CLI flags (`--search`, `--status`, `--project`, `--service`, `--sort`, `--desc`/`--asc`) to jump straight to what you need without extra navigation.

---

## Prerequisites

* Python 3.7+
* Docker CLI installed and accessible in your `PATH`
* Linux / macOS (or WSL on Windows)

---

## Quick Start

1. **Make the script executable:**
   ```bash
   chmod +x docker-ps-interactive.py
2. **Run the script**
   ```bash
   ./docker-ps-interactive.py
3. **Create a bash shortcut (optional)**
   ```bash
   echo "alias dps='/path/to/your/DockerPS-Interactive.py'" >> ~/.bashrc
   source ~/.bashrc
    ```
4. **Alternative: Symlink to PATH**
   ```bash
   mkdir -p ~/.local/bin
   ln -s /path/to/your/DockerPS-Interactive.py ~/.local/bin/dps
If you created a (bash) shortcut, Run it with shortcut: dps

## Interactive Shortcuts

## Interactive Shortcuts

### Overview View
| Key | Action |
| :--- | :--- |
| `↑` `↓` / `j` `k` | Select container |
| `Enter` | Open details |
| `/` | Search |
| `f` | Filters |
| `s` | Sort by name |
| `S` | Sort by status |
| `r` | Refresh |
| `c` | Clear search/filters |
| `q` | Quit |

### Detail View
| Key | Action |
| :--- | :--- |
| `L` | View logs |
| `F` | Follow live logs |
| `E` | Execute interactive shell |
| `R` | Restart container |
| `S` | Stop container |
| `I` | View raw inspect JSON |
| `B` / `Esc` | Back |

## CLI Options (--help)
```bash
usage: docker-ps-interactive.py [-h] [-V] [-s SEARCH]
                                [--status {all,running,stopped}]
                                [--project PROJECT] [--service SERVICE]
                                [--sort {created,name,status,project,service}]
                                [--asc | --desc] [--no-color]

Interactive terminal Docker container manager.

options:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -s SEARCH, --search SEARCH
                        Search container name, ID, image, project, service or
                        ports.
  --status {all,running,stopped}
                        Filter by container status.
  --project PROJECT, --stack PROJECT
                        Filter by Docker Compose project.
  --service SERVICE     Filter by Docker Compose service.
  --sort {created,name,status,project,service}
                        Sort containers by this field.
  --asc                 Sort ascending.
  --desc                Sort descending.
  --no-color            Disable terminal colors.

Examples:

  Show all containers:
    ./docker-ps-interactive.py

  Search for postgres:
    ./docker-ps-interactive.py --search postgres

  Show only running containers:
    ./docker-ps-interactive.py --status running

  Show containers from a Compose project:
    ./docker-ps-interactive.py --project myproject

  Show a Compose service:
    ./docker-ps-interactive.py --service web

  Newest containers first:
    ./docker-ps-interactive.py --sort created --desc

  Oldest containers first:
    ./docker-ps-interactive.py --sort created --asc

  Alphabetical by name:
    ./docker-ps-interactive.py --sort name --asc

  Combine filters:
    ./docker-ps-interactive.py \
        --project myproject \
        --status running \
        --sort name

## Usage/Examples

```javascript
import Component from 'my-project'

function App() {
  return <Component />
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
