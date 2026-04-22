import os

def list_cogs():
    """Auto-discover all cog files in the cogs/ folder"""
    return [f[:-3] for f in os.listdir(os.path.dirname(__file__)) if f.endswith(".py") and not f.startswith("_")]
