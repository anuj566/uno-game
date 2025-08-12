# game.py
import random

class Card:
    """ Represents a single UNO card """
    def __init__(self, color, value):
        self.color = color # Can be Red, Green, Blue, Yellow, or Wild
        self.value = value # Can be 0-9, "Skip", "Reverse", "Draw Two", "Wild", "Wild Draw Four"

    def __repr__(self):
        return f"Card({self.color}, {self.value})"
    
    def __str__(self):
        return f"{self.color} {self.value}"

class Deck:
    """ Represents the deck of 108 UNO cards """
    def __init__(self):
        self.cards = []
        self.build_deck()
        self.shuffle()

    def build_deck(self):
        """ Builds the full 108-card deck """
        colors = ["Red", "Green", "Blue", "Yellow"]
        values = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Skip", "Reverse", "Draw Two"]
        
        for color in colors:
            for value in values:
                count = 1 if value == "0" else 2
                for _ in range(count):
                    self.cards.append(Card(color, value))
        
        for _ in range(4):
            self.cards.append(Card("Wild", "Wild"))
            self.cards.append(Card("Wild", "Wild Draw Four"))

    def shuffle(self):
        """ Shuffles the deck """
        random.shuffle(self.cards)

    def draw_card(self):
        """ Draws a single card from the top of the deck """
        if not self.cards:
            return None
        return self.cards.pop()
