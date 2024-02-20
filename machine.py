class DataPath:
    used_latches = {}

    def __init__(self):
        pass


class ControlUnit:
    data_path = None

    def __init__(self, data_path):
        self.data_path = data_path
