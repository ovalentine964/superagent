from setuptools import setup, find_packages

setup(
    name="superagent",
    version="0.1.0",
    description="SUPERAGENT — Merged AI agent system (OpenClaw + Hermes)",
    author="SUPERAGENT Team",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.115",
        "uvicorn[standard]>=0.34",
        "pydantic>=2.11",
        "pydantic-settings>=2.9",
        "python-dotenv>=1.1",
        "pyyaml>=6.0",
        "litellm>=1.72",
        "langgraph>=0.4",
        "langchain-core>=0.3",
        "sqlalchemy>=2.0",
        "aiosqlite>=0.21",
        "chromadb>=1.0",
        "redis>=6.2",
        "python-telegram-bot>=22",
        "httpx>=0.28",
        "apscheduler>=3.11",
        "numpy>=1.26",
        "tiktoken>=0.9",
        "structlog>=25.4",
    ],
    entry_points={
        "console_scripts": [
            "superagent=superagent.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
