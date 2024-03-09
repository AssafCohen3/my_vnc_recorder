import asyncio
from multiprocessing import Process
from multiprocessing import Queue
from pathlib import Path

from vnc_recorder import VNCRecorder


async def main():
    recorder = VNCRecorder(
        host='localhost',
        port=5900,
        fps=30
    )

    queue = Queue()
    p = Process(target=recorder.subprocess_record, args=(queue,), daemon=True)
    print('Starting process...')

    p.start()

    await asyncio.sleep(5)

    print('Stopping process...')
    queue.put(str(Path('./doom.mp4')))
    p.join()


if __name__ == '__main__':
    asyncio.run(main())
