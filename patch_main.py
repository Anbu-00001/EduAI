import re

with open("app/api/main.py", "r") as f:
    content = f.read()

endpoint = """
@app.get("/v1/features/ranges")
async def get_feature_ranges():
    return app.state.feature_ranges

"""
if "/v1/features/ranges" not in content:
    content = content.replace('def get_notice():', endpoint + 'def get_notice():')
    with open("app/api/main.py", "w") as f:
        f.write(content)
