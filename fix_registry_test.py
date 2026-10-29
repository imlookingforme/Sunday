import re

with open("tests/test_dashboard_api.py", "r") as f:
    content = f.read()

content = content.replace("ToolRegistry._tools = {}", "")
content = content.replace("""
@pytest.fixture(autouse=True)
def setup_tools():
    # Clear tools before each test


    async def dummy_func""", """
@pytest.fixture(autouse=True)
def setup_tools():
    # Clear tools before each test
    original_tools = dict(ToolRegistry._tools)
    ToolRegistry._tools = {}

    async def dummy_func""")

content = content.replace("""    yield

""", """    yield
    ToolRegistry._tools = original_tools
""")

with open("tests/test_dashboard_api.py", "w") as f:
    f.write(content)
