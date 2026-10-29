with open("sunday/dashboard/api/main.py", "r") as f:
    content = f.read()

# Replace the get_memory_stats function to use a helper function or a dependency
new_func = """
def _get_memory_data():
    return {
        "total_episodes": 0,
        "avg_surprise": 0.0,
        "high_surprise_count": 0
    }

@app.get("/api/memory/stats")
async def get_memory_stats():
    \"\"\"Get memory statistics.\"\"\"
    try:
        # Placeholder - would use actual memory system
        return _get_memory_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""

content = content.replace("""@app.get("/api/memory/stats")
async def get_memory_stats():
    \"\"\"Get memory statistics.\"\"\"
    try:
        # Placeholder - would use actual memory system
        return {
            "total_episodes": 0,
            "avg_surprise": 0.0,
            "high_surprise_count": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))""", new_func)

with open("sunday/dashboard/api/main.py", "w") as f:
    f.write(content)
