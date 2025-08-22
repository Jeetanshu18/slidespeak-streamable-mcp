#!/usr/bin/env python3
"""
Comprehensive test client for SlideSpeak MCP Server.
Tests all available tools with proper authentication.
"""

import asyncio
import json
import os
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession

# Sample test data for SlideSpeak
TEST_PLAIN_TEXT = "Create a presentation about artificial intelligence and machine learning. Cover the basics of AI, different types of machine learning, current applications, and future trends in the field."
TEST_LENGTH = 5  # Number of slides
TEST_TEMPLATE = "business"  # Default template to use

# Sample slide-by-slide data
TEST_SLIDES = [
    {
        "title": "Introduction to AI",
        "content_description": "Artificial Intelligence is transforming the world around us with innovative solutions and applications.",
        "layout": "items",
        "item_amount": "1",
    },
    {
        "title": "Machine Learning Basics",
        "content_description": "Machine learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed.",
        "layout": "items",
        "item_amount": "2",
    },
    {
        "title": "Types of ML",
        "content_description": "Supervised learning, unsupervised learning, and reinforcement learning are the three main types of machine learning.",
        "layout": "items",
        "item_amount": "3",
    },
    {
        "title": "Current Applications",
        "content_description": "AI is used in healthcare, finance, transportation, entertainment, and many other industries today.",
        "layout": "items",
        "item_amount": "4",
    },
    {
        "title": "Future Trends",
        "content_description": "The future of AI includes advances in natural language processing, computer vision, and autonomous systems.",
        "layout": "items",
        "item_amount": "5",
    }
]

# Global variables to store test results
available_templates = []
selected_template = None

async def test_server_connectivity(session):
    """Test basic server connectivity and list available tools."""
    print("\n" + "="*50)
    print("🔧 Testing SERVER_CONNECTIVITY")
    print("="*50)
    
    try:
        # Get list of available tools
        tools = await session.list_tools()
        available_tools = [tool.name for tool in tools.tools]
        expected_tools = ["get_available_templates", "generate_powerpoint", "generate_powerpoint_slide_by_slide"]
        
        print(f"✅ Server connectivity successful")
        print(f"📚 Available tools: {available_tools}")
        
        # Check if all expected tools are available
        missing_tools = [tool for tool in expected_tools if tool not in available_tools]
        if missing_tools:
            print(f"⚠️  Missing expected tools: {missing_tools}")
            return False
        else:
            print(f"✅ All expected tools are available")
            return True
            
    except Exception as e:
        print(f"❌ Server connectivity failed: {e}")
        return False

async def test_get_available_templates(session):
    """Test the get_available_templates tool."""
    print("\n" + "="*50)
    print("📋 Testing GET_AVAILABLE_TEMPLATES")
    print("="*50)
    
    try:
        # Test 1: Get all templates (no limit)
        print("🔸 Test 1: Getting all available templates")
        result = await session.call_tool(
            "get_available_templates",
            arguments={}
        )
        print("✅ get_available_templates (no limit) successful")
        response_data = json.loads(result.content[0].text)
        print("Response:", json.dumps(response_data, indent=2))
        
        # Test 2: Get limited templates
        print("\n🔸 Test 2: Getting limited templates (limit=3)")
        result_limited = await session.call_tool(
            "get_available_templates",
            arguments={"limit": 3}
        )
        print("✅ get_available_templates (with limit) successful")
        response_data_limited = json.loads(result_limited.content[0].text)
        print("Response:", json.dumps(response_data_limited, indent=2))
        
        # Test 3: Test with limit=1 for minimal response
        print("\n🔸 Test 3: Getting single template (limit=1)")
        result_single = await session.call_tool(
            "get_available_templates",
            arguments={"limit": 1}
        )
        print("✅ get_available_templates (limit=1) successful")
        response_data_single = json.loads(result_single.content[0].text)
        print("Response:", json.dumps(response_data_single, indent=2))
        
        # Store templates for other tests (use the full list)
        global available_templates, selected_template
        if response_data.get("success") and "templates" in response_data:
            available_templates = response_data["templates"]
            # Select the first available template or use default
            if available_templates:
                selected_template = available_templates[0]
                print(f"📄 Selected template for testing: {selected_template}")
            else:
                selected_template = TEST_TEMPLATE
                print(f"📄 Using default template: {selected_template}")
        else:
            selected_template = TEST_TEMPLATE
            print(f"📄 Using default template: {selected_template}")
        
        return True
    except Exception as e:
        print(f"❌ get_available_templates failed: {e}")
        return False

async def test_generate_powerpoint(session):
    """Test the generate_powerpoint tool."""
    print("\n" + "="*50)
    print("📊 Testing GENERATE_POWERPOINT")
    print("="*50)
    
    if not selected_template:
        print("⚠️  No template available, using default")
        template_to_use = TEST_TEMPLATE
    else:
        template_to_use = selected_template
    
    try:
        result = await session.call_tool(
            "generate_powerpoint",
            arguments={
                "plain_text": TEST_PLAIN_TEXT,
                "length": TEST_LENGTH,
                "template": template_to_use
            }
        )
        print("✅ generate_powerpoint successful")
        response_data = json.loads(result.content[0].text)
        print("Response:", json.dumps(response_data, indent=2))
        return True
    except Exception as e:
        print(f"❌ generate_powerpoint failed: {e}")
        return False

async def test_generate_powerpoint_slide_by_slide(session):
    """Test the generate_powerpoint_slide_by_slide tool."""
    print("\n" + "="*50)
    print("📖 Testing GENERATE_POWERPOINT_SLIDE_BY_SLIDE")
    print("="*50)
    
    if not selected_template:
        print("⚠️  No template available, using default")
        template_to_use = TEST_TEMPLATE
    else:
        template_to_use = selected_template
    
    try:
        result = await session.call_tool(
            "generate_powerpoint_slide_by_slide",
            arguments={
                "slides": TEST_SLIDES,
                "template": template_to_use
            }
        )
        print("✅ generate_powerpoint_slide_by_slide successful")
        response_data = json.loads(result.content[0].text)
        print("Response:", json.dumps(response_data, indent=2))
        return True
    except Exception as e:
        print(f"❌ generate_powerpoint_slide_by_slide failed: {e}")
        return False

async def test_all_tools(server_url: str = "http://localhost:5001"):
    """Test all available tools in the SlideSpeak MCP server."""
    print("="*70)
    print("🚀 SLIDESPEAK MCP SERVER - COMPREHENSIVE TOOL TEST")
    print("="*70)
    
    print(f"🔗 Connecting to server: {server_url}/mcp")
    print("🔐 Using SlideSpeak API key authentication")
    
    try:
        async with streamablehttp_client(f"{server_url}/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                # Initialize session
                await session.initialize()
                print("✅ Connection initialized")
                
                # Get list of available tools
                tools = await session.list_tools()
                print(f"📚 Available tools: {[tool.name for tool in tools.tools]}")
                
                # Test results tracking
                test_results = {}
                
                # Run all tests in logical order
                test_functions = [
                    ("server_connectivity", test_server_connectivity),
                    ("get_available_templates", test_get_available_templates),
                    # ("generate_powerpoint", test_generate_powerpoint),
                    ("generate_powerpoint_slide_by_slide", test_generate_powerpoint_slide_by_slide),
                ]
                
                for test_name, test_func in test_functions:
                    try:
                        result = await test_func(session)
                        test_results[test_name] = result
                    except Exception as e:
                        print(f"❌ {test_name} failed with exception: {e}")
                        test_results[test_name] = False
                
                # Print summary
                print("\n" + "="*70)
                print("📊 TEST SUMMARY")
                print("="*70)
                
                passed_tests = sum(1 for result in test_results.values() if result)
                total_tests = len(test_results)
                
                for test_name, result in test_results.items():
                    status = "✅ PASS" if result else "❌ FAIL"
                    print(f"{status} {test_name}")
                
                print(f"\n🎯 Results: {passed_tests}/{total_tests} tests passed")
                
                if passed_tests == total_tests:
                    print("🎉 All tests passed! The SlideSpeak MCP server is working correctly.")
                else:
                    print("⚠️  Some tests failed. Check the logs above for details.")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the MCP server is running on the specified port")
        print("2. Verify your SlideSpeak API key is valid")
        print("3. Check that your environment variables are set correctly")
        print("4. Ensure SlideSpeak API is accessible from your network")

async def test_specific_tool(tool_name: str, server_url: str = "http://localhost:5001"):
    """Test a specific tool by name."""
    print(f"🎯 Testing specific tool: {tool_name}")
    
    
    async with streamablehttp_client(f"{server_url}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Map tool names to test functions
            tool_map = {
                "get_available_templates": test_get_available_templates,
                "generate_powerpoint": test_generate_powerpoint,
                "generate_powerpoint_slide_by_slide": test_generate_powerpoint_slide_by_slide,
            }
            
            if tool_name in tool_map:
                # For individual tool tests, we might need templates first
                if tool_name in ["generate_powerpoint", "generate_powerpoint_slide_by_slide"]:
                    print("🔄 Getting templates first...")
                    await test_get_available_templates(session)
                
                await tool_map[tool_name](session)
            else:
                print(f"❌ Unknown tool: {tool_name}")
                print(f"Available tools: {list(tool_map.keys())}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Check if first argument is a tool name or help
        if sys.argv[1] in ["help", "--help", "-h"]:
            print("SlideSpeak MCP Server Test Client")
            print("==================================")
            print("Usage:")
            print("  python client.py                              - Run all tests")
            print("  python client.py [server_url]                 - Run all tests against specified server")
            print("  python client.py [tool] [server]              - Run specific tool test")
            print("")
            print("Available tools:")
            print("  get_available_templates                       - Get all available presentation templates (supports limit parameter)")
            print("  generate_powerpoint                           - Generate PowerPoint from plain text")
            print("  generate_powerpoint_slide_by_slide            - Generate PowerPoint from slide array")
            print("")
            print("Environment variables required:")
            print("  SLIDESPEAK_API_KEY                            - Your SlideSpeak API key")
            print("")
            print("Example test data:")
            print(f"  Plain text: {TEST_PLAIN_TEXT[:50]}...")
            print(f"  Length: {TEST_LENGTH} slides")
            print(f"  Template: {TEST_TEMPLATE}")
        elif sys.argv[1] in ["get_available_templates", "generate_powerpoint", "generate_powerpoint_slide_by_slide"]:
            # Test specific tool
            tool_name = sys.argv[1]
            server_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5001"
            asyncio.run(test_specific_tool(tool_name, server_url))
        else:
            # First argument is server URL, test all tools
            server_url = sys.argv[1]
            asyncio.run(test_all_tools(server_url))
    else:
        # Test all tools with default server
        asyncio.run(test_all_tools())
