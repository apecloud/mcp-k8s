import asyncio
import json
import httpx

MCP_VERSION = "1.8"

async def main():
    """Connects to the k8s-mcp-server and performs an MCP initialize handshake using raw httpx streaming."""
    mcp_url = "http://localhost:9096/mcp"
    client_id = "test-client-123"
    
    request_headers = {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-MCP-Client-ID': client_id,
        'X-MCP-Version': MCP_VERSION,
    }

    try:
        async with httpx.AsyncClient(headers=request_headers, timeout=30) as client:
            print(f"Connecting to MCP server at {mcp_url}...")
            
            async with client.stream("POST", mcp_url) as response:
                print("Connection established. Raw response headers:")
                for key, value in response.headers.items():
                    print(f"  {key}: {value}")

                if response.status_code != 200:
                    print(f"❌ Server returned status {response.status_code}")
                    return

                print("\n<-- Waiting for server raw stream...")
                buffer = ""
                async for chunk in response.aiter_raw():
                    buffer += chunk.decode('utf-8')
                    # Process buffer line-by-line
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        if line:
                            print(f"<-- Received raw line: {line}")
                            if line.startswith("data:"):
                                try:
                                    data_str = line[len("data:"):].strip()
                                    data = json.loads(data_str)
                                    print(f"<-- Parsed message:\n{json.dumps(data, indent=2)}")
                                    
                                    if data.get("id") == 1 and "result" in data:
                                        print("\n✅ MCP Handshake Successful!")
                                        print("Server capabilities:", data["result"].get("capabilities"))
                                        # Test successful, we can exit
                                        return 
                                except json.JSONDecodeError:
                                    print(f"<-- Received non-JSON data payload: {data_str}")
                
                print("\nStream finished.")

    except httpx.ConnectError as e:
        print(f"❌ Connection failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 