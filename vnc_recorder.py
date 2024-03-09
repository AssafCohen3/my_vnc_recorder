"""
Influenced by https://github.com/kaganisildak/vnc2mp4
"""

import logging
import shutil
import time
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from tempfile import TemporaryDirectory
from typing import Optional

import cv2
import numpy as np
import vncdotool.api
from vncdotool.api import ThreadedVNCClientProxy
from vncdotool.client import VNCDoToolClient


class VNCAPIConnectType(VNCDoToolClient, ThreadedVNCClientProxy):
    pass


class VNCRecorder:
    def __init__(self, host: str, port: int, password: Optional[str] = None, fps: int = 30):
        self._host: str = host
        self._port: int = port
        self._password: Optional[str] = password
        self._fps: int = fps

    def subprocess_record(self, interprocess_queue: Queue):
        with TemporaryDirectory() as temp_output_dir_path:
            temp_output_path = Path(temp_output_dir_path) / 'output.mp4'

            video_writer: Optional[cv2.VideoWriter] = None
            cli: Optional[VNCAPIConnectType] = None
            try:
                # noinspection PyTypeChecker
                cli: VNCAPIConnectType = vncdotool.api.connect(
                    server=f'{self._host}::{self._port}',
                    password=self._password
                )
                cli.refreshScreen(False)
                video_dims = cli.screen.size
                # noinspection PyUnresolvedReferences
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                output_path: Optional[Path] = None

                logging.info(f'Saving video to temporary path: {temp_output_path}')
                video_writer = cv2.VideoWriter(
                    filename=str(temp_output_path),
                    fourcc=fourcc,
                    fps=self._fps,
                    frameSize=video_dims
                )
                while True:
                    output_path = self.try_get_output_path(interprocess_queue)
                    if output_path is not None:
                        break
                    else:
                        self.record_second(cli, video_writer)
            finally:
                if video_writer is not None:
                    video_writer.release()
                if cli is not None:
                    cli.disconnect()
                    vncdotool.api.shutdown()
                if output_path is not None:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(temp_output_path, output_path)

    @staticmethod
    def try_get_output_path(queue: Queue) -> Optional[Path]:
        try:
            message = queue.get(block=False)
        except Empty:
            return None

        return Path(message)

    def record_second(self, cli: VNCAPIConnectType, video_writer: cv2.VideoWriter):
        expected_finish_time = time.time() + 1.0

        for i in range(self._fps):
            current_frame_start_time = time.time()
            time_left_to_finish = expected_finish_time - current_frame_start_time
            frame_expected_finish_time = current_frame_start_time + time_left_to_finish / (self._fps - i)

            cli.refreshScreen(False)
            imtemp = cli.screen.copy()
            video_writer.write(cv2.cvtColor(np.array(imtemp), cv2.COLOR_RGB2BGR))

            current_frame_record_finish_time = time.time()
            if current_frame_record_finish_time < frame_expected_finish_time:
                time.sleep(frame_expected_finish_time - current_frame_record_finish_time)
