def test_main_module_registers_all_tools_on_import():
    import game_audio_mcp.main as main_module

    names = {t.name for t in main_module.mcp._tool_manager.list_tools()}
    assert {"generate_game_audio"} <= names
