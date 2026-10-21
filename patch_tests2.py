with open('/app/tests/test_phase5_academic_focus.py', 'r') as f:
    content = f.read()

content = content.replace('tree_species="Sakura Cherry Blossom"', 'species="Sakura Cherry Blossom"')

patch2 = """    test_db = tmp_path / "test_forest_wilt.db"
    engine = ForestEngine(db_path=test_db)
    await engine.initialize()"""

content = content.replace('    test_db = tmp_path / "test_forest_wilt.db"\n    engine = ForestEngine(db_path=test_db)', patch2)

with open('/app/tests/test_phase5_academic_focus.py', 'w') as f:
    f.write(content)
