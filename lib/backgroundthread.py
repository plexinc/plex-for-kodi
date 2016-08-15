import Queue
import xbmc
import util
from plexnet import threadutils


class Task:
    def __init__(self):
        self._canceled = False

    def start(self):
        BGThreader.addTask(self)

    def run(self):
        pass

    def cancel(self):
        self._canceled = True

    def isCanceled(self):
        return self._canceled or xbmc.abortRequested


class BackgroundWorker:
    def __init__(self, queue, name=None):
        self._queue = queue
        self.name = name
        self._thread = None
        self._abort = False
        self._task = None

    def _runTask(self, task):
        if task._canceled:
            return
        try:
            task.run()
        except:
            util.ERROR()

    def abort(self):
        self._abort = True
        return self

    def aborted(self):
        return self._abort or xbmc.abortRequested

    def start(self):
        if self._thread and self._thread.isAlive():
            return

        self._thread = threadutils.KillableThread(target=self._queueLoop, name='BACKGROUND-WORKER({0})'.format(self.name))
        self._thread.start()

    def _queueLoop(self):
        if self._queue.empty():
            return

        util.DEBUG_LOG('BGThreader: ({0}): Active'.format(self.name))
        try:
            while not self.aborted():
                self._task = self._queue.get_nowait()
                self._runTask(self._task)
                self._queue.task_done()
                self._task = None
        except Queue.Empty:
            util.DEBUG_LOG('BGThreader ({0}): Idle'.format(self.name))

    def shutdown(self):
        self.abort()

        if self._task:
            self._task.cancel()

        if self._thread and self._thread.isAlive():
            util.DEBUG_LOG('BGThreader: thread ({0}): Waiting...'.format(self.name))
            self._thread.join()
            util.DEBUG_LOG('BGThreader: thread ({0}): Done'.format(self.name))

    def working(self):
        return self._thread and self._thread.isAlive()


class BackgroundThreader:
    def __init__(self, name=None, worker_count=8):
        self.name = name
        self._queue = Queue.Queue()
        self._abort = False
        self.workers = [BackgroundWorker(self._queue, 'queue.{0}:worker.{1}'.format(self.name, x)) for x in range(worker_count)]

    def abort(self):
        self._abort = True
        for w in self.workers:
            w.abort()
        return self

    def aborted(self):
        return self._abort or xbmc.abortRequested

    def shutdown(self):
        self.abort()

        for w in self.workers:
            w.shutdown()

    def addTask(self, task):
        self._queue.put(task)
        util.TEST(self._queue.qsize())
        self.startWorkers()

    def addTasks(self, tasks):
        for t in tasks:
            self._queue.put(t)
        self.startWorkers()

    def startWorkers(self):
        for w in self.workers:
            w.start()

    def working(self):
        return not self._queue.empty() or self.hasTask()

    def hasTask(self):
        return any([w.working() for w in self.workers])


class ThreaderManager:
    def __init__(self):
        self.index = 0
        self.abandoned = []
        self.threader = BackgroundThreader(str(self.index))

    def __getattr__(self, name):
        return getattr(self.threader, name)

    def reset(self):
        if self.threader._queue.empty() and not self.threader.hasTask():
            return

        self.index += 1
        self.abandoned.append(self.threader.abort())
        self.threader = BackgroundThreader(str(self.index))

    def shutdown(self):
        self.threader.shutdown()
        for a in self.abandoned:
            a.shutdown()

BGThreader = ThreaderManager()
