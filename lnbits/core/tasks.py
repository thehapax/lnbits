import asyncio
from typing import Tuple, List, Callable, Awaitable
from quart import Request, g
from werkzeug.datastructures import Headers

from lnbits.settings import WALLET
from lnbits.db import open_db, open_ext_db

from .models import Payment
from .crud import get_standalone_payment

invoice_listeners: List[Tuple[str, Callable[[Payment], Awaitable[None]]]] = []


def register_invoice_listener(ext_name: str, callback: Callable[[Payment], Awaitable[None]]):
    """
    A method intended for extensions to call when they want to be notified about
    new invoice payments incoming.
    """
    print("registering callback", callback)
    invoice_listeners.append((ext_name, callback))


async def webhook_handler():
    handler = getattr(WALLET, "webhook_listener", None)
    if handler:
        handler()


async def invoice_listener(app):
    fakerequest = Request(
        "GET",
        "http",
        "/background/fake",
        b"",
        Headers([("host", "lnbits.background")]),
        "",
        "1.1",
        send_push_promise=lambda x, h: None,
    )
    async for checking_id in WALLET.paid_invoices_stream():
        async with app.request_context(fakerequest):
            # do this just so the g object is available
            g.db = await open_db()
            payment = await get_standalone_payment(checking_id)
            if payment.is_in:
                await payment.set_pending(False)
                loop = asyncio.get_event_loop()
                for ext_name, cb in invoice_listeners:
                    g.ext_db = await open_ext_db(ext_name)
                    loop.create_task(cb(payment))
