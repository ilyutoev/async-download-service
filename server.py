import os
import logging
import asyncio
import argparse
from functools import partial

from aiohttp import web
import aiofiles


DEFAULT_PHOTOS_FOLDER = 'test_photos'
DEFAULT_DELAY = 0


def get_arguments():
    """Получаем аргументы командной строки, переданной скрипту."""
    parser = argparse.ArgumentParser(description='Script runs server for downloading photo archives')
    parser.add_argument('--logging', default=False, action='store_true', help='Enable logging.')
    parser.add_argument('--delay', type=int, default=DEFAULT_DELAY, help='Enable delay before downloading.')
    parser.add_argument('--folder', type=str, default=DEFAULT_PHOTOS_FOLDER, help="Path to photo directory.")
    return parser.parse_args()


async def archivate(request, photos_folder, delay):
    """
    Функция, которая архивирует переданую в запросе папку и возвращает ответ клиенту по частям.
    :params photos_folder папка с фотографиями
    :params delay задержка между частями ответа
    """
    response = web.StreamResponse()

    archive_hash = request.match_info.get('archive_hash')
    full_path_to_folder = os.path.join(photos_folder, archive_hash)
    if not os.path.exists(full_path_to_folder):
        raise web.HTTPNotFound(text='Архив не существует или был удален.')

    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'

    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec('zip', '-rj', '-', f'{full_path_to_folder}',
                                                stdout=asyncio.subprocess.PIPE)

    try:
        while True:
            archive_part = await proc.stdout.read(500 * 1024)
            if archive_part:
                logging.info(f'Sending archive {archive_hash}.zip chunk ...')
                await response.write(archive_part)
                if delay:
                    await asyncio.sleep(delay)
            else:
                break
    except (asyncio.exceptions.CancelledError, KeyboardInterrupt):
        logging.info(f'Download was interrupted')
        proc.kill()
    except BaseException as e:
        proc.kill()
        logging.exception(f'Download was interrupted by exception: {e}', exc_info=True)
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.communicate()
        response.force_close()

    return response


async def handle_index_page(request):
    """Статическая главная страница."""
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    args = get_arguments()

    if args.logging:
        logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', partial(archivate, photos_folder=args.folder, delay=args.delay)),
    ])
    web.run_app(app)
