import re

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
            "Numéro de": "phone",
        }

        for i, line in enumerate(self._block.lines):
            sentence = " ".join([word.value for word in line.words])
            for key, field in FIELD_MAP.items():
                if key in sentence:
                    if field == "phone":
                        val = self.get_line_value(i, field)
                    else:
                        val = self.get_next_line_value(i, field)
                    user[FIELD_MAP[key]] = val

            sentences.append(sentence)
        if user:
            filename = f"runs/{self.slug}/{dt.now().strftime('%Y%m%d-%H:%M:%S')}.txt"
            with open(filename, "w") as f:
                f.write("\n".join(sentences))
        return user

    def clean_birth_date(self, birth_date):
        parsed = dateparser.parse(birth_date)
        if parsed:
            return parsed.strftime("%Y-%m-%d")

    def clean_phone(self, phone):
        search = re.search(r"\d{8}", phone)
        if search:
            return search.group()

    def get_next_line_value(self, line, field):
        return self.get_line_value(line + 1, field)

    def get_line_value(self, line, field):
        val = self.get_line(line)
        if hasattr(self, f"clean_{field}"):
            val = getattr(self, f"clean_{field}")(val)
        return val
