class VCSError(Exception):
    def __init__(self, msg, directory):
        self.msg = msg
        self.directory = directory

    def __str__(self):
        return self.msg + ' ({})'.format(self.directory)
