from __future__ import annotations

"""Stand-ins for the LLM, embedder, graph extractor, and PDF bytes."""

import hashlib
import math
import re

import fitz
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from agents.EvalAgent import EvalResult
from agents.ResponseAgent import Flashcard, FlashcardSet, QuizQuestion, QuizSet

ANSWER = (
    'Variance measures how far a set of numbers is spread out from their average value. '
    'A small variance means the values cluster tightly around the mean, while a large variance means they are more dispersed. '
    'In a textbook this idea is used to compare consistency across samples and to build standard deviation. '
    'You can think of it as the average squared distance from the mean, which stays positive and emphasizes larger gaps.'
)


def _blob(value) -> str:
    if hasattr(value, 'to_messages'):
        parts = []
        for message in value.to_messages():
            content = message.content
            if isinstance(content, list):
                content = ' '.join(str(part) for part in content)
            parts.append(str(content))
        return '\n'.join(parts)
    if isinstance(value, list):
        return '\n'.join(str(getattr(message, 'content', message)) for message in value)
    return str(value)


class _Structured(Runnable):
    def __init__(self, parent: 'FakeChatModel', schema):
        self.parent = parent
        self.schema = schema

    def invoke(self, input, config=None, **kwargs):
        return self.parent.structured(self.schema, input)

    async def ainvoke(self, input, config=None, **kwargs):
        return self.parent.structured(self.schema, input)


class FakeChatModel(Runnable):
    """Scripted chat model that satisfies the pipeline's LCEL and tool calls."""

    def __init__(self, *, bad_answers: int = 0, fail_grounding: int = 0):
        self.bad_answers = bad_answers
        self.fail_grounding = fail_grounding
        self.answer_calls = 0
        self.grounding_calls = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        return _Structured(self, schema)

    def invoke(self, input, config=None, **kwargs):
        return self._respond(input)

    async def ainvoke(self, input, config=None, **kwargs):
        return self._respond(input)

    def structured(self, schema, value):
        name = getattr(schema, '__name__', '')
        if name == 'EvalResult':
            self.grounding_calls += 1
            passed = self.grounding_calls > self.fail_grounding
            explanation = 'Grounded in the excerpts.' if passed else 'Not grounded in the excerpts.'
            return EvalResult(
                passed=passed,
                score=1.0 if passed else 0.2,
                claims_checked=2,
                claims_grounded=2 if passed else 0,
                ungrounded_claims=[] if passed else ['unsupported claim'],
                explanation=explanation,
            )
        if name == 'QuizSet':
            return QuizSet(
                questions=[
                    QuizQuestion(
                        question=f'Question {index} about variance?',
                        choices=['spread', 'location', 'color'],
                        correct_choice='spread',
                    )
                    for index in range(1, 4)
                ]
            )
        if name == 'FlashcardSet':
            return FlashcardSet(
                items=[
                    Flashcard(
                        front='What is variance?',
                        back='A measure of spread.',
                        citations=['[p1]'],
                    )
                ]
            )
        raise AssertionError(f'Unexpected structured schema {name}')

    def _respond(self, value):
        blob = _blob(value)
        lowered = blob.lower()
        if 'which tool' in lowered:
            query = blob.split('Query:', 1)[-1].strip()
            return AIMessage(
                content='',
                tool_calls=[
                    {'name': 'vector_search', 'args': {'query': query}, 'id': 'call-vector', 'type': 'tool_call'},
                    {'name': 'graph_search', 'args': {'query': query}, 'id': 'call-graph', 'type': 'tool_call'},
                ],
            )
        if 'rewrite the user' in lowered:
            return AIMessage(content='variance spread of data')

        self.answer_calls += 1
        if self.answer_calls <= self.bad_answers:
            return AIMessage(content='[p1]')
        pages = re.findall(r'\[p(\d+)\]', blob)
        if not pages:
            return AIMessage(content=ANSWER)
        return AIMessage(content=f'{ANSWER}\n\nReferences: [p{pages[0]}]')


class HashEmbedder:
    """Bag-of-tokens embedding so pgvector retrieval works without Gemini."""

    dim = 3072

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in re.findall(r'[a-z0-9]+', text.lower()):
            digest = hashlib.md5(token.encode()).hexdigest()
            vector[int(digest, 16) % self.dim] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]


class FakeGraphExtractor:
    """Returns a fixed statistics graph so ingestion can fill Neo4j without DeepSeek."""

    def extract(self, text: str) -> dict:
        return {
            'entities': [
                {'name': 'variance', 'type': 'concept', 'description': 'spread of data'},
                {'name': 'data', 'type': 'concept', 'description': 'observations'},
            ],
            'relationships': [
                {
                    'source': 'variance',
                    'target': 'data',
                    'type': 'ESTIMATES',
                    'evidence': (text or '')[:120],
                }
            ],
        }


def make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    payload = document.tobytes()
    document.close()
    return payload
