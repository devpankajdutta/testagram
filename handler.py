try:
    from app.main import handler
except ImportError:
    # Fallback or debugging
    import sys
    print(f"Path: {sys.path}")
    raise
