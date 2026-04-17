def dump(obj, indent=0):
    pad = "  " * indent

    if isinstance(obj, list):
        for item in obj:
            dump(item, indent)
        return

    if hasattr(obj, "__dict__"):
        print(f"{pad}{obj.__class__.__name__}(")
        for k, v in obj.__dict__.items():
            print(f"{pad}  {k}=")
            dump(v, indent + 2)
        print(f"{pad})")
    else:
        print(f"{pad}{obj}")