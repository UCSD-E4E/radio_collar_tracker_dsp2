'''General support utilities
'''
import logging
from threading import Thread


class InstrumentedThread(Thread):
    """Extention of threading.Thread that captures any exception from the thread

    """
    def run(self) -> None:
        try:
            return super().run()
        except Exception as exc:
            logging.exception('Unhandled fatal exception in %s', self.name)
            raise exc
