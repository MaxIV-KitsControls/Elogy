from random import randint

from faker import Faker
from faker.providers import BaseProvider


fake = Faker()


class ElogyProvider(BaseProvider):

    def title(self):
        return fake.sentence()

    def authors(self):
        authors = []
        for i in range(randint(1, 5)):
            name = fake.name()
            first, last = name.split(" ", 1)
            login = (first[:3] + last[:3]).lower()
            email = fake.email()
            authors.append(dict(name=name, email=email, login=login))
        return authors

    def text_content(self):
        return fake.text()

    def html_content(self):
        body = "</p><p>".join(fake.paragraphs())
        return "<html><body><p>{}</p></body></html>".format(body)

    def entry(self):
        return {
            "title": self.title(),
            "authors": self.authors(),
            "content_type": "text/html",
            "content": self.html_content()
        }

    def text_entry(self):
        return {
            "title": self.title(),
            "authors": self.authors(),
            "content_type": "text/plain",
            "content": self.text_content()
        }
