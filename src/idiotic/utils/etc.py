def mangle_name(name):
    return ''.join((x for x in name.lower().replace(" ", "_") if x.isalnum() or x=='_')) if name else ""
