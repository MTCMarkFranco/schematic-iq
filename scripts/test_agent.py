"""Minimal test of Foundry Agent call."""
import os, json, io, base64, time, sys
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
load_dotenv()

endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
agent_name = "schematic-iq-extractor"
base_version = "3"

pc = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
oc = pc.get_openai_client()
print("Client ready", flush=True)

# Upload a small test file
test_data = json.dumps({"test": True}).encode()
tf = oc.files.create(purpose="assistants", file=("test.json", io.BytesIO(test_data)))
print(f"Uploaded: {tf.id}", flush=True)

# Get base version config
v = pc.agents.get_version(agent_name=agent_name, agent_version=base_version)
d = v.definition
base_tools = d.get("tools", [])
existing_fids = []
for t in base_tools:
    if t.get("type") == "code_interpreter":
        existing_fids = t.get("container", {}).get("file_ids", [])
        break
print(f"Base CI files: {len(existing_fids)}", flush=True)

# Create temp version
new_fids = existing_fids + [tf.id]
new_tools = []
for t in base_tools:
    if t["type"] == "code_interpreter":
        new_tools.append({"type": "code_interpreter", "container": {"type": "auto", "file_ids": new_fids}})
    else:
        new_tools.append(t)

temp_defn = PromptAgentDefinition(model=d["model"], instructions=d.get("instructions", ""), tools=new_tools)
tv = pc.agents.create_version(agent_name=agent_name, definition=temp_defn)
print(f"Temp version: {tv.version}", flush=True)

# Call agent with minimal message
agent_ref = {"agent_reference": {"name": agent_name, "version": tv.version, "type": "agent_reference"}}
print("Calling agent (minimal test)...", flush=True)
t0 = time.time()
try:
    resp = oc.responses.create(
        input=[{"role": "user", "content": [{"type": "input_text", "text": "List all files in /mnt/data/ with their sizes. Use code interpreter."}]}],
        extra_body=agent_ref,
        timeout=300,
    )
    dt = time.time() - t0
    ot = resp.output_text or ""
    print(f"Response in {dt:.1f}s", flush=True)
    print(f"Output text length: {len(ot)}", flush=True)
    print(f"Output text preview: {ot[:500]}", flush=True)
except Exception as e:
    dt = time.time() - t0
    print(f"ERROR after {dt:.1f}s: {type(e).__name__}: {e}", flush=True)
finally:
    try:
        pc.agents.delete_version(agent_name=agent_name, agent_version=tv.version)
    except Exception:
        pass
    try:
        oc.files.delete(tf.id)
    except Exception:
        pass
    print("Cleaned up", flush=True)
