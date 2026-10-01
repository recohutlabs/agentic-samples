"""Sanitized stderr progress for CLI runs; library calls remain quiet by default."""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event, Lock, Thread
from time import monotonic
import sys

_ACTIVE = ContextVar('contract_progress', default=None)


class Progress:
    """Time model steps without printing prompts, document content or provider errors."""
    def __init__(self, debug=False, stream=None, heartbeat_seconds=10, observer=None):
        self.observer = observer
        self.debug = debug
        self.stream = stream if stream is not None else sys.stderr
        self.heartbeat_seconds = heartbeat_seconds
        self.started = monotonic()
        self.lock = Lock()

    def log(self, message, debug=False):
        """Write an elapsed timestamp and flush immediately so pending work is visible."""
        if debug and not self.debug:
            return
        seconds = int(monotonic() - self.started)
        with self.lock:
            if self.observer is not None:
                self.observer(message)
            else:
                print(f'[{seconds // 60:02d}:{seconds % 60:02d}] {message}', file=self.stream, flush=True)

    @contextmanager
    def step(self, label, function):
        """Emit start/end/failure and a cancellable heartbeat while a step is pending."""
        started = monotonic()
        self.log(f'{label} started')
        self.log(f'Function: {function}()', debug=True)
        stop = Event()
        def heartbeat():
            while not stop.wait(self.heartbeat_seconds):
                self.log(f'{label} running — {int(monotonic() - started)}s elapsed')
        worker = Thread(target=heartbeat, daemon=True)
        worker.start()
        try:
            yield
        except BaseException as error:
            stop.set()
            worker.join()
            self.log(f'{label} failed ({type(error).__name__}) after {monotonic()-started:.1f}s')
            raise
        else:
            stop.set()
            worker.join()
            self.log(f'{label} completed — {monotonic()-started:.1f}s')

    def callback(self, **kwargs):
        """Use only SDK event kinds; never emit streamed text, reasoning or tool arguments."""
        event = kwargs.get('event') or {}
        if 'messageStart' in event:
            self.log('Model response stream started', debug=True)
        if 'messageStop' in event:
            self.log('Model response stream completed', debug=True)
        tool = event.get('contentBlockStart', {}).get('start', {}).get('toolUse')
        if tool:
            # Current agents expose only the structured-output tool. Avoid logging
            # arbitrary names that could originate in document/model content.
            self.log('Structured-output tool event received', debug=True)


@contextmanager
def progress_session(debug=False, observer=None):
    """Enable one CLI run's progress without changing stdout or runtime output schemas."""
    progress = Progress(debug=debug, observer=observer)
    token = _ACTIVE.set(progress)
    try:
        yield progress
    finally:
        _ACTIVE.reset(token)


@contextmanager
def step(label, function):
    """Instrument a workflow step only when a progress session is active."""
    progress = _ACTIVE.get()
    if progress is None:
        yield
    else:
        with progress.step(label, function):
            yield


def log(message, debug=False):
    """Write safe host-produced progress details for the active run."""
    progress = _ACTIVE.get()
    if progress is not None:
        progress.log(message, debug=debug)


def callback_handler():
    """Capture the active progress handler for SDK callbacks in other execution contexts."""
    progress = _ACTIVE.get()
    return progress.callback if progress is not None and progress.debug else None
