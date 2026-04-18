#!/usr/bin/env python
"""Post-generation hook for cookiecutter template."""

import os
import shutil
import subprocess
import sys

# Get cookiecutter variables
use_frontend = "{{ cookiecutter.use_frontend }}" == "True"
generate_env = "{{ cookiecutter.generate_env }}" == "True"

# Feature flags
use_database = "{{ cookiecutter.use_database }}" == "True"
use_postgresql = "{{ cookiecutter.use_postgresql }}" == "True"
use_sqlite = "{{ cookiecutter.use_sqlite }}" == "True"
use_mongodb = "{{ cookiecutter.use_mongodb }}" == "True"
use_sqlalchemy = "{{ cookiecutter.use_sqlalchemy }}" == "True"
use_sqlmodel = "{{ cookiecutter.use_sqlmodel }}" == "True"
use_pydantic_ai = "{{ cookiecutter.use_pydantic_ai }}" == "True"
use_langchain = "{{ cookiecutter.use_langchain }}" == "True"
use_langgraph = "{{ cookiecutter.use_langgraph }}" == "True"
use_crewai = "{{ cookiecutter.use_crewai }}" == "True"
use_deepagents = "{{ cookiecutter.use_deepagents }}" == "True"
enable_admin_panel = "{{ cookiecutter.enable_admin_panel }}" == "True"
enable_websockets = "{{ cookiecutter.enable_websockets }}" == "True"
enable_redis = "{{ cookiecutter.enable_redis }}" == "True"
enable_caching = "{{ cookiecutter.enable_caching }}" == "True"
enable_rate_limiting = "{{ cookiecutter.enable_rate_limiting }}" == "True"
enable_session_management = "{{ cookiecutter.enable_session_management }}" == "True"
enable_webhooks = "{{ cookiecutter.enable_webhooks }}" == "True"
enable_oauth = "{{ cookiecutter.enable_oauth }}" == "True"
use_celery = "{{ cookiecutter.use_celery }}" == "True"
use_taskiq = "{{ cookiecutter.use_taskiq }}" == "True"
use_arq = "{{ cookiecutter.use_arq }}" == "True"
use_github_actions = "{{ cookiecutter.use_github_actions }}" == "True"
use_gitlab_ci = "{{ cookiecutter.use_gitlab_ci }}" == "True"
enable_kubernetes = "{{ cookiecutter.enable_kubernetes }}" == "True"
use_nginx = "{{ cookiecutter.use_nginx }}" == "True"
enable_logfire = "{{ cookiecutter.enable_logfire }}" == "True"
enable_langsmith = "{{ cookiecutter.enable_langsmith }}" == "True"
enable_rag = "{{ cookiecutter.enable_rag }}" == "True"
enable_rag_image_description = "{{ cookiecutter.enable_rag_image_description }}" == "True"
enable_google_drive_ingestion = "{{ cookiecutter.enable_google_drive_ingestion }}" == "True"
enable_s3_ingestion = "{{ cookiecutter.enable_s3_ingestion }}" == "True"
enable_web_search = "{{ cookiecutter.enable_web_search }}" == "True"
use_pydantic_deep = "{{ cookiecutter.use_pydantic_deep }}" == "True"
use_telegram = "{{ cookiecutter.use_telegram }}" == "True"
use_slack = "{{ cookiecutter.use_slack }}" == "True"


def remove_file(path: str) -> None:
    """Remove a file if it exists."""
    if os.path.exists(path):
        os.remove(path)
        print(f"  Removed: {os.path.relpath(path)}")


def is_stub_file(filepath: str) -> bool:
    """Check if file only contains a docstring stub with no real code."""
    if not os.path.exists(filepath):
        return False
    with open(filepath) as f:
        content = f.read().strip()
    # Empty file
    if not content:
        return True
    # File only has docstring (triple-quoted string)
    if content.startswith('"""') and content.endswith('"""'):
        # Check if there's only one docstring and no code
        inner = content[3:-3].strip()
        return '"""' not in inner and "def " not in content and "class " not in content
    return False


def remove_dir(path: str) -> None:
    """Remove a directory if it exists."""
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"  Removed: {os.path.relpath(path)}/")


# Base directories
backend_app = os.path.join(os.getcwd(), "backend", "app")

# Cleanup stub files based on disabled features
print("Cleaning up unused files...")

# --- AI Agent files (remove unused framework-specific files) ---
if not use_pydantic_ai:
    remove_file(os.path.join(backend_app, "agents", "assistant.py"))
if not use_langchain:
    remove_file(os.path.join(backend_app, "agents", "langchain_assistant.py"))
if not use_langgraph:
    remove_file(os.path.join(backend_app, "agents", "langgraph_assistant.py"))
if not use_crewai:
    remove_file(os.path.join(backend_app, "agents", "crewai_assistant.py"))
if not use_deepagents:
    remove_file(os.path.join(backend_app, "agents", "deepagents_assistant.py"))
if not use_pydantic_deep:
    remove_file(os.path.join(backend_app, "agents", "pydantic_deep_assistant.py"))
if not enable_web_search:
    remove_file(os.path.join(backend_app, "agents", "tools", "web_search.py"))

# --- Webhook files ---
if not enable_webhooks or not use_database:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "webhooks.py"))
    remove_file(os.path.join(backend_app, "db", "models", "webhook.py"))
    remove_file(os.path.join(backend_app, "repositories", "webhook.py"))
    remove_file(os.path.join(backend_app, "services", "webhook.py"))
    remove_file(os.path.join(backend_app, "schemas", "webhook.py"))

# --- Session management files ---
if not enable_session_management:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "sessions.py"))
    remove_file(os.path.join(backend_app, "db", "models", "session.py"))
    remove_file(os.path.join(backend_app, "repositories", "session.py"))
    remove_file(os.path.join(backend_app, "services", "session.py"))
    remove_file(os.path.join(backend_app, "schemas", "session.py"))


# --- Admin panel (requires SQLAlchemy, not SQLModel) ---
if not enable_admin_panel or (not use_postgresql and not use_sqlite) or not use_sqlalchemy:
    remove_file(os.path.join(backend_app, "admin.py"))

# --- Redis/Cache files ---
if not enable_redis:
    remove_file(os.path.join(backend_app, "clients", "redis.py"))

if not enable_caching:
    remove_file(os.path.join(backend_app, "core", "cache.py"))

# --- Rate limiting ---
if not enable_rate_limiting:
    remove_file(os.path.join(backend_app, "core", "rate_limit.py"))

# --- OAuth ---
if not enable_oauth:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "oauth.py"))
    remove_file(os.path.join(backend_app, "core", "oauth.py"))


# --- Logfire setup file (when logfire is disabled) ---
if not enable_logfire:
    remove_file(os.path.join(backend_app, "core", "logfire_setup.py"))

# --- RAG files ---
if not enable_rag:
    # Remove entire rag directory when RAG is disabled
    remove_dir(os.path.join(backend_app, "rag"))
    # Remove RAG-related API route
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "rag.py"))
    # Remove RAG schema
    remove_file(os.path.join(backend_app, "schemas", "rag.py"))
    # Remove RAG commands
    remove_file(os.path.join(backend_app, "commands", "rag.py"))
    # Remove RAG worker tasks
    remove_file(os.path.join(backend_app, "worker", "tasks", "rag_ingestion.py"))
    # Remove RAG agent tool
    remove_file(os.path.join(backend_app, "agents", "tools", "rag_tool.py"))
    # Remove frontend RAG files
    if use_frontend:
        frontend_src = os.path.join(os.getcwd(), "frontend", "src")
        remove_file(os.path.join(frontend_src, "lib", "rag-api.ts"))
        remove_dir(os.path.join(frontend_src, "app", "api", "v1", "rag"))
        # Remove RAG management page (both paths - i18n variant may be moved later)
        remove_dir(os.path.join(frontend_src, "app", "[locale]", "(dashboard)", "rag"))
        remove_dir(os.path.join(frontend_src, "app", "(dashboard)", "rag"))
else:
    # RAG enabled — remove optional components if not enabled
    if not enable_rag_image_description:
        remove_file(os.path.join(backend_app, "rag", "image_describer.py"))
    if not enable_google_drive_ingestion:
        remove_file(os.path.join(backend_app, "rag", "sources", "google_drive.py"))
        remove_file(os.path.join(backend_app, "rag", "connectors", "google_drive.py"))
    if not enable_s3_ingestion:
        remove_file(os.path.join(backend_app, "rag", "sources", "s3.py"))
        remove_file(os.path.join(backend_app, "rag", "connectors", "s3.py"))
    if not enable_google_drive_ingestion and not enable_s3_ingestion:
        remove_dir(os.path.join(backend_app, "rag", "sources"))
        remove_dir(os.path.join(backend_app, "rag", "connectors"))

# --- Cleanup stub files (files with only docstring, no code) ---
core_dir = os.path.join(backend_app, "core")
for stub_candidate in ["security.py", "cache.py", "rate_limit.py", "oauth.py", "logfire_setup.py", "csrf.py"]:
    filepath = os.path.join(core_dir, stub_candidate)
    if is_stub_file(filepath):
        remove_file(filepath)
        print(f"  Removed stub: {os.path.relpath(filepath)}")

# --- Worker/Background tasks ---
use_any_background_tasks = use_celery or use_taskiq or use_arq
if not use_any_background_tasks:
    remove_dir(os.path.join(backend_app, "worker"))
else:
    # Remove specific worker files based on selection
    worker_dir = os.path.join(backend_app, "worker")
    if not use_celery:
        remove_file(os.path.join(worker_dir, "celery_app.py"))
        remove_file(os.path.join(worker_dir, "tasks", "examples.py"))
    if not use_taskiq:
        remove_file(os.path.join(worker_dir, "taskiq_app.py"))
        remove_file(os.path.join(worker_dir, "tasks", "taskiq_examples.py"))
        remove_file(os.path.join(worker_dir, "tasks", "schedules.py"))
    if not use_arq:
        remove_file(os.path.join(worker_dir, "arq_app.py"))


# --- Cleanup empty directories ---
def remove_empty_dirs(path: str) -> None:
    """Recursively remove empty directories."""
    if not os.path.isdir(path):
        return
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            remove_empty_dirs(item_path)
    # Check if directory is now empty (except __init__.py)
    remaining = os.listdir(path)
    if not remaining:
        os.rmdir(path)
        print(f"  Removed empty: {os.path.relpath(path)}/")
    elif remaining == ["__init__.py"]:
        # Directory only has __init__.py - remove it
        os.remove(os.path.join(path, "__init__.py"))
        os.rmdir(path)
        print(f"  Removed empty: {os.path.relpath(path)}/")


# Clean up empty directories in key locations
for subdir in ["clients", "agents", "worker", "worker/tasks"]:
    dir_path = os.path.join(backend_app, subdir)
    if os.path.exists(dir_path):
        remove_empty_dirs(dir_path)

print("File cleanup complete.")

# --- CI/CD files cleanup ---
if not use_github_actions:
    github_dir = os.path.join(os.getcwd(), ".github")
    if os.path.exists(github_dir):
        shutil.rmtree(github_dir)
        print("Removed .github/ directory (GitHub Actions not enabled)")

if not use_gitlab_ci:
    gitlab_ci_file = os.path.join(os.getcwd(), ".gitlab-ci.yml")
    if os.path.exists(gitlab_ci_file):
        os.remove(gitlab_ci_file)
        print("Removed .gitlab-ci.yml (GitLab CI not enabled)")

if not enable_kubernetes:
    kubernetes_dir = os.path.join(os.getcwd(), "kubernetes")
    if os.path.exists(kubernetes_dir):
        shutil.rmtree(kubernetes_dir)
        print("Removed kubernetes/ directory (Kubernetes not enabled)")

if not use_nginx:
    nginx_dir = os.path.join(os.getcwd(), "nginx")
    if os.path.exists(nginx_dir):
        shutil.rmtree(nginx_dir)
        print("Removed nginx/ directory (Nginx not enabled)")

# Remove frontend folder if not using frontend
if not use_frontend:
    frontend_dir = os.path.join(os.getcwd(), "frontend")
    if os.path.exists(frontend_dir):
        shutil.rmtree(frontend_dir)
        print("Removed frontend/ directory (frontend not enabled)")
    # Remove frontend-specific Claude rule
    remove_file(os.path.join(os.getcwd(), ".claude", "rules", "frontend.md"))


# Remove .env files if generate_env is false
if not generate_env:
    backend_env = os.path.join(os.getcwd(), "backend", ".env")
    if os.path.exists(backend_env):
        os.remove(backend_env)
        print("Removed backend/.env (generate_env disabled)")

    frontend_env = os.path.join(os.getcwd(), "frontend", ".env.local")
    if os.path.exists(frontend_env):
        os.remove(frontend_env)
        print("Removed frontend/.env.local (generate_env disabled)")
else:
    # Generate frontend/.env.local with necessary Next.js public variables
    if use_frontend:
        frontend_env_local = os.path.join(os.getcwd(), "frontend", ".env.local")
        if not os.path.exists(frontend_env_local):
            env_lines = [
                "# Backend API URL (server-side only - not exposed to browser)",
                "BACKEND_URL=http://localhost:{{ cookiecutter.backend_port }}",
                "",
                "# WebSocket URL for real-time features",
                "BACKEND_WS_URL=ws://localhost:{{ cookiecutter.backend_port }}",
            ]
            env_lines.extend([
                "",
                "# Authentication (always enabled)",
                "NEXT_PUBLIC_AUTH_ENABLED=true",
            ])
            if enable_oauth:
                env_lines.extend([
                    "",
                    "# Public API URL for OAuth redirects (exposed to browser)",
                    "NEXT_PUBLIC_API_URL=http://localhost:{{ cookiecutter.backend_port }}",
                ])
            if enable_rag:
                env_lines.extend([
                    "",
                    "# RAG (Retrieval Augmented Generation)",
                    "NEXT_PUBLIC_RAG_ENABLED=true",
                ])
            if enable_logfire:
                env_lines.extend([
                    "",
                    "# Logfire/OpenTelemetry (server-side instrumentation)",
                    "# Get your write token from: https://logfire.pydantic.dev",
                    "OTEL_EXPORTER_OTLP_ENDPOINT=https://logfire-api.pydantic.dev",
                    "OTEL_EXPORTER_OTLP_HEADERS=Authorization=your-logfire-write-token",
                ])

            with open(frontend_env_local, "w") as f:
                f.write("\n".join(env_lines) + "\n")
            print("Generated frontend/.env.local")

# Generate uv.lock for backend (required for Docker builds)
backend_dir = os.path.join(os.getcwd(), "backend")
if os.path.exists(backend_dir):
    uv_cmd = shutil.which("uv")
    if uv_cmd:
        print("Generating uv.lock for backend...")
        result = subprocess.run(
            [uv_cmd, "lock"],
            cwd=backend_dir,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            print("uv.lock generated successfully.")
        else:
            print("Warning: Failed to generate uv.lock. Run 'uv lock' in backend/ directory.")
    else:
        print("Warning: uv not found. Run 'uv lock' in backend/ to generate lock file.")

# Run ruff to auto-fix import sorting and other linting issues
if os.path.exists(backend_dir):
    ruff_cmd = None

    # Try multiple methods to find/run ruff
    # 1. Check if ruff is in PATH
    ruff_path = shutil.which("ruff")
    if ruff_path:
        ruff_cmd = [ruff_path]
    # 2. Try uvx ruff (if uv is installed)
    elif shutil.which("uvx"):
        ruff_cmd = ["uvx", "ruff"]
    # 3. Try python -m ruff
    else:
        # Test if ruff is available as a module
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            ruff_cmd = [sys.executable, "-m", "ruff"]

    if ruff_cmd:
        print(f"Running ruff to format code (using: {' '.join(ruff_cmd)})...")
        # Run ruff check --fix to auto-fix issues (suppress output)
        subprocess.run(
            [*ruff_cmd, "check", "--fix", "--quiet", backend_dir],
            check=False,
            capture_output=True,
        )
        # Run ruff format for consistent formatting (suppress output)
        subprocess.run(
            [*ruff_cmd, "format", "--quiet", backend_dir],
            check=False,
            capture_output=True,
        )
        print("Code formatting complete.")
    else:
        print("Warning: ruff not found. Run 'ruff format .' in backend/ to format code.")

# Format frontend with prettier if it exists
frontend_dir = os.path.join(os.getcwd(), "frontend")
if use_frontend and os.path.exists(frontend_dir):
    # Try to find bun or npx for running prettier
    bun_cmd = shutil.which("bun")
    npx_cmd = shutil.which("npx")

    if bun_cmd:
        print("Installing frontend dependencies and formatting with Prettier...")
        # Install dependencies first (prettier is a devDependency)
        result = subprocess.run(
            [bun_cmd, "install"],
            cwd=frontend_dir,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            # Format with prettier
            subprocess.run(
                [bun_cmd, "run", "format"],
                cwd=frontend_dir,
                capture_output=True,
                check=False,
            )
            print("Frontend formatting complete.")
        else:
            print("Warning: Failed to install frontend dependencies.")
    elif npx_cmd:
        print("Formatting frontend with Prettier...")
        subprocess.run(
            [npx_cmd, "prettier", "--write", "."],
            cwd=frontend_dir,
            capture_output=True,
            check=False,
        )
        print("Frontend formatting complete.")
    else:
        print("Warning: bun/npx not found. Run 'bun run format' in frontend/ to format code.")

print("Project generated successfully!")
