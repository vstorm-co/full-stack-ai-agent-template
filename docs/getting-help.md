# Getting Help

## Documentation

- [Installation](installation.md) - Setup guide
- [Quick Start](guides/quick-start.md) - First project walkthrough
- [Architecture](architecture.md) - Project structure and patterns
- [AI Agents](ai-agent.md) - AI framework configuration
- [Deployment](deployment.md) - Production deployment guides

## GitHub

- [Issues](https://github.com/vstorm-co/full-stack-ai-agent-template/issues) - Report bugs or request features
- [Discussions](https://github.com/vstorm-co/full-stack-ai-agent-template/discussions) - Ask questions and share ideas
- [Pull Requests](https://github.com/vstorm-co/full-stack-ai-agent-template/pulls) - Contribute to the project

## FAQ

### Which AI framework should I choose?

| Use Case | Recommended |
|----------|-------------|
| Type-safe agents with Pydantic | **PydanticAI** |
| Complex workflows and chains | **LangChain** |
| Stateful agent workflows | **LangGraph** |

### Which database should I use?

The template uses **PostgreSQL** (async, SQLAlchemy 2.0 + Alembic) as its single supported database — it covers relational data, complex queries, and doubles as a `pgvector` RAG store. Pass `--database none` only for a stateless service that needs no auth, RAG, or teams.

### How do I add authentication?

Choose during project generation:

```bash
fastapi-fullstack create my_app --auth jwt     # JWT tokens
fastapi-fullstack create my_app --auth api_key # API keys
fastapi-fullstack create my_app --auth both    # Both methods
```

### How do I deploy to production?

Generated projects include:

- `Dockerfile` for containerization
- `docker-compose.yml` for local development
- Optional Kubernetes manifests
- GitHub Actions / GitLab CI pipelines

See [Deployment Guide](deployment.md) for details.

## Related Projects

- [pydantic-deep](https://github.com/vstorm-co/pydantic-deepagents) - Deep agent framework with planning and subagents
- [pydantic-ai](https://github.com/pydantic/pydantic-ai) - The foundation for PydanticAI agents
- [FastAPI](https://fastapi.tiangolo.com/) - The web framework powering the backend
