ADMINS = ["admin"] # to add more ["admin, "dimad", "wertyr"]

def isDeveloper(username, debug):
    return username in ADMINS or debug

