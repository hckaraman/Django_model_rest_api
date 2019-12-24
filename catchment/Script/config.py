class ModeSelector(object):
    def __init__(self, mode):
        self.mode_list = ["run", "debug"]
        self.mode = mode

    @property
    def get_path(self):
        if self.mode == self.mode_list[1]:
            return '../../file_uploads'
        elif self.mode == self.mode_list[0]:
            return '../../file_uploads'

    @property
    def get_verbose(self):
        if self.mode == self.mode_list[1]:
            return True
        elif self.mode == self.mode_list[0]:
            return False
