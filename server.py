import os
import logging
import asyncio

from aiohttp import web
import aiofiles

logging.basicConfig(level=logging.DEBUG)

BASE_PHOTOS_FOLDER = 'test_photos'


def is_folder_exist(folder_name):
    """Проверяем существует ли папка с фотографиями в общем каталоге."""
    full_path = os.path.join(BASE_PHOTOS_FOLDER, folder_name)
    if os.path.exists(full_path):
        return True


async def archivate(request):
    """Функция, которая архивирует переданую в запросе папку и возвращает ответ клиенту по частям."""
    response = web.StreamResponse()

    archive_hash = request.match_info.get('archive_hash')
    if not is_folder_exist(archive_hash):
        raise web.HTTPNotFound(text='Архив не существует или был удален.')

    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'

    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec('zip', '-rj', '-', f'{BASE_PHOTOS_FOLDER}/{archive_hash}',
                                                stdout=asyncio.subprocess.PIPE)

    try:
        while True:
            archive_part = await proc.stdout.read(500 * 1024)
            if archive_part:
                logging.info(f'Sending archive {archive_hash}.zip chunk ...')
                await response.write(archive_part)
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
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
