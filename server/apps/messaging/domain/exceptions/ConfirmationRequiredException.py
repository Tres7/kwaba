class ConfirmationRequiredException(Exception):
    def __init__(self, categories):
        super().__init__("Ce message risque d'être mal reçu. Confirmez-vous son envoi ?")
        self.categories = tuple(categories)
