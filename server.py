import asyncio

from aiohttp import web
import aiofiles

BASE_PHOTOS_FOLDER = 'test_photos'


async def archivate(request):
    """Функция, которая архивирует переданую в запросе папку и возвращает ответ клиенту по частям."""
    response = web.StreamResponse()

    archive_hash = request.match_info.get('archive_hash')
    response.headers['Content-Disposition'] = f'attachment; filename="{archive_hash}.zip"'

    await response.prepare(request)

    proc = await asyncio.create_subprocess_shell(f'zip -rj - {BASE_PHOTOS_FOLDER}/{archive_hash}',
                                                 stdout=asyncio.subprocess.PIPE)

    while True:
        archive_part = await proc.stdout.read(500 * 1024)
        if archive_part:
            await response.write(archive_part)
        else:
            break

    await response.write_eof()

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
