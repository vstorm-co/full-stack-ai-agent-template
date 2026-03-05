#!/usr/bin/env python
"""Post-generation hook for cookiecutter template."""

import os
import shutil
import subprocess
import sys

# Get cookiecutter variables
use_frontend = "{{ cookiecutter.use_frontend }}" == "True"
generate_env = "{{ cookiecutter.generate_env }}" == "True"
enable_i18n = "{{ cookiecutter.enable_i18n }}" == "True"

# Feature flags
use_database = "{{ cookiecutter.use_database }}" == "True"
use_postgresql = "{{ cookiecutter.use_postgresql }}" == "True"
use_sqlite = "{{ cookiecutter.use_sqlite }}" == "True"
use_mongodb = "{{ cookiecutter.use_mongodb }}" == "True"
use_sqlserver = "{{ cookiecutter.use_sqlserver }}" == "True"
use_sqlalchemy = "{{ cookiecutter.use_sqlalchemy }}" == "True"
use_sqlmodel = "{{ cookiecutter.use_sqlmodel }}" == "True"
include_example_crud = "{{ cookiecutter.include_example_crud }}" == "True"
enable_ai_agent = "{{ cookiecutter.enable_ai_agent }}" == "True"
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
enable_conversation_persistence = "{{ cookiecutter.enable_conversation_persistence }}" == "True"
enable_webhooks = "{{ cookiecutter.enable_webhooks }}" == "True"
enable_oauth = "{{ cookiecutter.enable_oauth }}" == "True"
use_jwt = "{{ cookiecutter.use_jwt }}" == "True"
use_api_key = "{{ cookiecutter.use_api_key }}" == "True"
use_celery = "{{ cookiecutter.use_celery }}" == "True"
use_taskiq = "{{ cookiecutter.use_taskiq }}" == "True"
use_arq = "{{ cookiecutter.use_arq }}" == "True"
use_github_actions = "{{ cookiecutter.use_github_actions }}" == "True"
use_gitlab_ci = "{{ cookiecutter.use_gitlab_ci }}" == "True"
enable_kubernetes = "{{ cookiecutter.enable_kubernetes }}" == "True"
use_nginx = "{{ cookiecutter.use_nginx }}" == "True"
enable_logfire = "{{ cookiecutter.enable_logfire }}" == "True"


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

# ============================================================================
# Cleanup stub files based on disabled features
# ============================================================================
print("Cleaning up unused files...")

# --- AI Agent files ---
if not enable_ai_agent:
    # Remove entire agents directory when AI is disabled
    remove_dir(os.path.join(backend_app, "agents"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "agent.py"))
else:
    # Remove framework-specific files based on selection
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

# --- Example CRUD files ---
if not include_example_crud or not use_database:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "items.py"))
    remove_file(os.path.join(backend_app, "db", "models", "item.py"))
    remove_file(os.path.join(backend_app, "repositories", "item.py"))
    remove_file(os.path.join(backend_app, "services", "item.py"))
    remove_file(os.path.join(backend_app, "schemas", "item.py"))

# --- Conversation persistence files ---
if not enable_conversation_persistence:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "conversations.py"))
    remove_file(os.path.join(backend_app, "db", "models", "conversation.py"))
    remove_file(os.path.join(backend_app, "repositories", "conversation.py"))
    remove_file(os.path.join(backend_app, "services", "conversation.py"))
    remove_file(os.path.join(backend_app, "schemas", "conversation.py"))

# --- Webhook files ---
if not enable_webhooks or not use_database:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "webhooks.py"))
    remove_file(os.path.join(backend_app, "db", "models", "webhook.py"))
    remove_file(os.path.join(backend_app, "repositories", "webhook.py"))
    remove_file(os.path.join(backend_app, "services", "webhook.py"))
    remove_file(os.path.join(backend_app, "schemas", "webhook.py"))

# --- Session management files ---
if not enable_session_management or not use_jwt:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "sessions.py"))
    remove_file(os.path.join(backend_app, "db", "models", "session.py"))
    remove_file(os.path.join(backend_app, "repositories", "session.py"))
    remove_file(os.path.join(backend_app, "services", "session.py"))
    remove_file(os.path.join(backend_app, "schemas", "session.py"))

# --- WebSocket files ---
if not enable_websockets:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "ws.py"))

# --- Admin panel (requires SQLAlchemy, not SQLModel) ---
if (
    not enable_admin_panel
    or (not use_postgresql and not use_sqlite and not use_sqlserver)
    or not use_sqlalchemy
):
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

# --- Security file (only when no auth at all) ---
if not use_jwt and not use_api_key:
    remove_file(os.path.join(backend_app, "core", "security.py"))

# --- Auth/User files (when JWT is disabled) ---
if not use_jwt:
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "auth.py"))
    remove_file(os.path.join(backend_app, "api", "routes", "v1", "users.py"))
    remove_file(os.path.join(backend_app, "db", "models", "user.py"))
    remove_file(os.path.join(backend_app, "repositories", "user.py"))
    remove_file(os.path.join(backend_app, "services", "user.py"))
    remove_file(os.path.join(backend_app, "schemas", "user.py"))
    remove_file(os.path.join(backend_app, "schemas", "token.py"))

# --- Logfire setup file (when logfire is disabled) ---
if not enable_logfire:
    remove_file(os.path.join(backend_app, "core", "logfire_setup.py"))

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
        remove_file(os.path.join(worker_dir, "tasks", "schedules.py"))
    if not use_taskiq:
        remove_file(os.path.join(worker_dir, "taskiq_app.py"))
        remove_file(os.path.join(worker_dir, "tasks", "taskiq_examples.py"))
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

# Handle i18n disabled: move files from [locale]/ to app root
if use_frontend and not enable_i18n:
    app_dir = os.path.join(os.getcwd(), "frontend", "src", "app")
    locale_dir = os.path.join(app_dir, "[locale]")

    if os.path.exists(locale_dir):
        # Move all contents from [locale]/ to app/
        for item in os.listdir(locale_dir):
            src = os.path.join(locale_dir, item)
            dst = os.path.join(app_dir, item)
            # Skip the layout.tsx from [locale] - we'll use the root layout
            if item == "layout.tsx":
                continue
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            shutil.move(src, dst)

        # Remove the now-empty [locale] directory
        shutil.rmtree(locale_dir)
        print("Moved routes from [locale]/ to app/ (i18n not enabled)")

        # Update root layout to include providers
        root_layout = os.path.join(app_dir, "layout.tsx")
        if os.path.exists(root_layout):
            with open(root_layout) as f:
                content = f.read()
            # Add Providers import and wrap children
            content = content.replace(
                'import "./globals.css";',
                'import "./globals.css";\nimport { Providers } from "./providers";',
            )
            content = content.replace(
                "<body className={inter.className}>{children}</body>",
                "<body className={inter.className}>\n        <Providers>{children}</Providers>\n      </body>",
            )
            with open(root_layout, "w") as f:
                f.write(content)

    # Remove middleware.ts
    middleware_file = os.path.join(os.getcwd(), "frontend", "src", "middleware.ts")
    if os.path.exists(middleware_file):
        os.remove(middleware_file)

    # Remove i18n related files
    i18n_file = os.path.join(os.getcwd(), "frontend", "src", "i18n.ts")
    if os.path.exists(i18n_file):
        os.remove(i18n_file)

    messages_dir = os.path.join(os.getcwd(), "frontend", "messages")
    if os.path.exists(messages_dir):
        shutil.rmtree(messages_dir)

    # Remove language-switcher component
    lang_switcher = os.path.join(
        os.getcwd(), "frontend", "src", "components", "language-switcher.tsx"
    )
    if os.path.exists(lang_switcher):
        os.remove(lang_switcher)

    print("Removed i18n files (i18n not enabled)")

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
        # Run ruff check --fix to auto-fix issues
        subprocess.run(
            [*ruff_cmd, "check", "--fix", "--quiet", backend_dir],
            check=False,
        )
        # Run ruff format for consistent formatting
        subprocess.run(
            [*ruff_cmd, "format", "--quiet", backend_dir],
            check=False,
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
