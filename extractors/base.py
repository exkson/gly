from abc import abstractmethod

from doctr.io import Document


class BaseExtractor:
    slug: str

    def __init__(self, document: Document):
        self._document = document
        self._block = document.pages[0].blocks[0]

    @abstractmethod
    def extract(self) -> dict:
        pass

    def get_line(self, index):
        return " ".join([word.value for word in self._block.lines[index].words])
