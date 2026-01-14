# PrometheanProxy Overview

PrometheanProxy is a modular and multi-platform Command and Control (C2) framework designed for cybersecurity professionals for authorized red teaming and post-exploitation exercises. It provides a robust system for managing remote agents (implants) across different operating systems.

## Core Philosophy

The project is built on the following principles:

- **Modularity:** The framework is highly extensible through a powerful plugin system. New capabilities can be added dynamically without recompiling the core components.
- **Security & Obfuscation:** Communication channels are designed to be covert. The framework includes features for obfuscating network traffic to evade detection.
- **Flexibility:** With a Go-based client and a Python-based server, PrometheanProxy offers a flexible and powerful combination of performance and ease of use.
- **Multi-Platform:** The framework supports agents on major platforms like Windows and Linux, with capabilities for Android as well.

## Key Features

- **Multi-Platform Client (Go):** High-performance, low-level agents for Windows, Linux, and Android.
- **Python 3 Server:** A central server that manages clients, handles data, and provides a user interface for operators.
- **Dynamic Plugin System:** Load new commands and features at runtime. Go-based plugins are delivered to clients on-demand.
- **Encrypted & Obfuscated Communication:** Network traffic is designed to blend in with normal traffic and avoid inspection.
- **Multi-User Support:** The `multiplayer` module allows multiple operators to collaborate.
- **RESTful API:** The server exposes an API for interaction and automation.
- **Database Backend:** The server uses a SQLite database to store information about beacons, sessions, and other operational data.
