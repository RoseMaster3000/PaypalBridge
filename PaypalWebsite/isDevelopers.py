ADMINS = ["admin"] # to add more ["admin", "dimad", "wertyr"]

def isDeveloper(username, debug=False):
    if debug:
        return True
    return username in ADMINS



