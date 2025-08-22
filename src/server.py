from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.middleware.cors import CORSMiddleware
from constants.schema import *
from starlette.applications import Starlette
from event_store import InMemoryEventStore
from starlette.middleware import Middleware
from constants.enum import Tools
from helper.config import HOST, PORT, SLIDESPEAK_API_KEY
from helper.logger import logging
from starlette.routing import Route
from services.slidespeak_provider import *
from mcp.server import Server
import mcp.types as types
import contextlib
import uvicorn
import asyncio
import json

server = Server("slidespeak-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        # SlideSpeak tools
        types.Tool(
            name=Tools.GET_AVAILABLE_TEMPLATES,
            description="Get all available presentation templates from SlideSpeak",
            inputSchema=GetAvailableTemplates.model_json_schema(),
        ),
        types.Tool(
            name=Tools.GENERATE_POWERPOINT,
            description="Generate a PowerPoint presentation based on text, length, and template using SlideSpeak",
            inputSchema=GeneratePowerpoint.model_json_schema(),
        ),
        types.Tool(
            name=Tools.GENERATE_POWERPOINT_SLIDE_BY_SLIDE,
            description="Generate a PowerPoint presentation slide by slide based on slides array and template using SlideSpeak",
            inputSchema=GeneratePowerpointSlideBySlide.model_json_schema(),
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> types.CallToolResult:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    try:
        match name:
            # SlideSpeak tools
            case Tools.GET_AVAILABLE_TEMPLATES:
                result = await get_available_templates(
                    limit=arguments.get("limit") if arguments else None
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            case Tools.GENERATE_POWERPOINT:
                result = await generate_powerpoint(
                    plain_text=arguments.get("plain_text"),
                    length=arguments.get("length"),
                    template=arguments.get("template")
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            case Tools.GENERATE_POWERPOINT_SLIDE_BY_SLIDE:
                result = await generate_powerpoint_slide_by_slide(
                    slides=arguments.get("slides", []),
                    template=arguments.get("template")
                )
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            case _:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as error:
        print("Error:", error)
        error = {"message": f"Error: {str(error)}", "is_error": True}
        return [types.TextContent(type="text", text=json.dumps(error, indent=2))]


async def create_app():

    # Create an event store for resumability
    event_store = InMemoryEventStore(max_events_per_stream=100)

    # Create the session manager with the event store
    try:
        # Try with auth parameters (newer MCP versions)
        session_manager = StreamableHTTPSessionManager(
            app=server,
            event_store=event_store,  # Use our event store for resumability
            json_response=False,  # Use SSE format for responses
            stateless=False,  # Stateful mode for better user experience
        )
        logging.info(
            "StreamableHTTPSessionManager initialized with authentication support"
        )
    except TypeError:
        # Fallback for older MCP versions that don't support auth
        logging.warning(
            "Your MCP version doesn't support authentication in StreamableHTTPSessionManager"
        )
        logging.warning(
            "Initializing StreamableHTTPSessionManager without authentication"
        )

        # Try with just the basic parameters
        try:
            session_manager = StreamableHTTPSessionManager(
                app=server,
                event_store=event_store,
                json_response=False,
            )
            logging.info(
                "StreamableHTTPSessionManager initialized without authentication"
            )
        except TypeError:
            # If that still fails, try with minimal parameters
            logging.warning(
                "Falling back to minimal StreamableHTTPSessionManager initialization"
            )
            session_manager = StreamableHTTPSessionManager(app=server)
    except Exception as e:
        logging.error(f"Failed to initialize StreamableHTTPSessionManager: {e}")
        session_manager = None


    # Create a class for handling streamable HTTP connections
    class HandleStreamableHttp:
        def __init__(self, session_manager):
            self.session_manager = session_manager

        async def __call__(self, scope, receive, send):
            if self.session_manager is not None:
                try:
                    logging.info("Handling Streamable HTTP connection ....")
                    await self.session_manager.handle_request(scope, receive, send)
                    logging.info("Streamable HTTP connection closed ....")
                except Exception as e:
                    logging.error(f"Error handling Streamable HTTP request: {e}")
                    await send({
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [(b"content-type", b"application/json")],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": json.dumps({
                            "error": f"Internal server error: {str(e)}"
                        }).encode("utf-8"),
                    })
            else:
                # Return a 501 Not Implemented response if streamable HTTP is not available
                await send(
                    {
                        "type": "http.response.start",
                        "status": 501,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": json.dumps(
                            {"error": "Streamable HTTP transport is not available"}
                        ).encode("utf-8"),
                    }
                )

    
    # Helper functions for OAuth handlers
    async def get_request_body(receive):
        """Get request body from ASGI receive function."""
        body = b""
        more_body = True

        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        return body.decode("utf-8")

    async def send_json_response(send, status, data):
        """Send JSON response."""
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps(data).encode("utf-8"),
            }
        )

    # Define routes
    routes = []

    # Add Streamable HTTP route if available
    if session_manager is not None:
        routes.append(
            Route(
                "/mcp", endpoint=HandleStreamableHttp(session_manager), methods=["POST"]
            )
        )

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]

    # Define lifespan for session manager
    @contextlib.asynccontextmanager
    async def lifespan(app):
        """Context manager for session manager."""
        if session_manager is not None:
            async with session_manager.run():
                logging.info("Application started with StreamableHTTP session manager!")
                try:
                    yield
                finally:
                    logging.info("Application shutting down...")
        else:
            # No session manager, just yield
            yield

    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


async def start_server():
    """Start the server asynchronously."""
    app = await create_app()
    logging.info(f"Starting server at {HOST}:{PORT}")

    # Use uvicorn's async API
    config = uvicorn.Config(app, host=HOST, port=PORT)
    server = uvicorn.Server(config)
    await server.serve()



if __name__ == "__main__":
    while True:
        try:
            # Use asyncio.run to run the async start_server function
            asyncio.run(start_server())
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
            break
        except Exception as e:
            logging.error(f"Server crashed with error: {e}")
            continue
