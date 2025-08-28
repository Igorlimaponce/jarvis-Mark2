from tools.__all_tools__ import get_all_tools


def test_tools_registry():
	tools = get_all_tools()
	assert any(t.name == "list_directory_contents" for t in tools)
	assert any(t.name == "open_application" for t in tools)
	assert any(t.name == "web_search" for t in tools)
