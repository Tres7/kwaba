class MessagingSuspendedException(Exception):
    def __init__(self, until):
        super().__init__("Votre messagerie est suspendue : vous pouvez lire vos conversations mais pas écrire.")
        self.until = until
