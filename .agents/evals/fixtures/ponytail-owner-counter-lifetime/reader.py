epoch = 0


def create_owner(key):
    return {'key': key}


def advance(owner):
    global epoch
    epoch += 1
    return epoch
