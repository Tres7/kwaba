class MessageRefusedException(Exception):
    def __init__(self, categories):
        super().__init__("Ce message ne respecte pas les règles de la messagerie.")
        self.categories = tuple(categories)
