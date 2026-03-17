"""
Foundry Service — Unified Azure AI Client & Agent Management

Centralizes authentication, client lifecycle, and agent operations for:
  - Azure OpenAI chat completions (Stage 2 discovery via gpt-4o-mini)
  - Azure AI Foundry Agent lifecycle (Stage 3 extraction via gpt-5.4-pro)

Single credential, lazy-initialized clients, full agent lifecycle.
"""

import io
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

AGENT_NAME = "schematic-iq-extractor"
AGENT_MODEL = "gpt-5.4-pro"
RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "rules")
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


def _load_agent_instructions():
    """Load agent instructions from the prompt file."""
    path = os.path.join(PROMPTS_DIR, "agent-instructions-extraction.md")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


class FoundryService:
    """Manages Azure OpenAI and Foundry Agent clients with shared credentials."""

    def __init__(self, console=None):
        self._credential = DefaultAzureCredential()
        self._openai_client = None
        self._project_client = None
        self._agent_openai_client = None
        self._console = console
        self._agent_name = None
        self._base_version = None

    # ── Chat Completion Client (Stage 2) ─────────────────────────────────

    def get_openai_client(self):
        """Return the Azure OpenAI client for chat completions (Stage 2)."""
        if self._openai_client is None:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise RuntimeError(
                    "AZURE_OPENAI_ENDPOINT not set. Add it to your .env file."
                )
            token_provider = get_bearer_token_provider(
                self._credential,
                "https://cognitiveservices.azure.com/.default",
            )
            self._openai_client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
                azure_endpoint=endpoint,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            )
        return self._openai_client

    # ── Foundry Project Client (Stage 3) ─────────────────────────────────

    def get_project_client(self):
        """Return the Foundry AIProjectClient for agent lifecycle (Stage 3)."""
        if self._project_client is None:
            endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
            if not endpoint:
                raise RuntimeError(
                    "AZURE_AI_PROJECT_ENDPOINT not set. Add it to your .env file.\n"
                    "Format: https://<account>.services.ai.azure.com/api/projects/<project>"
                )
            self._project_client = AIProjectClient(
                endpoint=endpoint,
                credential=self._credential,
            )
        return self._project_client

    def get_agent_openai_client(self):
        """Return the OpenAI client from the Foundry project (for file uploads and responses)."""
        if self._agent_openai_client is None:
            self._agent_openai_client = self.get_project_client().get_openai_client()
        return self._agent_openai_client

    # ── Agent Lifecycle ──────────────────────────────────────────────────

    def get_or_create_agent(self):
        """Find the agent by name or create it. Returns (agent_name, base_version)."""
        if self._agent_name and self._base_version:
            return self._agent_name, self._base_version

        console = self._console
        project_client = self.get_project_client()

        try:
            versions = project_client.agents.list_versions(agent_name=AGENT_NAME)
            version_list = list(versions)
            if version_list:
                latest = version_list[-1]
                if console:
                    console.print(
                        f"  [green]\u2714[/green] Found existing agent [bold]{AGENT_NAME}[/bold] "
                        f"v{latest.version}"
                    )
                self._agent_name = AGENT_NAME
                self._base_version = latest.version
                return self._agent_name, self._base_version
        except Exception:
            pass

        if console:
            console.print(f"  [yellow]\u26a0[/yellow] Agent not found, creating [bold]{AGENT_NAME}[/bold]...")

        rules_content = _load_rules()
        full_instructions = _load_agent_instructions()
        if rules_content:
            full_instructions += "\n\n## DOMAIN RULES\n" + rules_content

        definition = PromptAgentDefinition(
            model=AGENT_MODEL,
            instructions=full_instructions,
            tools=[
                {"type": "code_interpreter"},
            ],
        )

        version = project_client.agents.create_version(
            agent_name=AGENT_NAME,
            definition=definition,
        )
        if console:
            console.print(
                f"  [green]\u2714[/green] Created agent [bold]{AGENT_NAME}[/bold] "
                f"v{version.version} with {AGENT_MODEL}"
            )
        self._agent_name = AGENT_NAME
        self._base_version = version.version
        return self._agent_name, self._base_version

    def upload_file(self, name, data):
        """Upload a file to Code Interpreter. Returns file ID.

        Args:
            name: Filename string (or open file handle for binary).
            data: bytes, BytesIO, or open binary file handle.
        """
        client = self.get_agent_openai_client()
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        uploaded = client.files.create(purpose="assistants", file=(name, data))
        return uploaded.id

    def upload_file_handle(self, file_handle):
        """Upload a file handle directly (e.g. for images). Returns file ID."""
        client = self.get_agent_openai_client()
        uploaded = client.files.create(purpose="assistants", file=file_handle)
        return uploaded.id

    def upload_rule_files(self):
        """Upload all rule markdown files to Code Interpreter. Returns list of file IDs."""
        console = self._console
        rule_file_ids = []
        if not os.path.isdir(RULES_DIR):
            if console:
                console.print(f"  [dim]No rules directory found at {RULES_DIR}[/dim]")
            return rule_file_ids

        rule_files = sorted(f for f in os.listdir(RULES_DIR) if f.endswith(".md"))
        if not rule_files:
            return rule_file_ids

        client = self.get_agent_openai_client()
        for rule_file in rule_files:
            filepath = os.path.join(RULES_DIR, rule_file)
            with open(filepath, "rb") as f:
                uploaded = client.files.create(
                    purpose="assistants",
                    file=(f"rule_{rule_file}", f),
                )
            rule_file_ids.append(uploaded.id)

        if console:
            console.print(
                f"  [green]\u2714[/green] {len(rule_file_ids)} rule files uploaded "
                f"({', '.join(rule_files)})"
            )
        return rule_file_ids

    def create_temp_agent_version(self, uploaded_file_ids):
        """Create a temp agent version with uploaded files attached to Code Interpreter.

        Returns the temp version string.
        """
        console = self._console
        project_client = self.get_project_client()
        agent_name, base_version = self.get_or_create_agent()

        agent_entry = project_client.agents.get_version(
            agent_name=agent_name, agent_version=base_version
        )
        base_defn = agent_entry.definition
        base_model = base_defn["model"]
        base_tools = base_defn.get("tools", [])

        existing_ci_fids = []
        for tool in base_tools:
            if tool.get("type") == "code_interpreter":
                existing_ci_fids = tool.get("container", {}).get("file_ids", [])
                break

        new_fids = existing_ci_fids + uploaded_file_ids
        new_tools = []
        for tool in base_tools:
            if tool["type"] == "code_interpreter":
                new_tools.append({
                    "type": "code_interpreter",
                    "container": {"type": "auto", "file_ids": new_fids},
                })
            else:
                new_tools.append(tool)

        if not any(t["type"] == "code_interpreter" for t in new_tools):
            new_tools.append({
                "type": "code_interpreter",
                "container": {"type": "auto", "file_ids": uploaded_file_ids},
            })

        temp_defn = PromptAgentDefinition(
            model=base_model,
            instructions=base_defn.get("instructions", ""),
            tools=new_tools,
        )
        if console:
            console.print(f"  Creating temp agent version with {len(uploaded_file_ids)} uploaded files...")

        temp_ver = project_client.agents.create_version(
            agent_name=agent_name, definition=temp_defn
        )
        if console:
            console.print(
                f"  [green]\u2714[/green] Temp version {temp_ver.version} created "
                f"({len(new_fids)} CI files)"
            )
        return temp_ver.version

    def stream_agent_response(self, input_content, agent_version, timeout=900):
        """Create a streaming agent response. Returns the stream iterator."""
        agent_name, _ = self.get_or_create_agent()
        client = self.get_agent_openai_client()

        agent_ref = {
            "agent_reference": {
                "name": agent_name,
                "version": agent_version,
                "type": "agent_reference",
            }
        }

        return client.responses.create(
            input=[{"role": "user", "content": input_content}],
            extra_body=agent_ref,
            stream=True,
            timeout=timeout,
        )

    def follow_up_agent_response(self, previous_response_id, agent_version, prompt, timeout=300):
        """Send a follow-up (non-streaming) request to the agent. Returns response."""
        agent_name, _ = self.get_or_create_agent()
        client = self.get_agent_openai_client()

        agent_ref = {
            "agent_reference": {
                "name": agent_name,
                "version": agent_version,
                "type": "agent_reference",
            }
        }

        return client.responses.create(
            input=[{"role": "user", "content": prompt}],
            previous_response_id=previous_response_id,
            extra_body=agent_ref,
            timeout=timeout,
        )

    def cleanup_resources(self, temp_version, uploaded_file_ids):
        """Delete temp agent version and uploaded files."""
        console = self._console
        project_client = self.get_project_client()
        client = self.get_agent_openai_client()
        agent_name = self._agent_name or AGENT_NAME

        if temp_version is not None:
            try:
                project_client.agents.delete_version(
                    agent_name=agent_name, agent_version=temp_version
                )
                if console:
                    console.print(f"  [dim]Temp agent version {temp_version} deleted[/dim]")
            except Exception:
                pass

        for fid in uploaded_file_ids:
            try:
                client.files.delete(fid, timeout=30)
            except (Exception, KeyboardInterrupt):
                pass

        if uploaded_file_ids and console:
            console.print(f"  [dim]{len(uploaded_file_ids)} uploaded files cleaned up[/dim]")


def _load_rules():
    """Load all rule markdown files from the rules directory."""
    if not os.path.isdir(RULES_DIR):
        return ""
    rule_parts = []
    for rule_file in sorted(os.listdir(RULES_DIR)):
        if not rule_file.endswith(".md"):
            continue
        filepath = os.path.join(RULES_DIR, rule_file)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        rule_name = os.path.splitext(rule_file)[0].replace("_", " ").title()
        rule_parts.append(f"### {rule_name}\n{content}")
    return "\n\n".join(rule_parts)
