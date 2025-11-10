import time

from demo.workflows import wfr


if __name__ == "__main__":
    wfr.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        wfr.shutdown()
