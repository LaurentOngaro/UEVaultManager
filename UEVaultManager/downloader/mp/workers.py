# coding: utf-8
"""
Implementation for:
- DLWorker: Downloads chunks from the internet and writes them to the shared memory segment.
- FileWorker: Writes chunks to files.
"""
import logging
import os
import time
from logging.handlers import QueueHandler
from multiprocessing import Process
from multiprocessing.shared_memory import SharedMemory
from queue import Empty

import requests

import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.lfs.utils import path_join
from UEVaultManager.models.ChunkClass import Chunk
from UEVaultManager.models.downloading import (DownloaderTask, DownloaderTaskResult, TaskFlags, TerminateWorkerTask, WriterTask, WriterTaskResult)


class DLWorker(Process):
    """
    Worker process that downloads chunks from the internet and writes them to the shared memory segment.
    :param name: name of the process
    :param queue: queue to get jobs from
    :param out_queue: queue to put results in
    :param shm: name of the shared memory segment to write to
    :param max_retries: maximum number of retries for a chunk
    :param logging_queue: queue to send log messages to
    :param timeout: timeout for the request. Could be a float or a tuple of float (connect timeout, read timeout).
    """

    def __init__(self, name, queue, out_queue, shm, max_retries=7, logging_queue=None, timeout=(7, 7)):
        super().__init__(name=name)
        self.q = queue
        self.o_q = out_queue
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'EpicGamesLauncher/11.0.1-14907503+++Portal+Release-Live Windows/10.0.19041.1.256.64bit'})
        self.max_retries = max_retries
        self.shm = SharedMemory(name=shm)
        self.log_level = logging.getLogger().level
        self.logging_queue = logging_queue
        self.timeout = timeout

    def run(self) -> None:
        """
        Main loop of the worker process.
        """
        # we have to fix up the logger before we can start
        _root = logging.getLogger()
        _root.handlers = []
        _root.addHandler(QueueHandler(self.logging_queue))

        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        logger.debug(f'Download worker reporting for duty!')

        empty = False
        while True:
            try:
                job: DownloaderTask = self.q.get(timeout=7)
                empty = False
            except Empty:
                if not empty:
                    logger.debug('Queue Empty, waiting for more...')
                empty = True
                continue

            if isinstance(job, TerminateWorkerTask):  # let worker die
                logger.debug('Worker received termination signal, shutting down...')
                break

            tries = 0
            compressed = 0
            chunk = None

            try:
                while tries < self.max_retries:
                    if gui_g.WindowsRef.progress and not gui_g.WindowsRef.progress.continue_execution:
                        logger.warning('Stop button has been pressed, exit requested, quitting...')
                        break
                    # retry once immediately, otherwise do exponential backoff
                    if tries > 1:
                        sleep_time = 2 ** (tries - 1)
                        logger.info(f'Sleeping {sleep_time} seconds before retrying.')
                        time.sleep(sleep_time)

                    # print('Downloading', job.url)
                    logger.debug(f'Downloading {job.url}')

                    try:
                        r = self.session.get(job.url, timeout=self.timeout)
                        r.raise_for_status()
                    except Exception as error:
                        logger.warning(f'Chunk download for {job.chunk_guid} failed: ({error!r}), retrying...')
                        continue

                    if r.status_code != 200:
                        logger.warning(f'Chunk download for {job.chunk_guid} failed: status {r.status_code}, retrying...')
                        continue
                    else:
                        compressed = len(r.content)
                        chunk = Chunk.read_buffer(r.content)
                        break
                else:
                    raise TimeoutError('Max retries reached')
            except Exception as error:
                logger.error(f'Job for {job.chunk_guid} failed with: {error!r}, fetching next one...')
                # add failed job to result queue to be requeued
                self.o_q.put(DownloaderTaskResult(success=False, **job.__dict__))
            except KeyboardInterrupt:
                logger.warning('Immediate exit requested, quitting...')
                break

            if not chunk:
                logger.warning('Chunk somehow None?')
                self.o_q.put(DownloaderTaskResult(success=False, **job.__dict__))
                continue

            # decompress stuff
            try:
                size = len(chunk.data)
                if size > job.shm.size:
                    logger.critical('Downloaded chunk is longer than SharedMemorySegment!')

                self.shm.buf[job.shm.offset:job.shm.offset + size] = bytes(chunk.data)
                del chunk
                self.o_q.put(DownloaderTaskResult(success=True, size_decompressed=size, size_downloaded=compressed, **job.__dict__))
            except Exception as error:
                logger.warning(f'Job for {job.chunk_guid} failed with: {error!r}, fetching next one...')
                self.o_q.put(DownloaderTaskResult(success=False, **job.__dict__))
                continue
            except KeyboardInterrupt:
                logger.warning('Immediate exit requested, quitting...')
                break

        self.shm.close()


class FileWorker(Process):
    """
    Worker process that writes chunks to files.
    :param queue: queue to get jobs from
    :param out_queue: queue to put results in
    :param base_path: base path to write files to
    :param shm: name of the shared memory segment to read from
    :param cache_path: path to the cache directory
    :param logging_queue: queue to send log messages to
    """

    def __init__(self, queue, out_queue, base_path, shm, cache_path=None, logging_queue=None):
        super().__init__(name='FileWorker')
        self.q = queue
        self.o_q = out_queue
        self.base_path = base_path
        self.cache_path = cache_path or path_join(base_path, '.cache')
        self.shm = SharedMemory(name=shm)
        self.log_level = logging.getLogger().level
        self.logging_queue = logging_queue

    def run(self) -> None:
        """
        Main loop of the worker process.
        """
        # we have to fix up the logger before we can start
        _root = logging.getLogger()
        _root.handlers = []
        _root.addHandler(QueueHandler(self.logging_queue))

        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        logger.debug('Download worker reporting for duty!')

        last_filename = ''
        current_file = None
        # noinspection PyTypeChecker
        j = None
        while True:
            try:
                try:
                    j: WriterTask = self.q.get(timeout=7)  # no tuple here !
                except Empty:
                    logger.warning('Writer queue empty')
                    continue

                if isinstance(j, TerminateWorkerTask):
                    if current_file:
                        current_file.close()
                    logger.debug('Worker received termination signal, shutting down...')
                    # send termination task to results halnder as well
                    self.o_q.put(TerminateWorkerTask())
                    break

                # make directories if required
                path = os.path.split(j.filename)[0]
                if not os.path.exists(path_join(self.base_path, path)):
                    os.makedirs(path_join(self.base_path, path))

                full_path = path_join(self.base_path, j.filename)

                if j.flags & TaskFlags.CREATE_EMPTY_FILE:  # just create an empty file
                    open(full_path, 'a').close()
                    self.o_q.put(WriterTaskResult(success=True, **j.__dict__))
                    continue
                elif j.flags & TaskFlags.OPEN_FILE:
                    if current_file:
                        logger.warning(f'Opening new file {j.filename} without closing previous! {last_filename}')
                        current_file.close()

                    current_file = open(full_path, 'wb')
                    last_filename = j.filename

                    self.o_q.put(WriterTaskResult(success=True, **j.__dict__))
                    continue
                elif j.flags & TaskFlags.CLOSE_FILE:
                    if current_file:
                        current_file.close()
                        current_file = None
                    else:
                        logger.warning(f'Asking to close file that is not open: {j.filename}')

                    self.o_q.put(WriterTaskResult(success=True, **j.__dict__))
                    continue
                elif j.flags & TaskFlags.RENAME_FILE:
                    if current_file:
                        logger.warning('Trying to rename file without closing first!')
                        current_file.close()
                        current_file = None
                    if j.flags & TaskFlags.DELETE_FILE:
                        try:
                            os.remove(full_path)
                        except OSError as error:
                            logger.error(f'Removing file failed: {error!r}')
                            self.o_q.put(WriterTaskResult(success=False, **j.__dict__))
                            continue

                    try:
                        os.rename(path_join(self.base_path, j.old_file), full_path)
                    except OSError as error:
                        logger.error(f'Renaming file failed: {error!r}')
                        self.o_q.put(WriterTaskResult(success=False, **j.__dict__))
                        continue

                    self.o_q.put(WriterTaskResult(success=True, **j.__dict__))
                    continue
                elif j.flags & TaskFlags.DELETE_FILE:
                    if current_file:
                        logger.warning('Trying to delete file without closing first!')
                        current_file.close()
                        current_file = None

                    try:
                        os.remove(full_path)
                    except OSError as error:
                        if not j.flags & TaskFlags.SILENT:
                            logger.error(f'Removing file failed: {error!r}')

                    self.o_q.put(WriterTaskResult(success=True, **j.__dict__))
                    continue
                elif j.flags & TaskFlags.MAKE_EXECUTABLE:
                    if current_file:
                        logger.warning('Trying to chmod file without closing first!')
                        current_file.close()
                        current_file = None

                    try:
                        st = os.stat(full_path)
                        os.chmod(full_path, st.st_mode | 0o111)
                    except OSError as error:
                        if not j.flags & TaskFlags.SILENT:
                            logger.error(f'chmod\'ing file failed: {error!r}')

                    self.o_q.put(WriterTaskResult(success=True, **j.__dict__))
                    continue

                try:
                    if j.shared_memory:
                        shm_offset = j.shared_memory.offset + j.chunk_offset
                        shm_end = shm_offset + j.chunk_size
                        current_file.write(self.shm.buf[shm_offset:shm_end].tobytes())
                    elif j.cache_file:
                        with open(path_join(self.cache_path, j.cache_file), 'rb') as file:
                            if j.chunk_offset:
                                file.seek(j.chunk_offset)
                            current_file.write(file.read(j.chunk_size))
                    elif j.old_file:
                        with open(path_join(self.base_path, j.old_file), 'rb') as file:
                            if j.chunk_offset:
                                file.seek(j.chunk_offset)
                            current_file.write(file.read(j.chunk_size))
                except Exception as error:
                    logger.warning(f'Something in writing a file failed: {error!r}')
                    self.o_q.put(WriterTaskResult(success=False, size=j.chunk_size, **j.__dict__))
                else:
                    self.o_q.put(WriterTaskResult(success=True, size=j.chunk_size, **j.__dict__))
            except Exception as error:
                logger.warning(f'Job {j.filename} failed with: {error!r}, fetching next one...')
                self.o_q.put(WriterTaskResult(success=False, **j.__dict__))

                try:
                    if current_file:
                        current_file.close()
                        current_file = None
                except Exception as error:
                    logger.error(f'Closing file after error failed: {error!r}')
            except KeyboardInterrupt:
                logger.warning('Immediate exit requested, quitting...')
                if current_file:
                    current_file.close()
                return
