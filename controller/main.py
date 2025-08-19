import signal, sys
from .environment import Controller

def main():
    c = Controller()
    def _sig(*_):
        c.stop()
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    c.run()

if __name__ == "__main__":
    main()
