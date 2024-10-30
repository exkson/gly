from datetime import datetime as dt
import dateparser

from extractors.base import BaseExtractor


class CIPExtractor(BaseExtractor):
    slug = "cip"

    def extract(self):
        user = {}
        sentences = []

        FIELD_MAP = {
            "Nom:": "last_name",
            "Prénom": "first_name",
            "Date de naissance": "birth_date",
        }

        for i, line in enumerate(self._block.lines):
            sentence = " ".join([word.value for word in line.words])
            for key in FIELD_MAP:
                if key in sentence:
                    val = self.get_line(i + 1)
                    if hasattr(self, f"clean_{FIELD_MAP[key]}"):
                        val = getattr(self, f"clean_{FIELD_MAP[key]}")(val)
                    user[FIELD_MAP[key]] = val
            sentences.append(sentence)
        if user:
            filename = f"runs/{self.slug}/{dt.now().strftime('%Y%m%d-%H:%M:%S')}.txt"
            with open(filename, "w") as f:
                f.write("\n".join(sentences))
        return user

    def clean_birth_date(self, birth_date):
        return dateparser.parse(birth_date).date()
