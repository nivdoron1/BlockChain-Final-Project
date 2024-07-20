
from ape_ethereum import Receipt

def find_event(tx: Receipt, name: str):
    for event in tx.events:
        if event.event_name == name:
            return event
    return None

