"""Run the local web server."""

import uvicorn


def main() -> None:
    uvicorn.run("my_stock_web.app:app", host="127.0.0.1", port=7800, reload=False)


if __name__ == "__main__":
    main()
