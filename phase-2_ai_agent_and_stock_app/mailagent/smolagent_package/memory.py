
# mailagent/smolagent_package/memory.py


class AgentMemory:
    def __init__(self):
        self.logs = []

    def add_interaction(self, entry):
        self.logs.append(entry)

    def get_recent(self, n=5):
        return self.logs[-n:]
