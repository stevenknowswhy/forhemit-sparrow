# Sparrow Desktop App

Local-first expense reduction agent built with Rust + Tauri.

## Structure

```
sparrow-app/
├── Cargo.toml              # Core Rust crate (libs, scoring, DB)
├── src/                    # Shared Rust code
│   └── main.rs
├── src-tauri/              # Tauri desktop wrapper
│   ├── Cargo.toml
│   ├── src/
│   │   ├── main.rs         # Desktop entry point
│   │   └── lib.rs          # Tauri builder
│   └── tauri.conf.json     # Tauri config
└── src/                    # Frontend (HTML/CSS/JS)
    └── index.html
```

## Setup

Requires Rust toolchain. Install via:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Then:
```bash
cd sparrow-app
cargo build
```

To build the Tauri desktop app (requires Tauri CLI):
```bash
cargo install tauri-cli --version "^2"
cargo tauri dev
```

## Architecture

The Rust core handles:
- Encrypted SQLite database (rusqlite + SQLCipher)
- Communication with Python agent via IPC
- UI rendering via Tauri WebView

The Python agent (in `agent/`) handles:
- LLM inference (Agnes AI / OpenRouter)
- Brave Search integration
- 8-dimension rubric scoring
- HTML report generation

They communicate via stdin/stdout or local TCP socket.
