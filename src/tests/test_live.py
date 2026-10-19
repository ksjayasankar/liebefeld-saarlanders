"""Live check of quoted pages (D-32) against a fake site."""
import httpx

from navigator import live

QUOTE = "Our lab develops closed-loop insulin delivery for people with diabetes."
PAGES = {
    "/same": f"<main><p>Our <a href='#'>lab</a> develops closed‑loop insulin delivery for people with <b>diabetes</b>.</p></main>",
    "/edited": "<main><p>Our lab now works on something else.</p></main>",
}


def client():
    def handle(request):
        if request.url.path == "/down":
            raise httpx.ConnectTimeout("timeout", request=request)
        body = PAGES.get(request.url.path)
        return httpx.Response(200, text=body) if body else httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handle), base_url="https://lab.example")


def test_quote_found_through_inline_markup_and_hyphen_variants():
    assert live.status(client(), "https://lab.example/same", [QUOTE]) == {QUOTE: "found"}


def test_changed_gone_and_unreachable():
    c = client()
    assert live.status(c, "https://lab.example/edited", [QUOTE]) == {QUOTE: "changed"}
    assert live.status(c, "https://lab.example/missing", [QUOTE]) == {QUOTE: "gone"}
    assert live.status(c, "https://lab.example/down", [QUOTE]) == {QUOTE: "unreachable"}
