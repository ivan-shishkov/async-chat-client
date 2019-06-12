from contextlib import asynccontextmanager

from aionursery import Nursery, MultiError


@asynccontextmanager
async def create_handy_nursery():
    try:
        async with Nursery() as nursery:
            yield nursery
    except MultiError as e:
        if len(e.exceptions) == 1:
            raise e.exceptions[0]
        raise


def get_sanitized_text(text):
    return text.replace('\n', '')
